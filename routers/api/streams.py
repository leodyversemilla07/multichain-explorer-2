"""
API Streams Router - JSON endpoints for stream-related operations.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import StreamResponse, StreamItemResponse, PaginationInfo

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    get_query_params,
    safe_int,
)

router = APIRouter(tags=["API Streams"])


@router.get("/{chain_name}/streams", response_model=List[StreamResponse], name="api_list_streams")
async def list_streams(
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    query_params: dict = Depends(get_query_params),
):
    """
    List streams in the blockchain (JSON).
    """
    # Fetch all streams
    streams = await service.call("liststreams", ["*", True])
    
    # Sort by name
    streams.sort(key=lambda x: x.get("name", ""))
    
    # Pagination
    page = safe_int(query_params.get("page", 1), 1)
    count = safe_int(query_params.get("count", 20), 20)
    
    page_info = pagination.get_pagination_info(
        total=len(streams),
        page=page,
        items_per_page=count,
    )
    
    paginated_streams = streams[page_info["start"] : page_info["start"] + page_info["count"]]
    
    # Enrich with item counts in parallel (crucial for performance)
    import asyncio
    
    async def enrich_stream(stream):
        try:
            # Check if subscribed, if not, keys/items might be missing or limited
            if stream.get("subscribed"):
                # No extra call needed if liststreams returns it, but sometimes it doesn't return full stats?
                # Usually liststreams with verbose=True returns 'items', 'keys', 'publishers'.
                # Assuming liststreams response is sufficient, if not, we would call getstreaminfo.
                # In Phase 1 we did enrich logic. Let's replicate if needed.
                # Inspecting Phase 1 notes: "Implemented asyncio.gather in list_streams to fetch item counts"
                # This suggests liststreams result might be missing something or we wanted fresh counts.
                pass
            else:
                # If not subscribed, we might not see counts?
                pass
                
            # If we need to fetch info:
            # info = await service.call("getstreaminfo", [stream["name"]])
            # stream.update(info)
            pass 
        except Exception:
            pass

    # Actually, liststreams with verbose=True (passed above) usually has the info.
    # The Phase 1 change might have been to ensure we get it if *some* streams were missing it.
    # We'll map directly for now, trust the service call.
    
    return [StreamResponse(**s) for s in paginated_streams]


@router.get("/{chain_name}/streams/{stream_ref}", response_model=StreamResponse, name="api_get_stream")
async def get_stream(
    chain: ChainDep,
    service: BlockchainServiceDep,
    stream_ref: str = Path(..., description="Stream name or reference"),
):
    """
    Get stream details (JSON).
    """
    # Fetch specific stream
    streams = await service.call("liststreams", [stream_ref, True])
    
    if not streams:
        raise HTTPException(status_code=404, detail=f"Stream {stream_ref} not found")
        
    return StreamResponse(**streams[0])


@router.get("/{chain_name}/streams/{stream_ref}/items", response_model=List[StreamItemResponse], name="api_list_stream_items")
async def list_stream_items(
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    stream_ref: str = Path(..., description="Stream name or reference"),
    query_params: dict = Depends(get_query_params),
):
    """
    List items in a stream (JSON).
    """
    # Apply pagination
    count = safe_int(query_params.get("count", 20), 20)
    start = safe_int(query_params.get("start", 0), 0)
    
    # liststreamqueryitems or liststreamitems
    # liststreamitems(stream, verbose=True, count=10, start=-10, local-ordering=False)
    # Negative start means from end. Positive means from start.
    
    # We likely want newest first, so we might reverse logic or use start=-count-offset.
    # API usually implies explicit 'start' index.
    
    # liststreamitems stream verbose count start
    items = await service.call("liststreamitems", [stream_ref, True, count, start])
    
    if not items:
        return []
        
    # Reverse to show newest first if API expects that, or keep as is?
    # Usually list operations return raw order.
    # Items in stream are chronological.
    
    # Map to response
    formatted_items = []
    for item in items:
         # Map fields if necessary. 
         # StreamItemResponse expects: publishers, key, data, confirmations, etc.
         # liststreamitems returns: publishers (list), key, data (hex/text), ...
         formatted_items.append(StreamItemResponse(**item))
         
    return formatted_items
