#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Assets Router - FastAPI routes for asset-related operations.

Handles:
- Asset listing
- Asset details
- Asset holders
- Asset transactions
- Asset issues
- Asset permissions
- Holder transactions
"""

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Path, Request, HTTPException
from fastapi.responses import HTMLResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    CommonContextDep,
    get_query_params,
    get_page_count,
    raise_backend_http_error,
)

router = APIRouter(tags=["Assets"])

_COUNT_FETCH_LIMIT = 100000


async def _get_asset_or_raise(service: BlockchainServiceDep, asset_name: str) -> Dict[str, Any]:
    """Load an asset and raise a typed HTTP error when it is unavailable."""
    try:
        assets = await service.call("listassets", [asset_name, True])
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Asset {asset_name} not found")

    if not assets:
        raise HTTPException(status_code=404, detail=f"Asset {asset_name} not found")

    return assets[0]


async def _validate_address(service: BlockchainServiceDep, address: str) -> None:
    """Validate holder addresses before rendering dependent pages."""
    try:
        address_info = await service.call("validateaddress", [address])
    except Exception as exc:
        raise_backend_http_error(exc)

    if not address_info or not address_info.get("isvalid"):
        raise HTTPException(status_code=404, detail=f"Address {address} not found")


async def _count_asset_transactions(service: BlockchainServiceDep, asset_name: str) -> int:
    """Estimate the total asset transactions by fetching a bounded full result set."""
    transactions = await service.call(
        "listassettransactions",
        [asset_name, False, _COUNT_FETCH_LIMIT, 0],
    )
    return len(transactions) if transactions else 0


@router.get("/{chain_name}/assets", response_class=HTMLResponse, name="assets",
            summary="List assets")
async def list_assets(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List all assets on the blockchain.
    """
    try:
        assets = await service.call("listassets", ["*", True])
        if not assets:
            assets = []
    except Exception as exc:
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    page_info = pagination.get_pagination_info(
        total=len(assets),
        page=page,
        items_per_page=count,
    )

    paginated_assets = assets[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = pagination.build_context(page_info, f"/{chain.path_name}/assets")

    return templates.TemplateResponse(
        name="pages/assets.html",
        context=context.build_context(
            title=f"Assets - {chain.display_name}",
            assets=paginated_assets,
            pagination=page_info,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}", response_class=HTMLResponse, name="asset",
            summary="Asset details")
async def asset_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
):
    """
    Show asset details.
    """
    asset = await _get_asset_or_raise(service, asset_name)

    return templates.TemplateResponse(
        name="pages/asset.html",
        context=context.build_context(
            title=f"Asset {asset_name}",
            asset=asset,
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/holders", response_class=HTMLResponse, name="asset_holders",
            summary="Asset holders")
async def asset_holders(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List asset holders.
    """
    await _get_asset_or_raise(service, asset_name)

    try:
        holders = await service.call("listassetholders", [asset_name])
        if not holders:
            holders = []
    except Exception as exc:
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    page_info = pagination.get_pagination_info(
        total=len(holders),
        page=page,
        items_per_page=count,
    )

    paginated_holders = holders[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/asset/{asset_name}/holders",
        include_component_fields=True,
        total_items=len(holders),
    )

    return templates.TemplateResponse(
        name="pages/asset_holders.html",
        context=context.build_context(
            title=f"Holders - {asset_name}",
            asset_name=asset_name,
            holders=paginated_holders,
            pagination=page_info,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/transactions", response_class=HTMLResponse, name="asset_transactions",
            summary="Asset transaction history")
async def asset_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List asset transactions.
    """
    await _get_asset_or_raise(service, asset_name)

    # Get transaction count
    try:
        total_count = await _count_asset_transactions(service, asset_name)
    except Exception as exc:
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    page_info = pagination.get_pagination_info(
        total=total_count,
        page=page,
        items_per_page=count,
    )

    transactions = []
    if total_count > 0:
        try:
            transactions = await service.call(
                "listassettransactions",
                [asset_name, True, page_info["count"], page_info["start"]],
            )
        except Exception as exc:
            raise_backend_http_error(exc)

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/asset/{asset_name}/transactions",
        include_component_fields=True,
        total_items=total_count,
    )

    return templates.TemplateResponse(
        name="pages/asset_transactions.html",
        context=context.build_context(
            title=f"Transactions - {asset_name}",
            asset_name=asset_name,
            transactions=transactions,
            pagination=page_info,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/issues", response_class=HTMLResponse, name="asset_issues",
            summary="Asset issuances")
async def asset_issues(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show asset issuance history.
    """
    asset = await _get_asset_or_raise(service, asset_name)
    issues = asset.get("issues", [])

    # Apply pagination
    page, count = get_page_count(query_params)

    page_info = pagination.get_pagination_info(
        total=len(issues),
        page=page,
        items_per_page=count,
    )

    paginated_issues = issues[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/asset/{asset_name}/issues",
        include_component_fields=True,
        total_items=len(issues),
    )

    return templates.TemplateResponse(
        name="pages/asset_issues.html",
        context=context.build_context(
            title=f"Issuances - {asset_name}",
            asset_name=asset_name,
            issues=paginated_issues,
            pagination=page_info,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/permissions", response_class=HTMLResponse, name="asset_permissions",
            summary="Asset permissions")
async def asset_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
):
    """
    Show asset permissions.
    """
    await _get_asset_or_raise(service, asset_name)

    try:
        permissions = await service.call("listpermissions", [asset_name])
        if not permissions:
            permissions = []
    except Exception as exc:
        raise_backend_http_error(exc)

    return templates.TemplateResponse(
        name="pages/asset_permissions.html",
        context=context.build_context(
            title=f"Permissions - {asset_name}",
            asset_name=asset_name,
            permissions=permissions,
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/holder/{address}/transactions",
            response_class=HTMLResponse, name="holder_transactions",
            summary="Holder transaction history")
async def holder_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    address: str = Path(..., min_length=26, max_length=52, description="Holder address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List transactions for a specific asset holder.
    """
    await _get_asset_or_raise(service, asset_name)
    await _validate_address(service, address)

    def output_matches_asset(output: Dict[str, Any]) -> bool:
        """Match either legacy flat asset fields or nested MultiChain asset entries."""
        if output.get("assetref") == asset_name or output.get("asset") == asset_name:
            return True

        for asset in output.get("assets", []) or []:
            if (
                asset.get("assetref") == asset_name
                or asset.get("name") == asset_name
                or asset.get("asset") == asset_name
            ):
                return True
        return False

    # Get transactions
    try:
        # Note: inefficient to fetch all address transactions to filter by asset.
        all_txs = await service.call("listaddresstransactions", [address, 1000, 0, True])
        if not all_txs:
            all_txs = []
        # Filter transactions for this specific asset
        # Match both nested assets arrays and legacy flattened output fields.
        transactions = [
            tx
            for tx in all_txs
            if any(output_matches_asset(item) for item in tx.get("vout", []))
        ]
    except Exception as exc:
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    page_info = pagination.get_pagination_info(
        total=len(transactions),
        page=page,
        items_per_page=count,
    )

    paginated_txs = transactions[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/asset/{asset_name}/holder/{address}/transactions",
        include_component_fields=True,
        total_items=len(transactions),
    )

    return templates.TemplateResponse(
        name="pages/asset_holder_transactions.html",
        context=context.build_context(
            title=f"Transactions - {asset_name} - {address[:16]}...",
            asset_name=asset_name,
            address=address,
            transactions=paginated_txs,
            pagination=page_info,
            **pagination_context
        ),
    )


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/assets", response_class=HTMLResponse, name="legacy_assets", include_in_schema=False)
async def legacy_list_assets(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy assets list route."""
    return await list_assets(request, chain, service, pagination, templates, context, query_params)


@router.get("/chain/{chain_name}/asset/{asset_name}", response_class=HTMLResponse, name="legacy_asset", include_in_schema=False)
async def legacy_asset_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(..., min_length=1, max_length=32),
):
    """Legacy asset detail route."""
    return await asset_detail(request, chain, service, templates, context, asset_name)
