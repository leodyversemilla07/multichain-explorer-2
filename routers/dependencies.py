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
from exceptions import ChainNotFoundError
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService


def get_templates(request: Request) -> Jinja2Templates:
    """
    Get Jinja2Templates instance from app state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Jinja2Templates instance
    """
    return request.app.state.templates


def get_base_url() -> str:
    """
    Get the base URL from application settings.
    
    Returns:
        Base URL string
    """
    state = app_state.get_state()
    return state.get_setting("main", "base", "/")


def get_chain(chain_name: str = Path(..., description="Chain path name")):
    """
    Get chain object by name.
    
    This is a dependency that retrieves the chain configuration
    from the application state.
    
    Args:
        chain_name: The path name of the chain
        
    Returns:
        Chain object (MCEChain)
        
    Raises:
        ChainNotFoundError: If chain doesn't exist
    """
    state = app_state.get_state()
    chains = state.chains or []
    
    for chain in chains:
        if chain.config.get("path-name") == chain_name:
            return chain
    
    raise ChainNotFoundError(chain_name)


def get_blockchain_service(chain = Depends(get_chain)) -> BlockchainService:
    """
    Get BlockchainService instance for a chain.
    
    Args:
        chain: Chain object from get_chain dependency
        
    Returns:
        BlockchainService instance
    """
    return BlockchainService(chain)


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
        chain = Depends(get_chain),
    ):
        self.request = request
        self.chain = chain
        self.templates = request.app.state.templates
        self.base_url = get_base_url()
        self.chain_name = chain.config.get("display-name", chain.config.get("name", ""))
        self.chain_path = chain.config.get("path-name", "")
    
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
ChainDep = Annotated[Any, Depends(get_chain)]
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


# Optional version for routes where query params might not be needed
def get_optional_query_params(request: Request) -> Dict[str, str]:
    """
    Extract query parameters from request (returns empty dict if none).
    """
    return dict(request.query_params) if request.query_params else {}


OptionalQueryParamsDep = Annotated[Dict[str, str], Depends(get_optional_query_params)]
