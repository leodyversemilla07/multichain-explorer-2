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

from typing import Annotated, Any, Dict, Optional

from fastapi import Depends, HTTPException, Path, Query, Request, status
from fastapi.templating import Jinja2Templates

from app_state import ApplicationState
from config import ChainConfig
from exceptions import ChainConnectionError, ChainNotFoundError, RPCError
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService
from services.pagination_service import PaginationInfo


def get_state(request: Request) -> ApplicationState:
    """
    Dependency to get the application state.

    Returns:
        ApplicationState instance from app.state.config.

    Raises:
        RuntimeError: If application state is not initialized on app.state.
    """
    if hasattr(request.app.state, "config"):
        return request.app.state.config
    raise RuntimeError(
        "ApplicationState is not initialized on app.state.config. "
        "Ensure application lifespan startup has run or set app.state.config in tests."
    )


def get_templates(request: Request) -> Jinja2Templates:
    """
    Get Jinja2Templates instance from app state.

    Args:
        request: FastAPI request object

    Returns:
        Jinja2Templates instance
    """
    return request.app.state.templates


def _resolve_base_url(state: ApplicationState) -> str:
    """Resolve the configured base URL from application state."""
    return state.get_setting("main", "base", "/")


def get_base_url(state: ApplicationState = Depends(get_state)) -> str:
    """
    Get the base URL from application settings.

    Returns:
        Base URL string
    """
    return _resolve_base_url(state)


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
        base = _resolve_base_url(state)
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


async def get_state_dep(request: Request) -> ApplicationState:
    """Async wrapper for FastAPI dependency injection."""
    return get_state(request)


async def get_templates_dep(request: Request) -> Jinja2Templates:
    """Async wrapper for FastAPI dependency injection."""
    return get_templates(request)


async def get_base_url_dep(
    state: ApplicationState = Depends(get_state_dep),
) -> str:
    """Async wrapper for FastAPI dependency injection."""
    return _resolve_base_url(state)


async def get_chain_dep(
    chain_name: str = Path(..., description="Chain path name"),
    state: ApplicationState = Depends(get_state_dep),
) -> ChainConfig:
    """Async wrapper for FastAPI dependency injection."""
    return get_chain(chain_name=chain_name, state=state)


async def get_blockchain_service_dep(
    request: Request,
    chain: ChainConfig = Depends(get_chain_dep),
) -> BlockchainService:
    """Async wrapper for FastAPI dependency injection."""
    return get_blockchain_service(request=request, chain=chain)


async def get_pagination_service_dep() -> PaginationService:
    """Async wrapper for FastAPI dependency injection."""
    return get_pagination_service()


async def get_query_params_dep(request: Request) -> Dict[str, str]:
    """Async wrapper for FastAPI dependency injection."""
    return get_query_params(request)


async def get_optional_query_params_dep(request: Request) -> Dict[str, str]:
    """Async wrapper for FastAPI dependency injection."""
    return get_optional_query_params(request)


async def get_common_context(
    request: Request,
    chain: ChainConfig = Depends(get_chain_dep),
    state: ApplicationState = Depends(get_state_dep),
) -> CommonContext:
    """Build the shared template context without threadpool dependency hops."""
    return CommonContext(request=request, chain=chain, state=state)


# Type aliases for cleaner dependency injection
StateDep = Annotated[ApplicationState, Depends(get_state_dep)]
ChainDep = Annotated[ChainConfig, Depends(get_chain_dep)]
BlockchainServiceDep = Annotated[BlockchainService, Depends(get_blockchain_service_dep)]
PaginationServiceDep = Annotated[PaginationService, Depends(get_pagination_service_dep)]
PaginationDep = Annotated[PaginationParams, Depends()]
TemplatesDep = Annotated[Jinja2Templates, Depends(get_templates_dep)]
CommonContextDep = Annotated[CommonContext, Depends(get_common_context)]
BaseUrlDep = Annotated[str, Depends(get_base_url_dep)]


def get_query_params(request: Request) -> Dict[str, str]:
    """
    Extract query parameters from request.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary of query parameters (never None, always a dict)
    """
    return dict(request.query_params)


QueryParamsDep = Annotated[Dict[str, str], Depends(get_query_params_dep)]


def safe_int(value: Any, default: int = 0) -> int:
    """Safely cast a value to int, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def raise_backend_http_error(
    exc: Exception, not_found_detail: Optional[str] = None
) -> None:
    """Map backend service exceptions to the correct HTTP response."""
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, ChainConnectionError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if isinstance(exc, RPCError):
        if exc.error_code == -5 and not_found_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=not_found_detail,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    raise exc


def get_page_count(
    query_params: Dict[str, str],
    default_page: int = 1,
    default_count: int = 20,
) -> tuple[int, int]:
    """Parse page/count params, falling back to legacy start/count links."""
    count = safe_int(query_params.get("count", default_count), default_count)

    if "page" in query_params:
        return (
            safe_int(query_params.get("page", default_page), default_page),
            count,
        )

    if "start" in query_params and count > 0:
        start = safe_int(query_params.get("start", 0), 0)
        return ((start // count) + 1, count)

    return (default_page, count)


def get_start_count(
    query_params: Dict[str, str],
    default_start: int = 0,
    default_count: int = 20,
) -> tuple[int, int]:
    """Parse pagination params, preferring page/count and falling back to start/count."""
    count = safe_int(query_params.get("count", default_count), default_count)

    if "page" in query_params:
        page = safe_int(query_params.get("page", 1), 1)
        page = max(page, 1)
        return ((page - 1) * count, count)

    return (
        safe_int(query_params.get("start", default_start), default_start),
        count,
    )


def get_page_info_from_query(
    pagination: PaginationService,
    query_params: Dict[str, str],
    total: int,
    default_page: int = 1,
    default_count: int = 20,
) -> PaginationInfo:
    """Build PaginationInfo directly from shared page/count query parsing."""
    page, count = get_page_count(
        query_params,
        default_page=default_page,
        default_count=default_count,
    )
    return pagination.get_pagination_info(
        total=total,
        page=page,
        items_per_page=count,
    )


def get_page_info_from_start_count(
    pagination: PaginationService,
    total: int,
    start: int,
    count: int,
) -> PaginationInfo:
    """Build PaginationInfo from normalized start/count values."""
    page = ((start // count) + 1) if count > 0 else 1
    return pagination.get_pagination_info(
        total=total,
        page=page,
        items_per_page=count,
    )


async def get_page_count_dep(request: Request) -> tuple[int, int]:
    """Async dependency that returns normalized page/count values."""
    return get_page_count(get_query_params(request))


async def get_start_count_dep(request: Request) -> tuple[int, int]:
    """Async dependency that returns normalized start/count values."""
    return get_start_count(get_query_params(request))


PageCountDep = Annotated[tuple[int, int], Depends(get_page_count_dep)]
StartCountDep = Annotated[tuple[int, int], Depends(get_start_count_dep)]


# Optional version for routes where query params might not be needed
def get_optional_query_params(request: Request) -> Dict[str, str]:
    """
    Extract query parameters from request (returns empty dict if none).
    """
    return dict(request.query_params) if request.query_params else {}


OptionalQueryParamsDep = Annotated[
    Dict[str, str], Depends(get_optional_query_params_dep)
]
