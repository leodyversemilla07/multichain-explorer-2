#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MultiChain Explorer 2 - FastAPI Application

Modern FastAPI-based web application for exploring MultiChain blockchains.
Replaces the legacy http.server implementation with a production-grade ASGI server.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import app_state
from exceptions import (
    ChainNotFoundError,
    ResourceNotFoundError,
    MCEException,
)

# Import routers
from routers import (
    chains as chains_router,
    blocks as blocks_router,
    transactions as transactions_router,
    addresses as addresses_router,
    assets as assets_router,
    streams as streams_router,
    search as search_router,
    permissions as permissions_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Runs on startup and shutdown to initialize/cleanup resources.
    """
    # Startup
    logger.info("Starting MultiChain Explorer 2 (FastAPI)")
    
    # Initialize from .env
    logger.info("Loading configuration from .env")
    if app_state.init_from_env():
        logger.info("Configuration loaded successfully")
        chains = app_state.get_state().chains
        if chains:
            for chain in chains:
                chain_name = chain.config.get("name", "unknown")
                logger.info(f"Chain configured: {chain_name}")
    else:
        logger.warning("Could not load configuration from .env - using defaults")
    
    logger.info(f"Templates directory: {TEMPLATES_DIR}")
    logger.info(f"Static directory: {STATIC_DIR}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MultiChain Explorer 2")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Get version from app_state
    version = app_state.VERSION
    
    app = FastAPI(
        title="MultiChain Explorer 2",
        description="A modern, web-based explorer for MultiChain blockchains",
        version=version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"Mounted static files from {STATIC_DIR}")
    else:
        logger.warning(f"Static directory not found: {STATIC_DIR}")
    
    # Setup Jinja2 templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    
    # Store templates in app state for access in routes
    app.state.templates = templates
    
    # Register custom template filters
    _register_template_filters(templates)
    
    # Register exception handlers
    _register_exception_handlers(app, templates)

    # Register system routes FIRST to avoid being masked by catch-all routes
    system_router = APIRouter(tags=["System"])

    @system_router.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "version": app_state.VERSION,
        }

    @system_router.get("/api/info")
    async def api_info():
        """API information endpoint."""
        return {
            "name": "MultiChain Explorer 2 API",
            "version": app_state.VERSION,
            "docs": "/docs",
            "redoc": "/redoc",
        }
    
    app.include_router(system_router)

    # Include functional routers
    app.include_router(chains_router.router)
    app.include_router(blocks_router.router)
    app.include_router(transactions_router.router)
    app.include_router(addresses_router.router)
    app.include_router(assets_router.router)
    app.include_router(streams_router.router)
    app.include_router(search_router.router)
    app.include_router(permissions_router.router)
    
    logger.info("FastAPI application configured successfully")
    
    return app


def _register_template_filters(templates: Jinja2Templates) -> None:
    """Register custom Jinja2 filters for templates."""
    
    def format_hash(value: str, length: int = 16) -> str:
        """Format a hash for display (truncate with ellipsis)."""
        if not value or len(value) <= length:
            return value
        half = length // 2
        return f"{value[:half]}...{value[-half:]}"
    
    def format_amount(value: float, decimals: int = 8) -> str:
        """Format an amount with proper decimals."""
        if value == 0:
            return "0"
        return f"{value:.{decimals}f}".rstrip("0").rstrip(".")
    
    def format_timestamp(value: int) -> str:
        """Format a Unix timestamp to human-readable date."""
        from datetime import datetime
        if not value:
            return "N/A"
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
    
    # Register filters
    templates.env.filters["format_hash"] = format_hash
    templates.env.filters["format_amount"] = format_amount
    templates.env.filters["format_timestamp"] = format_timestamp


def _register_exception_handlers(app: FastAPI, templates: Jinja2Templates) -> None:
    """Register custom exception handlers."""
    
    @app.exception_handler(ChainNotFoundError)
    async def chain_not_found_handler(request: Request, exc: ChainNotFoundError):
        """Handle chain not found errors."""
        state = app_state.get_state()
        base_url = state.get_setting("main", "base", "/")
        
        context = {
            "request": request,
            "title": "Chain Not Found",
            "status_code": 404,
            "error_title": "Chain Not Found",
            "error_message": f"The blockchain '{exc.chain_name}' was not found.",
            "base_url": base_url,
        }
        return templates.TemplateResponse(
            name="pages/error.html",
            context=context,
            status_code=404,
        )
    
    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
        """Handle resource not found errors."""
        state = app_state.get_state()
        base_url = state.get_setting("main", "base", "/")
        
        context = {
            "request": request,
            "title": f"{exc.resource_type} Not Found",
            "status_code": 404,
            "error_title": f"{exc.resource_type} Not Found",
            "error_message": str(exc),
            "base_url": base_url,
        }
        return templates.TemplateResponse(
            name="pages/error.html",
            context=context,
            status_code=404,
        )
    
    @app.exception_handler(MCEException)
    async def mce_exception_handler(request: Request, exc: MCEException):
        """Handle general MCE exceptions."""
        state = app_state.get_state()
        base_url = state.get_setting("main", "base", "/")
        
        context = {
            "request": request,
            "title": "Error",
            "status_code": 500,
            "error_title": "Error",
            "error_message": str(exc),
            "base_url": base_url,
        }
        return templates.TemplateResponse(
            name="pages/error.html",
            context=context,
            status_code=500,
        )
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handle 404 errors."""
        state = app_state.get_state()
        base_url = state.get_setting("main", "base", "/")
        
        context = {
            "request": request,
            "title": "Page Not Found",
            "status_code": 404,
            "error_title": "Page Not Found",
            "error_message": "The page you requested could not be found.",
            "path": str(request.url.path),
            "base_url": base_url,
        }
        return templates.TemplateResponse(
            name="pages/error.html",
            context=context,
            status_code=404,
        )
    
    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc):
        """Handle 500 errors."""
        state = app_state.get_state()
        base_url = state.get_setting("main", "base", "/")
        
        context = {
            "request": request,
            "title": "Server Error",
            "status_code": 500,
            "error_title": "Internal Server Error",
            "error_message": "An unexpected error occurred. Please try again later.",
            "base_url": base_url,
        }
        return templates.TemplateResponse(
            name="pages/error.html",
            context=context,
            status_code=500,
        )


