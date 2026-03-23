"""
API Assets Router - JSON endpoints for asset-related operations.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path
from schemas.responses import AssetResponse, TransactionResponse

from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    get_query_params,
    get_page_count,
    get_start_count,
    raise_backend_http_error,
)

router = APIRouter(tags=["API Assets"])


async def _get_asset_or_raise(
    service: BlockchainServiceDep, asset_ref: str
) -> Dict[str, Any]:
    """Load an asset or raise the correct HTTP error."""
    try:
        asset = await service.get_asset(asset_ref)
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Asset {asset_ref} not found")

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_ref} not found")

    return asset


@router.get(
    "/{chain_name}/assets",
    response_model=List[AssetResponse],
    name="api_list_assets",
    summary="List assets",
    description="Returns a paginated list of all assets on the chain, sorted by name. Accepts `page` and `count` query params.",
    responses={
        200: {"description": "Paginated list of assets"},
        404: {"description": "Chain not found"},
    },
)
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
    try:
        assets = await service.call("listassets", ["*", True])
    except Exception as exc:
        raise_backend_http_error(exc)

    # Sort by name
    assets.sort(key=lambda x: x.get("name", ""))

    # Pagination
    page, count = get_page_count(query_params)

    page_info = pagination.get_pagination_info(
        total=len(assets),
        page=page,
        items_per_page=count,
    )

    paginated_assets = assets[
        page_info["start"] : page_info["start"] + page_info["count"]
    ]

    return [AssetResponse(**a) for a in paginated_assets]


@router.get(
    "/{chain_name}/assets/{asset_ref}",
    response_model=AssetResponse,
    name="api_get_asset",
    summary="Get asset",
    description="Fetch details for a single asset by name or reference.",
    responses={
        200: {"description": "Asset details"},
        404: {"description": "Asset not found"},
    },
)
async def get_asset(
    chain: ChainDep,
    service: BlockchainServiceDep,
    asset_ref: str = Path(..., description="Asset name or reference"),
):
    """
    Get asset details (JSON).
    """
    asset = await _get_asset_or_raise(service, asset_ref)

    return AssetResponse(**asset)


@router.get(
    "/{chain_name}/assets/{asset_ref}/transactions",
    response_model=List[TransactionResponse],
    name="api_list_asset_transactions",
    summary="List asset transactions",
    description="Returns a paginated list of transactions involving a specific asset. Accepts `start` and `count` query params.",
    responses={
        200: {"description": "Transactions for the asset"},
        404: {"description": "Asset not found"},
    },
)
async def list_asset_transactions(
    chain: ChainDep,
    service: BlockchainServiceDep,
    asset_ref: str = Path(..., description="Asset name or reference"),
    query_params: dict = Depends(get_query_params),
):
    """
    List transactions involving a specific asset (JSON).
    """
    start, count = get_start_count(query_params)
    await _get_asset_or_raise(service, asset_ref)

    try:
        tx_list = await service.call(
            "listassettransactions", [asset_ref, True, count, start]
        )
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Asset {asset_ref} not found")

    return [TransactionResponse(**tx) for tx in (tx_list or [])]
