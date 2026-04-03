"""
API Addresses Router - JSON endpoints for address-related operations.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Path
from schemas.responses import AddressResponse, TransactionResponse
from exceptions import ChainConnectionError, RPCError

from routers.api.helpers import load_transaction_responses
from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    StartCountDep,
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
    description="Returns a paginated list of transactions involving this address. Accepts `page` and `count` query params, with legacy `start` support.",
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
    start_count: StartCountDep,
    address: str = Path(..., description="Wallet address"),
):
    """
    List transactions for a specific address (JSON).
    """
    # Apply pagination
    start, count = start_count

    try:
        address_info = await service.call("validateaddress", [address])
        if not address_info or not address_info.get("isvalid", False):
            raise HTTPException(status_code=404, detail=f"Address {address} not found")

        tx_list = await service.get_address_transactions(address, count, start)
        txids = [tx.get("txid") for tx in tx_list if "txid" in tx]
        return await load_transaction_responses(service, txids)
    except HTTPException:
        raise
    except (ChainConnectionError, RPCError) as exc:
        raise_backend_http_error(exc)