# Create the application instance
app = create_app()


def run_server(host: str = "127.0.0.1", port: int = 8080, reload: bool = False) -> None:
    """
    Run the FastAPI server using uvicorn.
    
    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to listen on (default: 8080)
        reload: Enable auto-reload for development (default: False)
    """
    import uvicorn
    
    print(f"\n🚀 MultiChain Explorer 2 (FastAPI)")
    print(f"   Server running at: http://{host}:{port}")
    print(f"   API Documentation: http://{host}:{port}/docs")
    print(f"   Press Ctrl+C to stop\n")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    import sys
    from env_config import get_settings
    
    # Load defaults from .env
    settings = get_settings()
    host = settings.explorer_host
    port = settings.explorer_port
    reload = settings.debug
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--reload":
            reload = True
            i += 1
        elif args[i] in ("-h", "--help"):
            print(f"""
MultiChain Explorer 2 - FastAPI Server

Usage: python main.py [options]

Configuration is loaded from .env file. CLI options override .env values.

Options:
  --host HOST    Host to bind to (default: {settings.explorer_host})
  --port PORT    Port to listen on (default: {settings.explorer_port})
  --reload       Enable auto-reload for development
  -h, --help     Show this help message

Current .env settings:
  Chain: {settings.multichain_chain_name}
  RPC:   {settings.multichain_rpc_host}:{settings.multichain_rpc_port}

Examples:
  python main.py
  python main.py --port 8000
  python main.py --host 0.0.0.0 --port 8080 --reload
  
Alternative (recommended):
  uvicorn main:app --host 0.0.0.0 --port 8080 --reload
""")
            sys.exit(0)
        else:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)
    
    run_server(host=host, port=port, reload=reload)
