"""
API Transactions Router - JSON endpoints for transaction-related operations.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import TransactionResponse, PaginationInfo

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    get_query_params,
)

router = APIRouter(tags=["API Transactions"])


@router.get("/{chain_name}/transactions/{txid}", response_model=TransactionResponse, name="api_get_transaction")
async def get_transaction(
    chain: ChainDep,
    service: BlockchainServiceDep,
    txid: str = Path(..., description="Transaction ID"),
):
    """
    Get transaction details by ID (JSON).
    """
    tx = await service.get_transaction(txid)
    
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")

    return TransactionResponse(**tx)


@router.get("/{chain_name}/blocks/{height}/transactions", response_model=List[TransactionResponse], name="api_list_block_transactions")
async def list_block_transactions(
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    height: int = Path(..., description="Block height"),
    query_params: dict = Depends(get_query_params),
):
    """
    List transactions in a specific block (JSON).
    """
    # Get block
    block = await service.get_block_by_height(height)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block #{height} not found")

    # Get transactions
    tx_ids = block.get("tx", [])
    if not tx_ids:
        return []

    # Apply pagination
    start = int(query_params.get("start", 0))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(tx_ids),
        start=start,
        count=count,
    )

    paginated_tx_ids = tx_ids[page_info["start"] : page_info["start"] + page_info["count"]]
    
    # Concurrent fetch
    import asyncio
    tasks = [service.get_transaction(tx_id) for tx_id in paginated_tx_ids]
    
    transactions = []
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, dict):
                transactions.append(TransactionResponse(**res))
                
    return transactions
