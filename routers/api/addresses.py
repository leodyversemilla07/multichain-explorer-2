"""
API Addresses Router - JSON endpoints for address-related operations.
"""

import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import AddressResponse, TransactionResponse
from exceptions import ChainConnectionError, RPCError

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    get_query_params,
    get_start_count,
    raise_backend_http_error,
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
    try:
        address_info = await service.call("validateaddress", [address])
        if not address_info or not address_info.get("isvalid", False):
            raise HTTPException(status_code=404, detail=f"Address {address} not found")

        summary = await service.get_address_summary(address)
    except Exception as exc:
        raise_backend_http_error(exc)

    if not summary:
        raise HTTPException(status_code=404, detail=f"Address {address} not found")

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
    address: str = Path(..., description="Wallet address"),
    query_params: dict = Depends(get_query_params),
):
    """
    List transactions for a specific address (JSON).
    """
    # Apply pagination
    start, count = get_start_count(query_params)

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
    except (ChainConnectionError, RPCError) as exc:
        raise_backend_http_error(exc)
