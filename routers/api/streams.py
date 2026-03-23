"""API Streams Router - JSON endpoints for stream-related operations."""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import StreamResponse, StreamItemResponse

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    get_query_params,
    get_page_count,
    get_start_count,
    raise_backend_http_error,
)

router = APIRouter(tags=["API Streams"])


async def _get_stream_or_raise(service: BlockchainServiceDep, stream_ref: str) -> Dict:
    """Load a stream or raise the correct HTTP error."""
    try:
        stream = await service.get_stream(stream_ref)
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Stream {stream_ref} not found")

    if not stream:
        raise HTTPException(status_code=404, detail=f"Stream {stream_ref} not found")

    return stream


@router.get(
    "/{chain_name}/streams",
    response_model=List[StreamResponse],
    name="api_list_streams",
    summary="List streams",
    description="Returns a paginated list of all streams on the chain, sorted by name. Accepts `page` and `count` query params.",
    responses={
        200: {"description": "Paginated list of streams"},
        404: {"description": "Chain not found"},
    },
)
async def list_streams(
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    query_params: dict = Depends(get_query_params),
):
    """
    List streams in the blockchain (JSON).
    """
    try:
        streams = await service.get_all_streams()
    except Exception as exc:
        raise_backend_http_error(exc)

    streams = sorted(streams, key=lambda x: x.get("name", ""))
    page, count = get_page_count(query_params)

    page_info = pagination.get_pagination_info(
        total=len(streams),
        page=page,
        items_per_page=count,
    )

    paginated_streams = streams[
        page_info["start"] : page_info["start"] + page_info["count"]
    ]

    return [StreamResponse(**s) for s in paginated_streams]


@router.get(
    "/{chain_name}/streams/{stream_ref}",
    response_model=StreamResponse,
    name="api_get_stream",
    summary="Get stream",
    description="Fetch details for a single stream by name or reference.",
    responses={
        200: {"description": "Stream details"},
        404: {"description": "Stream not found"},
    },
)
async def get_stream(
    chain: ChainDep,
    service: BlockchainServiceDep,
    stream_ref: str = Path(..., description="Stream name or reference"),
):
    """
    Get stream details (JSON).
    """
    stream = await _get_stream_or_raise(service, stream_ref)
    return StreamResponse(**stream)


@router.get(
    "/{chain_name}/streams/{stream_ref}/items",
    response_model=List[StreamItemResponse],
    name="api_list_stream_items",
    summary="List stream items",
    description="Returns a paginated list of items published to a stream. Accepts `start` and `count` query params.",
    responses={
        200: {"description": "Stream items"},
        404: {"description": "Stream not found"},
    },
)
async def list_stream_items(
    chain: ChainDep,
    service: BlockchainServiceDep,
    stream_ref: str = Path(..., description="Stream name or reference"),
    query_params: dict = Depends(get_query_params),
):
    """
    List items in a stream (JSON).
    """
    start, count = get_start_count(query_params)
    await _get_stream_or_raise(service, stream_ref)

    try:
        items = await service.call("liststreamitems", [stream_ref, True, count, start])
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Stream {stream_ref} not found")

    return [StreamItemResponse(**item) for item in (items or [])]
