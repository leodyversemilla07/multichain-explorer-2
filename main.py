#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MultiChain Explorer 2 - FastAPI Application

Modern FastAPI-based web application for exploring MultiChain blockchains.
Replaces the legacy http.server implementation with a production-grade ASGI server.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware

import app_state
from env_config import get_settings
from exceptions import (
    ChainNotFoundError,
    ResourceNotFoundError,
    MCEException,
)
from services.cache_service import CacheService, create_cache_provider, _replace_global_cache
from services.blockchain_service import BlockchainService
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Rate limiter — keyed by client IP, 60 requests/minute default
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

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
from routers.api import api_router

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

    # Create a shared HTTP client for all blockchain RPC calls
    # This enables connection pooling (one client reused across requests)
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    logger.info("Shared HTTP client created")

    # Select and initialise cache provider from env config
    settings = get_settings()
    cache_provider = create_cache_provider(
        backend=settings.cache_backend,
        redis_url=settings.redis_url,
    )
    _replace_global_cache(CacheService(cache_provider))
    app.state.cache_provider = cache_provider
    logger.info(f"Cache backend initialised: {settings.cache_backend}")

    # Initialize from .env
    logger.info("Loading configuration from .env")
    if app_state.init_from_env():
        logger.info("Configuration loaded successfully")
        state = app_state.get_state()
        app.state.config = state
        chains = state.chains
        if chains:
            for chain in chains:
                logger.info(f"Chain configured: {chain.name}")
    else:
        logger.warning("Could not load configuration from .env - using defaults")

    logger.info(f"Templates directory: {TEMPLATES_DIR}")
    logger.info(f"Static directory: {STATIC_DIR}")

    yield

    # Shutdown
    logger.info("Shutting down MultiChain Explorer 2")
    await app.state.http_client.aclose()
    logger.info("Shared HTTP client closed")
    # Close Redis connection pool if applicable
    if hasattr(app.state.cache_provider, "close"):
        await app.state.cache_provider.close()
        logger.info("Cache provider closed")


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

    # Rate limiting — attach limiter to app state and add middleware + 429 handler
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting enabled (60 req/min per IP by default)")

    # TrustedHostMiddleware — rejects requests with unexpected Host headers.
    # Must be registered before CORSMiddleware so it's between rate limiting and CORS.
    # Skill ref: fastapi-agents > middleware > TrustedHostMiddleware
    settings = get_settings()
    trusted_hosts = settings.trusted_hosts_list
    if trusted_hosts != ["*"]:  # skip in dev (wildcard = allow all)
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
        logger.info(f"TrustedHostMiddleware enabled for: {trusted_hosts}")
    else:
        logger.info("TrustedHostMiddleware: wildcard mode (all hosts allowed – set TRUSTED_HOSTS in production)")

    # CORS — must be added LAST (outermost) so OPTIONS preflight requests are
    # answered before rate limiting or other middleware runs.
    # Skill ref: fastapi-agents > middleware > CORSMiddleware
    cors_origins = settings.cors_origins_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=cors_origins != ["*"],  # never combine wildcard + credentials
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {cors_origins}")

    # Register system routes FIRST to avoid being masked by catch-all routes
    system_router = APIRouter(tags=["System"])

    @system_router.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        """Serve favicon."""
        from fastapi.responses import FileResponse
        favicon_path = STATIC_DIR / "logo32.png"
        if favicon_path.exists():
            return FileResponse(favicon_path, media_type="image/png")
        return FileResponse(status_code=204)

    @system_router.get("/health")
    async def health_check(request: Request):
        """Health check endpoint for monitoring."""
        status = "healthy"
        chain_status = {}

        state = getattr(request.app.state, "config", None)
        http_client = getattr(request.app.state, "http_client", None)
        chains = getattr(state, "chains", []) if state is not None else []

        # Only run chain connectivity checks when lifespan has initialized shared app state.
        if chains and http_client is not None:
            checks = await asyncio.gather(
                *[
                    BlockchainService(chain, client=http_client).is_healthy()
                    for chain in chains
                ],
                return_exceptions=True,
            )
            for chain, result in zip(chains, checks):
                connected = not isinstance(result, Exception) and bool(result)
                chain_status[chain.name] = "connected" if connected else "disconnected"
                if not connected:
                    status = "degraded"

        return {
            "status": status,
            "version": app_state.VERSION,
            "chains": chain_status,
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
    app.include_router(api_router)

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
        from datetime import datetime, timezone
        if not value:
            return "N/A"
        return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    # Register filters
    templates.env.filters["format_hash"] = format_hash
    templates.env.filters["format_amount"] = format_amount
    templates.env.filters["format_timestamp"] = format_timestamp


def _register_exception_handlers(app: FastAPI, templates: Jinja2Templates) -> None:
    """Register custom exception handlers."""

    def _is_api_request(request: Request) -> bool:
        """Return True when the client expects JSON (API routes or explicit Accept header)."""
        if request.url.path.startswith("/api/"):
            return True
        accept = request.headers.get("accept", "")
        return "application/json" in accept and "text/html" not in accept

    def _get_base_url(request: Request) -> str:
        """Safely get base_url from app state, fall back to '/' if not yet initialised."""
        try:
            return request.app.state.config.get_setting("main", "base", "/")
        except AttributeError:
            return "/"

    @app.exception_handler(ChainNotFoundError)
    async def chain_not_found_handler(request: Request, exc: ChainNotFoundError):
        """Handle chain not found errors."""
        if _is_api_request(request):
            return JSONResponse(status_code=404, content={"detail": str(exc)})
        base_url = _get_base_url(request)
        context = {
            "request": request,
            "title": "Chain Not Found",
            "status_code": 404,
            "error_title": "Chain Not Found",
            "error_message": f"The blockchain '{exc.chain_name}' was not found.",
            "base_url": base_url,
        }
        return templates.TemplateResponse(name="pages/error.html", context=context, status_code=404)
    
    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
        """Handle resource not found errors."""
        if _is_api_request(request):
            return JSONResponse(status_code=404, content={"detail": str(exc)})
        base_url = _get_base_url(request)
        context = {
            "request": request,
            "title": f"{exc.resource_type} Not Found",
            "status_code": 404,
            "error_title": f"{exc.resource_type} Not Found",
            "error_message": str(exc),
            "base_url": base_url,
        }
        return templates.TemplateResponse(name="pages/error.html", context=context, status_code=404)
    
    @app.exception_handler(MCEException)
    async def mce_exception_handler(request: Request, exc: MCEException):
        """Handle general MCE exceptions."""
        if _is_api_request(request):
            return JSONResponse(status_code=500, content={"detail": str(exc), "type": type(exc).__name__})
        base_url = _get_base_url(request)
        context = {
            "request": request,
            "title": "Error",
            "status_code": 500,
            "error_title": "Error",
            "error_message": str(exc),
            "base_url": base_url,
        }
        return templates.TemplateResponse(name="pages/error.html", context=context, status_code=500)
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handle 404 errors."""
        if _is_api_request(request):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        base_url = _get_base_url(request)
        context = {
            "request": request,
            "title": "Page Not Found",
            "status_code": 404,
            "error_title": "Page Not Found",
            "error_message": "The page you requested could not be found.",
            "path": str(request.url.path),
            "base_url": base_url,
        }
        return templates.TemplateResponse(name="pages/error.html", context=context, status_code=404)
    
    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc):
        """Handle 500 errors."""
        if _is_api_request(request):
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
        base_url = _get_base_url(request)
        context = {
            "request": request,
            "title": "Server Error",
            "status_code": 500,
            "error_title": "Internal Server Error",
            "error_message": "An unexpected error occurred. Please try again later.",
            "base_url": base_url,
        }
        return templates.TemplateResponse(name="pages/error.html", context=context, status_code=500)

    # Catch-all bare Exception guard — skill ref: fastapi-agents > errors > Unhandled Exception Guard
    # Must be registered LAST so more-specific handlers above take priority.
    # Prevents raw Python tracebacks from ever reaching clients in production.
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for any unhandled exception."""
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
        if _is_api_request(request):
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
        base_url = _get_base_url(request)
        context = {
            "request": request,
            "title": "Server Error",
            "status_code": 500,
            "error_title": "Internal Server Error",
            "error_message": "An unexpected error occurred. Please try again later.",
            "base_url": base_url,
        }
        return templates.TemplateResponse(name="pages/error.html", context=context, status_code=500)


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
