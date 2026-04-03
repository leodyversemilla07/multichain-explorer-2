#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Streams Router - FastAPI routes for stream-related operations.

Handles:
- Stream listing
- Stream details
- Stream items
- Stream keys
- Stream publishers
- Stream permissions
- Key items
- Publisher items
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, Path, Request, HTTPException
from fastapi.responses import HTMLResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    CommonContextDep,
    get_query_params_dep,
    get_page_count,
    get_page_info_from_query,
    raise_backend_http_error,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Streams"])


async def _get_stream_or_raise(
    service: BlockchainServiceDep, stream_name: str
) -> Dict[str, Any]:
    """Load a stream and raise a typed HTTP error when it is unavailable."""
    try:
        stream = await service.get_stream(stream_name)
    except Exception as exc:
        raise_backend_http_error(
            exc, not_found_detail=f"Stream {stream_name} not found"
        )

    if not stream:
        raise HTTPException(status_code=404, detail=f"Stream {stream_name} not found")

    return stream


async def _count_stream_results(
    service: BlockchainServiceDep,
    method: str,
    *leading_params: Any,
) -> int:
    """Count paginated stream-related results using the shared fallback."""
    if method == "liststreamitems" and len(leading_params) == 1:
        return await service.count_stream_items(leading_params[0])
    if method == "liststreamkeyitems" and len(leading_params) == 2:
        return await service.count_stream_key_items(
            leading_params[0], leading_params[1]
        )
    if method == "liststreampublisheritems" and len(leading_params) == 2:
        return await service.count_stream_publisher_items(
            leading_params[0], leading_params[1]
        )
    return await service.count_rpc_list_results(method, *leading_params)


