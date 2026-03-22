"""
API Addresses Router - JSON endpoints for address-related operations.
"""

import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import AddressResponse, TransactionResponse, PaginationInfo
from exceptions import ChainConnectionError, RPCError

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    get_query_params,
    safe_int,
)

router = APIRouter(tags=["API Addresses"])


@router.get(
    "/{chain_name}/addresses/{address}",
    response_model=AddressResponse,
    name="api_get_address",
    summary="Get address",
    description="Fetch balances, permissions, and transaction count for a wallet address.",
    responses={
        200: {"description": "Address details"},
        404: {"description": "Address not found or invalid"},
    },
)
async def get_address(
    chain: ChainDep,
    service: BlockchainServiceDep,
    address: str = Path(..., description="Wallet address"),
):
    """
    Get address details (JSON).
    
    Fetches info, balances, and permissions in parallel.
    """
    # Fetch comprehensive summary from service
    summary = await service.get_address_summary(address)
    
    if not summary:
        # Should not happen as get_address_summary handles errors
        raise HTTPException(status_code=404, detail=f"Address {address} not found")
        
    # Check if we have valid data (at least address should be there)
    # If it's an empty dict or just permissions, it might be invalid
    if not summary.get("address"):
        raise HTTPException(status_code=404, detail="Invalid address")
        
    return AddressResponse(**summary)


@router.get(
    "/{chain_name}/addresses/{address}/transactions",
    response_model=List[TransactionResponse],
    name="api_list_address_transactions",
    summary="List address transactions",
    description="Returns a paginated list of transactions involving this address. Accepts `start` and `count` query params.",
    responses={
        200: {"description": "Transactions for the address"},
        404: {"description": "Address not found"},
        502: {"description": "RPC error while fetching address transactions"},
        503: {"description": "Chain connection unavailable"},
    },
)
async def list_address_transactions(
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    address: str = Path(..., description="Wallet address"),
    query_params: dict = Depends(get_query_params),
):
    """
    List transactions for a specific address (JSON).
    """
    # Apply pagination
    start = safe_int(query_params.get("start", 0), 0)
    count = safe_int(query_params.get("count", 20), 20)

    try:
        address_info = await service.call("validateaddress", [address])
        if not address_info or not address_info.get("isvalid", False):
            raise HTTPException(status_code=404, detail=f"Address {address} not found")

        tx_list = await service.get_address_transactions(address, count, start)
        txids = [tx.get("txid") for tx in tx_list if "txid" in tx]
        tasks = [service.get_transaction(txid) for txid in txids]

        transactions = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, dict):
                    transactions.append(TransactionResponse(**res))
        return transactions
    except HTTPException:
        raise
    except ChainConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RPCError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
