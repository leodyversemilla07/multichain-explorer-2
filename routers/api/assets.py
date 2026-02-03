"""
API Assets Router - JSON endpoints for asset-related operations.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import AssetResponse, TransactionResponse, PaginationInfo

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    get_query_params,
)

router = APIRouter(tags=["API Assets"])


@router.get("/{chain_name}/assets", response_model=List[AssetResponse], name="api_list_assets")
async def list_assets(
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    query_params: dict = Depends(get_query_params),
):
    """
    List assets in the blockchain (JSON).
    """
    # Fetch all assets
    # listassets returns list of dicts.
    assets = await service.call("listassets", ["*", True])
    
    # Sort by name
    assets.sort(key=lambda x: x.get("name", ""))
    
    # Pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))
    
    page_info = pagination.get_pagination_info(
        total=len(assets),
        page=page,
        items_per_page=count,
    )
    
    paginated_assets = assets[page_info["start"] : page_info["start"] + page_info["count"]]
    
    return [AssetResponse(**a) for a in paginated_assets]


@router.get("/{chain_name}/assets/{asset_ref}", response_model=AssetResponse, name="api_get_asset")
async def get_asset(
    chain: ChainDep,
    service: BlockchainServiceDep,
    asset_ref: str = Path(..., description="Asset name or reference"),
):
    """
    Get asset details (JSON).
    """
    # Fetch specific asset
    # listassets with name/ref
    assets = await service.call("listassets", [asset_ref, True])
    
    if not assets:
        raise HTTPException(status_code=404, detail=f"Asset {asset_ref} not found")
        
    # Should be single result exactly matching
    asset = assets[0]
    
    return AssetResponse(**asset)


@router.get("/{chain_name}/assets/{asset_ref}/transactions", response_model=List[TransactionResponse], name="api_list_asset_transactions")
async def list_asset_transactions(
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    asset_ref: str = Path(..., description="Asset name or reference"),
    query_params: dict = Depends(get_query_params),
):
    """
    List transactions involving a specific asset (JSON).
    """
    # Apply pagination
    count = int(query_params.get("count", 20))
    start = int(query_params.get("start", 0))
    
    # listassettransactions
    tx_list = await service.call("listassettransactions", [asset_ref, True, count, start])
    
    if not tx_list:
        return []
        
    # Only TXIDs are usually returned or partial info.
    # Check if we need to fetch full details.
    # Assuming we do for consistency.
    
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
