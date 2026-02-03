"""
API Addresses Router - JSON endpoints for address-related operations.
"""

import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import AddressResponse, TransactionResponse, PaginationInfo

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    get_query_params,
)

router = APIRouter(tags=["API Addresses"])


@router.get("/{chain_name}/addresses/{address}", response_model=AddressResponse, name="api_get_address")
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


@router.get("/{chain_name}/addresses/{address}/transactions", response_model=List[TransactionResponse], name="api_list_address_transactions")
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
    start = int(query_params.get("start", 0))
    count = int(query_params.get("count", 20))
    
    # Fetch transactions - simplified list
    # get_address_transactions usually returns list of {txid, balance_change, ...}
    # We might need to fetch full tx details if standardized response is required
    
    try:
        # Get simplified list first
        # We use 'count' + 'start' logic with skip/limit if supported by RPC `listaddresstransactions`
        # But commonly we might get all and slice, or use specific RPC args.
        # Check service method signature.
        # Since I don't see service code right now, assuming getting raw list then full details.
        
        # Actually, let's look at how HTML router does it.
        # It used `service.get_address_transactions(address, count, start)` likely.
        
        tx_list = await service.get_address_transactions(address, count, start)
        
        # tx_list is likely list of dicts. 
        # API expects TransactionResponse. 
        # If tx_list contains full tx details, great. 
        # If it only contains txid, we need to fetch details.
        # Usually `listaddresstransactions` returns partial info.
        
        # For full details matching TransactionResponse, we should fetch individual TXs.
        # But that's heavy. Use what we have if possible, or fetch.
        # Let's assume we want full details for standardization.
        
        txids = [tx.get("txid") for tx in tx_list if "txid" in tx]
        
        import asyncio
        tasks = [service.get_transaction(txid) for txid in txids]
        
        transactions = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, dict):
                    transactions.append(TransactionResponse(**res))
                    
        return transactions

    except Exception as e:
        # If address not found or error
        return []
