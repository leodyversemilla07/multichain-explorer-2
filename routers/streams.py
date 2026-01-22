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
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Path, Request, HTTPException
from fastapi.responses import HTMLResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    CommonContextDep,
    get_query_params,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Streams"])


@router.get("/{chain_name}/streams", response_class=HTMLResponse, name="streams")
def list_streams(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List all streams on the blockchain.
    """
    try:
        streams = service.call("liststreams", ["*", True])
        if not streams:
            streams = []
        else:
            # Ensure each stream has proper item counts
            for stream in streams:
                # Get item count for each stream if not present
                if "items" not in stream or not isinstance(stream.get("items"), (int, float)):
                    try:
                        # Get actual count from liststreamitems
                        stream_items = service.call(
                            "liststreamitems", [stream["name"], False, 1]
                        )
                        stream["items"] = len(stream_items) if stream_items else 0
                    except:
                        stream["items"] = 0

                if "confirmed" not in stream or not isinstance(
                    stream.get("confirmed"), (int, float)
                ):
                    stream["confirmed"] = stream.get("items", 0)

    except Exception as e:
        logger.error(f"Error fetching streams: {e}")
        streams = []

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(streams),
        page=page,
        items_per_page=count,
    )

    paginated_streams = streams[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/streams",
    }

    return templates.TemplateResponse(
        name="pages/streams.html",
        context=context.build_context(
            title=f"Streams - {chain.config['display-name']}",
            streams=paginated_streams,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/stream/{stream_name}", response_class=HTMLResponse, name="stream")
def stream_detail(
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
        streams = service.call("liststreams", [stream_name, True])
        if not streams or len(streams) == 0:
            raise HTTPException(status_code=404, detail=f"Stream {stream_name} not found")
        stream = streams[0]

        # Fix items count if it's not a number
        if "items" not in stream or not isinstance(stream.get("items"), (int, float)):
            try:
                # Get actual count from liststreamitems
                stream_items = service.call("liststreamitems", [stream_name, False, 1])
                stream["items"] = len(stream_items) if stream_items else 0
            except:
                stream["items"] = 0

        if "confirmed" not in stream or not isinstance(stream.get("confirmed"), (int, float)):
            stream["confirmed"] = stream.get("items", 0)

    except Exception as e:
        logger.error(f"Error fetching stream {stream_name}: {e}")
        raise HTTPException(status_code=404, detail=f"Stream {stream_name} not found")

    return templates.TemplateResponse(
        name="pages/stream.html",
        context=context.build_context(
            title=f"Stream {stream_name}",
            stream=stream,
        ),
    )


@router.get("/{chain_name}/stream/{stream_name}/items", response_class=HTMLResponse, name="stream_items")
def stream_items(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List items in a stream.
    """
    try:
        # liststreamitems returns a list of items
        count_items = service.call("liststreamitems", [stream_name, False, 1, 0])
        total_count = len(count_items) if count_items else 0
    except Exception as e:
        logger.error(f"Error getting stream item count: {e}")
        total_count = 0

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=total_count,
        page=page,
        items_per_page=count,
    )

    items = []
    if total_count > 0:
        try:
            items = service.call(
                "liststreamitems",
                [stream_name, True, page_info["count"], page_info["start"]],
            )
        except Exception as e:
            logger.error(f"Error fetching stream items: {e}")
            items = []

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/stream/{stream_name}/items",
        "total": total_count,
        "total_pages": page_info["page_count"],
        "page_number": page_info["page"],
        "base_path": f"/{chain.config['path-name']}/stream/{stream_name}/items",
    }

    return templates.TemplateResponse(
        name="pages/stream_items.html",
        context=context.build_context(
            title=f"Items - {stream_name}",
            stream_name=stream_name,
            items=items,
            pagination=pagination_context,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/stream/{stream_name}/keys", response_class=HTMLResponse, name="stream_keys")
def stream_keys(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List keys in a stream.
    """
    try:
        keys = service.call("liststreamkeys", [stream_name, "*", False, 1000, 0])
        if not keys:
            keys = []
    except Exception as e:
        logger.error(f"Error fetching stream keys: {e}")
        keys = []

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(keys),
        page=page,
        items_per_page=count,
    )

    paginated_keys = keys[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/stream/{stream_name}/keys",
        "total": len(keys),
        "total_pages": page_info["page_count"],
        "page_number": page_info["page"],
        "base_path": f"/{chain.config['path-name']}/stream/{stream_name}/keys",
    }

    show_pagination = page_info["page_count"] > 1

    return templates.TemplateResponse(
        name="pages/stream_keys.html",
        context=context.build_context(
            title=f"Keys - {stream_name}",
            stream_name=stream_name,
            keys=paginated_keys,
            pagination=pagination_context,
            show_pagination=show_pagination,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/stream/{stream_name}/publishers", response_class=HTMLResponse, name="stream_publishers")
def stream_publishers(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List publishers in a stream.
    """
    try:
        publishers = service.call("liststreampublishers", [stream_name, "*", False, 1000, 0])
        if not publishers:
            publishers = []
    except Exception as e:
        logger.error(f"Error fetching stream publishers: {e}")
        publishers = []

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(publishers),
        page=page,
        items_per_page=count,
    )

    paginated_publishers = publishers[
        page_info["start"] : page_info["start"] + page_info["count"]
    ]

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/stream/{stream_name}/publishers",
        "total": len(publishers),
        "total_pages": page_info["page_count"],
        "page_number": page_info["page"],
        "base_path": f"/{chain.config['path-name']}/stream/{stream_name}/publishers",
    }

    show_pagination = page_info["page_count"] > 1

    return templates.TemplateResponse(
        name="pages/stream_publishers.html",
        context=context.build_context(
            title=f"Publishers - {stream_name}",
            stream_name=stream_name,
            publishers=paginated_publishers,
            pagination=pagination_context,
            show_pagination=show_pagination,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/stream/{stream_name}/permissions", response_class=HTMLResponse, name="stream_permissions")
def stream_permissions(
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
    try:
        permissions = service.call("listpermissions", [stream_name])
        if not permissions:
            permissions = []
    except Exception as e:
        logger.error(f"Error fetching stream permissions: {e}")
        permissions = []

    return templates.TemplateResponse(
        name="pages/stream_permissions.html",
        context=context.build_context(
            title=f"Permissions - {stream_name}",
            stream_name=stream_name,
            permissions=permissions,
        ),
    )


@router.get("/{chain_name}/stream/{stream_name}/key/{key}", response_class=HTMLResponse, name="key_items")
def key_items(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    key: str = Path(..., min_length=1, description="Key name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List items for a specific key in a stream.
    """
    try:
        count_items = service.call("liststreamkeyitems", [stream_name, key, False, 1, 0])
        total_count = len(count_items) if count_items else 0
    except Exception as e:
        logger.error(f"Error getting key item count: {e}")
        total_count = 0

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=total_count,
        page=page,
        items_per_page=count,
    )

    items = []
    if total_count > 0:
        try:
            items = service.call(
                "liststreamkeyitems",
                [stream_name, key, True, page_info["count"], page_info["start"]],
            )
        except Exception as e:
            logger.error(f"Error fetching key items: {e}")
            items = []

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/stream/{stream_name}/key/{key}",
        "total": total_count,
        "total_pages": page_info["page_count"],
        "page_number": page_info["page"],
        "base_path": f"/{chain.config['path-name']}/stream/{stream_name}/key/{key}",
    }

    return templates.TemplateResponse(
        name="pages/stream_key_items.html",
        context=context.build_context(
            title=f"Key Items - {stream_name} - {key}",
            stream_name=stream_name,
            key=key,
            items=items,
            pagination=pagination_context,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/stream/{stream_name}/publisher/{publisher}", response_class=HTMLResponse, name="publisher_items")
def publisher_items(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    publisher: str = Path(..., min_length=26, max_length=52, description="Publisher address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List items from a specific publisher in a stream.
    """
    try:
        count_items = service.call(
            "liststreampublisheritems", [stream_name, publisher, False, 1, 0]
        )
        total_count = len(count_items) if count_items else 0
    except Exception as e:
        logger.error(f"Error getting publisher item count: {e}")
        total_count = 0

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=total_count,
        page=page,
        items_per_page=count,
    )

    items = []
    if total_count > 0:
        try:
            items = service.call(
                "liststreampublisheritems",
                [stream_name, publisher, True, page_info["count"], page_info["start"]],
            )
        except Exception as e:
            logger.error(f"Error fetching publisher items: {e}")
            items = []

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/stream/{stream_name}/publisher/{publisher}",
        "total": total_count,
        "total_pages": page_info["page_count"],
        "page_number": page_info["page"],
        "base_path": f"/{chain.config['path-name']}/stream/{stream_name}/publisher/{publisher}",
    }

    return templates.TemplateResponse(
        name="pages/stream_publisher_items.html",
        context=context.build_context(
            title=f"Publisher Items - {stream_name} - {publisher[:16]}...",
            stream_name=stream_name,
            publisher=publisher,
            items=items,
            pagination=pagination_context,
            **pagination_context
        ),
    )


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/streams", response_class=HTMLResponse, name="legacy_streams", include_in_schema=False)
def legacy_list_streams(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy streams list route."""
    return list_streams(request, chain, service, pagination, templates, context, query_params)


@router.get("/chain/{chain_name}/stream/{stream_name}", response_class=HTMLResponse, name="legacy_stream", include_in_schema=False)
def legacy_stream_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    stream_name: str = Path(..., min_length=1),
):
    """Legacy stream detail route."""
    return stream_detail(request, chain, service, templates, context, stream_name)
