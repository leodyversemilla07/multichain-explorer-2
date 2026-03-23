"""
API Transactions Router - JSON endpoints for transaction-related operations.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import TransactionResponse

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    get_query_params,
    get_start_count,
    raise_backend_http_error,
)

router = APIRouter(tags=["API Transactions"])


@router.get(
    "/{chain_name}/transactions/{txid}",
    response_model=TransactionResponse,
    name="api_get_transaction",
    summary="Get transaction",
    description="Fetch full transaction details by TXID.",
    responses={
        200: {"description": "Transaction details"},
        404: {"description": "Transaction not found"},
    },
)
async def get_transaction(
    chain: ChainDep,
    service: BlockchainServiceDep,
    txid: str = Path(..., description="Transaction ID"),
):
    """
    Get transaction details by ID (JSON).
    """
    try:
        tx = await service.get_transaction(txid)
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Transaction {txid} not found")
    
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")

    return TransactionResponse(**tx)


@router.get(
    "/{chain_name}/blocks/{height}/transactions",
    response_model=List[TransactionResponse],
    name="api_list_block_transactions",
    summary="List transactions in a block",
    description="Returns a paginated list of transactions in a block by height. Accepts `start` and `count` query params.",
    responses={
        200: {"description": "Transactions in the specified block"},
        404: {"description": "Block not found"},
    },
)
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
    try:
        block_hash = await service.get_block_hash(height)
        block = await service.get_block(block_hash)
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Block #{height} not found")
    if not block:
        raise HTTPException(status_code=404, detail=f"Block #{height} not found")

    # Get transactions
    tx_ids = block.get("tx", [])
    if not tx_ids:
        return []

    # Apply pagination
    start, count = get_start_count(query_params)

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
