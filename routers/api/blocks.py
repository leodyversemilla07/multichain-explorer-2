"""
API Blocks Router - JSON endpoints for block-related operations.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Path
from schemas.responses import BlockResponse

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PageCountDep,
    PaginationServiceDep,
    raise_backend_http_error,
)

router = APIRouter(tags=["API Blocks"])


async def _get_block_or_raise(service: BlockchainServiceDep, identifier: str) -> dict:
    """Load a block by height/hash or raise the correct HTTP error."""
    try:
        if identifier.isdigit():
            block = await service.get_block_by_height(int(identifier))
        elif len(identifier) == 64:
            block = await service.get_block_by_hash(identifier)
        else:
            raise HTTPException(status_code=400, detail="Invalid block identifier")
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Block {identifier} not found")

    if not block:
        raise HTTPException(status_code=404, detail=f"Block {identifier} not found")

    return block


@router.get(
    "/{chain_name}/blocks",
    response_model=List[BlockResponse],
    name="api_list_blocks",
    summary="List blocks",
    description="Returns a paginated list of blocks in the chain, newest first. Accepts `page` and `count` query params.",
    responses={
        200: {"description": "Paginated list of blocks"},
        404: {"description": "Chain not found"},
    },
)
async def list_blocks(
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    page_count: PageCountDep,
):
    """
    List blocks in the blockchain (JSON).
    """
    # Get blockchain info for total blocks
    try:
        info = await service.get_blockchain_info()
    except Exception as exc:
        raise_backend_http_error(exc)
    total_blocks = info.get("blocks", 0)

    # Apply pagination
    page, count = page_count

    page_info = pagination.get_pagination_info(
        total=total_blocks,
        page=page,
        items_per_page=count,
    )

    try:
        raw_blocks = await service.get_newest_blocks_page(
            total_blocks,
            start=page_info["start"],
            count=page_info["count"],
        )
    except Exception as exc:
        raise_backend_http_error(exc)

    return [BlockResponse.from_rpc_block(block) for block in raw_blocks]


@router.get(
    "/{chain_name}/blocks/{identifier}",
    response_model=BlockResponse,
    name="api_get_block",
    summary="Get block",
    description="Fetch a single block by height (integer) or hash (64-char hex string).",
    responses={
        200: {"description": "Block details"},
        400: {"description": "Invalid block identifier format"},
        404: {"description": "Block not found"},
    },
)
async def get_block(
    chain: ChainDep,
    service: BlockchainServiceDep,
    identifier: str = Path(..., description="Block height or hash"),
):
    """
    Get block details by height or hash (JSON).
    """
    block = await _get_block_or_raise(service, identifier)

    return BlockResponse.from_rpc_block(block)
