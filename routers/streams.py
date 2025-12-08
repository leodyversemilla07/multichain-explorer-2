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

from typing import Dict

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import HTMLResponse

from handlers.stream_handler import StreamHandler
from routers.dependencies import (
    ChainDep,
    get_query_params,
)

router = APIRouter(tags=["Streams"])


@router.get("/{chain_name}/streams", response_class=HTMLResponse, name="streams")
async def list_streams(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List all streams on the blockchain.
    
    Displays all created streams with their details.
    """
    handler = StreamHandler()
    status, headers, body = handler.handle_streams_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/stream/{stream_name}", response_class=HTMLResponse, name="stream")
async def stream_detail(
    request: Request,
    chain: ChainDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show stream details.
    
    Displays comprehensive stream information including:
    - Stream configuration
    - Item count
    - Publisher count
    - Recent items
    """

    handler = StreamHandler()
    status, headers, body = handler.handle_stream_detail(chain, stream_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/stream/{stream_name}/items", response_class=HTMLResponse, name="stream_items")
async def stream_items(
    request: Request,
    chain: ChainDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List items in a stream.
    
    Shows all items published to this stream.
    """

    handler = StreamHandler()
    status, headers, body = handler.handle_stream_items(chain, stream_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/stream/{stream_name}/keys", response_class=HTMLResponse, name="stream_keys")
async def stream_keys(
    request: Request,
    chain: ChainDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List keys in a stream.
    
    Shows all unique keys used in stream items.
    """

    handler = StreamHandler()
    status, headers, body = handler.handle_stream_keys(chain, stream_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/stream/{stream_name}/publishers", response_class=HTMLResponse, name="stream_publishers")
async def stream_publishers(
    request: Request,
    chain: ChainDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List publishers in a stream.
    
    Shows all addresses that have published to this stream.
    """

    handler = StreamHandler()
    status, headers, body = handler.handle_stream_publishers(chain, stream_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/stream/{stream_name}/permissions", response_class=HTMLResponse, name="stream_permissions")
async def stream_permissions(
    request: Request,
    chain: ChainDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show stream permissions.
    
    Displays permission settings for this stream.
    """

    handler = StreamHandler()
    status, headers, body = handler.handle_stream_permissions(chain, stream_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/stream/{stream_name}/key/{key}", response_class=HTMLResponse, name="key_items")
async def key_items(
    request: Request,
    chain: ChainDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    key: str = Path(..., min_length=1, description="Key name"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List items for a specific key in a stream.
    
    Shows all items with the specified key.
    """

    handler = StreamHandler()
    status, headers, body = handler.handle_key_items(chain, stream_name, key, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/stream/{stream_name}/publisher/{publisher}", response_class=HTMLResponse, name="publisher_items")
async def publisher_items(
    request: Request,
    chain: ChainDep,
    stream_name: str = Path(..., min_length=1, description="Stream name"),
    publisher: str = Path(..., min_length=26, max_length=35, description="Publisher address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List items from a specific publisher in a stream.
    
    Shows all items published by the specified address.
    """

    handler = StreamHandler()
    status, headers, body = handler.handle_publisher_items(chain, stream_name, publisher, query_params)
    return HTMLResponse(content=body, status_code=status)


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/streams", response_class=HTMLResponse, name="legacy_streams", include_in_schema=False)
async def legacy_list_streams(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy streams list route."""
    handler = StreamHandler()
    status, headers, body = handler.handle_streams_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/chain/{chain_name}/stream/{stream_name}", response_class=HTMLResponse, name="legacy_stream", include_in_schema=False)
async def legacy_stream_detail(
    request: Request,
    chain: ChainDep,
    stream_name: str = Path(..., min_length=1),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy stream detail route."""

    handler = StreamHandler()
    status, headers, body = handler.handle_stream_detail(chain, stream_name, query_params)
    return HTMLResponse(content=body, status_code=status)
