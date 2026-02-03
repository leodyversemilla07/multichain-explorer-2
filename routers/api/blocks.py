"""
API Blocks Router - JSON endpoints for block-related operations.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import BlockResponse, PaginationInfo

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    get_query_params,
)

router = APIRouter(tags=["API Blocks"])


@router.get("/{chain_name}/blocks", response_model=List[BlockResponse], name="api_list_blocks")
async def list_blocks(
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    query_params: dict = Depends(get_query_params),
):
    """
    List blocks in the blockchain (JSON).
    """
    # Get blockchain info for total blocks
    info = await service.get_blockchain_info()
    total_blocks = info.get("blocks", 0)

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=total_blocks,
        page=page,
        items_per_page=count,
    )

    # Calculate block range for newest-first display
    end_height = total_blocks - 1 - page_info["start"]
    start_height = max(0, end_height - page_info["count"] + 1)
    blocks_to_fetch = end_height - start_height + 1
    
    blocks = []
    if blocks_to_fetch > 0 and start_height <= end_height:
        # Batch fetch blocks
        raw_blocks = await service.list_blocks(start_height, blocks_to_fetch)
        # Sort blocks by height descending (newest first)
        raw_blocks.sort(key=lambda x: x.get("height", 0), reverse=True)
        
        # Map to Reponse Model
        for b in raw_blocks:
            # Helper to map fields if needed
            block_data = b.copy()
            if "tx" in block_data:
                block_data["transactions"] = block_data.pop("tx")
            if "nTx" in block_data:
                block_data["tx_count"] = block_data.pop("nTx")
            elif "transactions" in block_data:
                block_data["tx_count"] = len(block_data["transactions"])
            
            blocks.append(BlockResponse(**block_data))

    return blocks


@router.get("/{chain_name}/blocks/{identifier}", response_model=BlockResponse, name="api_get_block")
async def get_block(
    chain: ChainDep,
    service: BlockchainServiceDep,
    identifier: str = Path(..., description="Block height or hash"),
):
    """
    Get block details by height or hash (JSON).
    """
    # Determine if identifier is a height (numeric) or hash (64 hex chars)
    block = None
    if identifier.isdigit():
        height = int(identifier)
        block = await service.get_block_by_height(height)
    elif len(identifier) == 64:
        block = await service.get_block_by_hash(identifier)
    else:
        raise HTTPException(status_code=400, detail="Invalid block identifier")

    if not block:
        raise HTTPException(status_code=404, detail=f"Block {identifier} not found")

    # Map fields
    block_data = block.copy()
    if "tx" in block_data:
        block_data["transactions"] = block_data.pop("tx")
    if "nTx" in block_data:
        block_data["tx_count"] = block_data.pop("nTx")
    elif "transactions" in block_data:
        block_data["tx_count"] = len(block_data["transactions"])

    return BlockResponse(**block_data)