@router.get(
    "/{chain_name}/streams",
    response_class=HTMLResponse,
    name="streams",
    summary="List streams",
)
async def list_streams(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List all streams on the blockchain.
    """
    try:
        streams = await service.get_all_streams()
    except Exception as exc:
        logger.error("Error fetching streams", exc_info=exc)
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    paginated_streams, page_info = pagination.paginate(
        streams,
        page=page,
        items_per_page=count,
    )
    paginated_streams = [dict(stream) for stream in paginated_streams]

    for stream in paginated_streams:
        if "items" not in stream or not isinstance(stream.get("items"), (int, float)):
            try:
                stream["items"] = await service.count_stream_items(stream["name"])
            except Exception:
                stream["items"] = 0

        if "confirmed" not in stream or not isinstance(
            stream.get("confirmed"), (int, float)
        ):
            stream["confirmed"] = stream.get("items", 0)

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/streams",
        include_component_fields=True,
        total_items=len(streams),
    )
    show_pagination = page_info["page_count"] > 1

    return templates.TemplateResponse(
        name="pages/streams.html",
        context=context.build_context(
            title=f"Streams - {chain.display_name}",
            streams=paginated_streams,
            pagination=page_info,
            show_pagination=show_pagination,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/stream/{stream_name}",
    response_class=HTMLResponse,
    name="stream",
    summary="Stream details",
)
async def stream_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
):
    """
    Show stream details.
    """
    try:
        stream = dict(await _get_stream_or_raise(service, stream_name))

        # Fix items count if it's not a number
        if "items" not in stream or not isinstance(stream.get("items"), (int, float)):
            try:
                stream["items"] = await service.count_stream_items(stream_name)
            except Exception:
                stream["items"] = 0

        if "confirmed" not in stream or not isinstance(
            stream.get("confirmed"), (int, float)
        ):
            stream["confirmed"] = stream.get("items", 0)

    except Exception as exc:
        logger.error("Error fetching stream %s", stream_name, exc_info=exc)
        raise_backend_http_error(
            exc, not_found_detail=f"Stream {stream_name} not found"
        )

    try:
        stream_items_preview = await service.call(
            "liststreamitems", [stream_name, True, 10, 0]
        )
    except Exception:
        stream_items_preview = []

    return templates.TemplateResponse(
        name="pages/stream.html",
        context=context.build_context(
            title=f"Stream {stream_name}",
            stream=stream,
            stream_items=stream_items_preview or [],
            show_pagination=False,
            pagination=None,
        ),
    )


@router.get(
    "/{chain_name}/stream/{stream_name}/items",
    response_class=HTMLResponse,
    name="stream_items",
    summary="Stream items",
)
async def stream_items(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List items in a stream.
    """
    await _get_stream_or_raise(service, stream_name)

    try:
        total_count = await _count_stream_results(
            service,
            "liststreamitems",
            stream_name,
        )
    except Exception as exc:
        logger.error("Error getting stream item count", exc_info=exc)
        raise_backend_http_error(exc)

    page_info = get_page_info_from_query(pagination, query_params, total_count)

    items = []
    if total_count > 0:
        try:
            items = await service.call_windowed_list(
                "liststreamitems",
                stream_name,
                count=page_info["count"],
                start=page_info["start"],
                verbose=True,
            )
        except Exception as exc:
            logger.error("Error fetching stream items", exc_info=exc)
            raise_backend_http_error(exc)

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/stream/{stream_name}/items",
        include_component_fields=True,
        total_items=total_count,
    )

    return templates.TemplateResponse(
        name="pages/stream_items.html",
        context=context.build_context(
            title=f"Items - {stream_name}",
            stream_name=stream_name,
            items=items,
            pagination=page_info,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/stream/{stream_name}/keys",
    response_class=HTMLResponse,
    name="stream_keys",
    summary="Stream keys",
)
async def stream_keys(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List keys in a stream.
    """
    await _get_stream_or_raise(service, stream_name)

    try:
        keys = await service.get_all_stream_keys(stream_name)
    except Exception as exc:
        logger.error("Error fetching stream keys", exc_info=exc)
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    paginated_keys, page_info = pagination.paginate(
        keys,
        page=page,
        items_per_page=count,
    )

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/stream/{stream_name}/keys",
        include_component_fields=True,
        total_items=len(keys),
    )

    show_pagination = page_info["page_count"] > 1

    return templates.TemplateResponse(
        name="pages/stream_keys.html",
        context=context.build_context(
            title=f"Keys - {stream_name}",
            stream_name=stream_name,
            keys=paginated_keys,
            pagination=page_info,
            show_pagination=show_pagination,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/stream/{stream_name}/publishers",
    response_class=HTMLResponse,
    name="stream_publishers",
    summary="Stream publishers",
)
async def stream_publishers(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List publishers in a stream.
    """
    await _get_stream_or_raise(service, stream_name)

    try:
        publishers = await service.get_all_stream_publishers(stream_name)
    except Exception as exc:
        logger.error("Error fetching stream publishers", exc_info=exc)
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    paginated_publishers, page_info = pagination.paginate(
        publishers,
        page=page,
        items_per_page=count,
    )

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/stream/{stream_name}/publishers",
        include_component_fields=True,
        total_items=len(publishers),
    )

    show_pagination = page_info["page_count"] > 1

    return templates.TemplateResponse(
        name="pages/stream_publishers.html",
        context=context.build_context(
            title=f"Publishers - {stream_name}",
            stream_name=stream_name,
            publishers=paginated_publishers,
            pagination=page_info,
            show_pagination=show_pagination,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/stream/{stream_name}/permissions",
    response_class=HTMLResponse,
    name="stream_permissions",
    summary="Stream permissions",
)
async def stream_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
):
    """
    Show stream permissions.
    """
    await _get_stream_or_raise(service, stream_name)

    try:
        permissions = await service.call("listpermissions", [stream_name])
        if not permissions:
            permissions = []
    except Exception as exc:
        logger.error("Error fetching stream permissions", exc_info=exc)
        raise_backend_http_error(exc)

    return templates.TemplateResponse(
        name="pages/stream_permissions.html",
        context=context.build_context(
            title=f"Permissions - {stream_name}",
            stream_name=stream_name,
            permissions=permissions,
        ),
    )


@router.get(
    "/{chain_name}/stream/{stream_name}/key/{key}",
    response_class=HTMLResponse,
    name="key_items",
    summary="Items by stream key",
)
async def key_items(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    key: str = Path(..., min_length=1, description="Key name"),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List items for a specific key in a stream.
    """
    await _get_stream_or_raise(service, stream_name)

    try:
        total_count = await _count_stream_results(
            service,
            "liststreamkeyitems",
            stream_name,
            key,
        )
    except Exception as exc:
        logger.error("Error getting key item count", exc_info=exc)
        raise_backend_http_error(exc)

    page_info = get_page_info_from_query(pagination, query_params, total_count)

    items = []
    if total_count > 0:
        try:
            items = await service.call_windowed_list(
                "liststreamkeyitems",
                stream_name,
                key,
                count=page_info["count"],
                start=page_info["start"],
                verbose=True,
            )
        except Exception as exc:
            logger.error("Error fetching key items", exc_info=exc)
            raise_backend_http_error(exc)

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/stream/{stream_name}/key/{key}",
        include_component_fields=True,
        total_items=total_count,
    )

    return templates.TemplateResponse(
        name="pages/stream_key_items.html",
        context=context.build_context(
            title=f"Key Items - {stream_name} - {key}",
            stream_name=stream_name,
            key=key,
            items=items,
            pagination=page_info,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/stream/{stream_name}/publisher/{publisher}",
    response_class=HTMLResponse,
    name="publisher_items",
    summary="Items by stream publisher",
)
async def publisher_items(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    publisher: str = Path(
        ..., min_length=26, max_length=52, description="Publisher address"
    ),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List items from a specific publisher in a stream.
    """
    await _get_stream_or_raise(service, stream_name)

    try:
        total_count = await _count_stream_results(
            service,
            "liststreampublisheritems",
            stream_name,
            publisher,
        )
    except Exception as exc:
        logger.error("Error getting publisher item count", exc_info=exc)
        raise_backend_http_error(exc)

    page_info = get_page_info_from_query(pagination, query_params, total_count)

    items = []
    if total_count > 0:
        try:
            items = await service.call_windowed_list(
                "liststreampublisheritems",
                stream_name,
                publisher,
                count=page_info["count"],
                start=page_info["start"],
                verbose=True,
            )
        except Exception as exc:
            logger.error("Error fetching publisher items", exc_info=exc)
            raise_backend_http_error(exc)

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/stream/{stream_name}/publisher/{publisher}",
        include_component_fields=True,
        total_items=total_count,
    )

    return templates.TemplateResponse(
        name="pages/stream_publisher_items.html",
        context=context.build_context(
            title=f"Publisher Items - {stream_name} - {publisher[:16]}...",
            stream_name=stream_name,
            publisher=publisher,
            items=items,
            pagination=page_info,
            **pagination_context,
        ),
    )


# Legacy routes for backward compatibility
@router.get(
    "/chain/{chain_name}/streams",
    response_class=HTMLResponse,
    name="legacy_streams",
    include_in_schema=False,
)
async def legacy_list_streams(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """Legacy streams list route."""
    return await list_streams(
        request, chain, service, pagination, templates, context, query_params
    )


@router.get(
    "/chain/{chain_name}/stream/{stream_name}",
    response_class=HTMLResponse,
    name="legacy_stream",
    include_in_schema=False,
)
async def legacy_stream_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1),
):
    """Legacy stream detail route."""
    return await stream_detail(request, chain, service, templates, context, stream_name)
