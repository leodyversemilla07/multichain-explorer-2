#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI Dependencies for MultiChain Explorer 2.

This module provides dependency injection functions for FastAPI routes.
These dependencies handle common operations like:
- Getting chain objects by name
- Getting service instances
- Template rendering
- Pagination parameters
"""

from typing import Annotated, Any, Dict

from fastapi import Depends, Path, Query, Request
from fastapi.templating import Jinja2Templates

import app_state
from app_state import ApplicationState
from config import ChainConfig
from exceptions import ChainNotFoundError
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService


def get_state(request: Request) -> ApplicationState:
    """
    Dependency to get the application state.
    
    Returns:
        ApplicationState instance from app state or singleton as fallback.
    """
    if hasattr(request.app.state, "config"):
        return request.app.state.config
    return app_state.get_state()


def get_templates(request: Request) -> Jinja2Templates:
    """
    Get Jinja2Templates instance from app state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Jinja2Templates instance
    """
    return request.app.state.templates


def get_base_url(state: ApplicationState = Depends(get_state)) -> str:
    """
    Get the base URL from application settings.
    
    Returns:
        Base URL string
    """
    return state.get_setting("main", "base", "/")


def get_chain(
    chain_name: str = Path(..., description="Chain path name"),
    state: ApplicationState = Depends(get_state),
) -> ChainConfig:
    """
    Get chain object by name.
    
    This is a dependency that retrieves the chain configuration
    from the application state.
    
    Args:
        chain_name: The path name of the chain
        state: Application state dependency
        
    Returns:
        ChainConfig object
        
    Raises:
        ChainNotFoundError: If chain doesn't exist
    """
    chain = state.get_chain_by_name(chain_name)
    if not chain:
        raise ChainNotFoundError(chain_name)
    return chain


def get_blockchain_service(
    request: Request,
    chain: ChainConfig = Depends(get_chain),
) -> BlockchainService:
    """
    Get BlockchainService instance for a chain.

    Injects the shared httpx.AsyncClient from app.state when available,
    enabling connection pooling across all requests.

    Args:
        request: FastAPI request (used to access app.state.http_client)
        chain: Chain configuration from get_chain dependency

    Returns:
        BlockchainService instance
    """
    http_client = getattr(request.app.state, "http_client", None)
    return BlockchainService(chain, client=http_client)


def get_pagination_service() -> PaginationService:
    """
    Get PaginationService instance.
    
    Returns:
        PaginationService instance
    """
    return PaginationService()


class PaginationParams:
    """
    Common pagination parameters.
    
    Use as a dependency to get standard pagination parameters.
    """
    
    def __init__(
        self,
        start: int = Query(0, ge=0, description="Starting offset"),
        count: int = Query(20, ge=1, le=500, description="Items per page"),
    ):
        self.start = start
        self.count = count
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for passing to handlers."""
        return {"start": self.start, "count": self.count}


class CommonContext:
    """
    Common template context provider.
    
    Provides common context variables needed by all templates.
    """
    
    def __init__(
        self,
        request: Request,
        chain: ChainConfig = Depends(get_chain),
        state: ApplicationState = Depends(get_state),
    ):
        self.request = request
        self.chain = chain
        self.templates = request.app.state.templates
        base = get_base_url(state)
        # Remove trailing slash from base_url to avoid double slashes, but keep it if it's just "/"
        self.base_url = base.rstrip("/") if len(base) > 1 else base
        self.chain_name = chain.display_name
        self.chain_path = "/" + chain.path_name
    
    def build_context(self, **kwargs) -> Dict[str, Any]:
        """
        Build template context with common variables.
        
        Args:
            **kwargs: Additional context variables
            
        Returns:
            Complete context dictionary
        """
        context = {
            "request": self.request,
            "base_url": self.base_url,
            "chain_name": self.chain_name,
            "chain_path": self.chain_path,
        }
        context.update(kwargs)
        return context


# Type aliases for cleaner dependency injection
StateDep = Annotated[ApplicationState, Depends(get_state)]
ChainDep = Annotated[ChainConfig, Depends(get_chain)]
BlockchainServiceDep = Annotated[BlockchainService, Depends(get_blockchain_service)]
PaginationServiceDep = Annotated[PaginationService, Depends(get_pagination_service)]
PaginationDep = Annotated[PaginationParams, Depends()]
TemplatesDep = Annotated[Jinja2Templates, Depends(get_templates)]
CommonContextDep = Annotated[CommonContext, Depends()]


def get_query_params(request: Request) -> Dict[str, str]:
    """
    Extract query parameters from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary of query parameters (never None, always a dict)
    """
    return dict(request.query_params)


QueryParamsDep = Annotated[Dict[str, str], Depends(get_query_params)]


def safe_int(value: Any, default: int = 0) -> int:
    """Safely cast a value to int, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Optional version for routes where query params might not be needed
def get_optional_query_params(request: Request) -> Dict[str, str]:
    """
    Extract query parameters from request (returns empty dict if none).
    """
    return dict(request.query_params) if request.query_params else {}


OptionalQueryParamsDep = Annotated[Dict[str, str], Depends(get_optional_query_params)]
