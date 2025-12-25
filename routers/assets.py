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
)

router = APIRouter(tags=["Assets"])


@router.get("/{chain_name}/assets", response_class=HTMLResponse, name="assets")
def list_assets(
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
        assets = service.call("listassets", ["*", True])
        if not assets:
            assets = []
    except Exception as e:
        # TODO: Log error?
        assets = []

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(assets),
        page=page,
        items_per_page=count,
    )

    paginated_assets = assets[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/assets",
    }

    return templates.TemplateResponse(
        name="pages/assets.html",
        context=context.build_context(
            title=f"Assets - {chain.config['display-name']}",
            assets=paginated_assets,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}", response_class=HTMLResponse, name="asset")
def asset_detail(
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
    try:
        assets = service.call("listassets", [asset_name, True])
        if not assets or len(assets) == 0:
            raise HTTPException(status_code=404, detail=f"Asset {asset_name} not found")
        asset = assets[0]
    except Exception:
        raise HTTPException(status_code=404, detail=f"Asset {asset_name} not found")

    return templates.TemplateResponse(
        name="pages/asset.html",
        context=context.build_context(
            title=f"Asset {asset_name}",
            asset=asset,
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/holders", response_class=HTMLResponse, name="asset_holders")
def asset_holders(
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
    try:
        holders = service.call("listassetholders", [asset_name])
        if not holders:
            holders = []
    except Exception:
        holders = []

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(holders),
        page=page,
        items_per_page=count,
    )

    paginated_holders = holders[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/asset/{asset_name}/holders",
    }

    return templates.TemplateResponse(
        name="pages/asset_holders.html",
        context=context.build_context(
            title=f"Holders - {asset_name}",
            asset_name=asset_name,
            holders=paginated_holders,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/transactions", response_class=HTMLResponse, name="asset_transactions")
def asset_transactions(
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
    # Get transaction count
    try:
        count_txs = service.call("listassettransactions", [asset_name, False, 1, 0])
        total_count = len(count_txs) if count_txs else 0
    except Exception:
        total_count = 0

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=total_count,
        page=page,
        items_per_page=count,
    )

    transactions = []
    if total_count > 0:
        try:
            transactions = service.call(
                "listassettransactions",
                [asset_name, True, page_info["count"], page_info["start"]],
            )
        except Exception:
            transactions = []

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/asset/{asset_name}/transactions",
    }

    return templates.TemplateResponse(
        name="pages/asset_transactions.html",
        context=context.build_context(
            title=f"Transactions - {asset_name}",
            asset_name=asset_name,
            transactions=transactions,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/issues", response_class=HTMLResponse, name="asset_issues")
def asset_issues(
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
    try:
        assets = service.call("listassets", [asset_name, True])
        if assets and len(assets) > 0:
            asset = assets[0]
            issues = asset.get("issues", [])
        else:
            issues = []
    except Exception:
        issues = []

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(issues),
        page=page,
        items_per_page=count,
    )

    paginated_issues = issues[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/asset/{asset_name}/issues",
    }

    return templates.TemplateResponse(
        name="pages/asset_issues.html",
        context=context.build_context(
            title=f"Issuances - {asset_name}",
            asset_name=asset_name,
            issues=paginated_issues,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/permissions", response_class=HTMLResponse, name="asset_permissions")
def asset_permissions(
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
    try:
        # Verify asset exists first
        assets = service.call("listassets", [asset_name, True])
        if not assets or len(assets) == 0:
            permissions = []
        else:
            # Get addresses with permissions for this asset
            # listpermissions for asset? Usually listpermissions stream|admin...
            # The handler used `listpermissions [asset_name]`. Assuming correct.
            permissions = service.call("listpermissions", [asset_name])
            if not permissions:
                permissions = []
    except Exception:
        permissions = []

    return templates.TemplateResponse(
        name="pages/asset_permissions.html",
        context=context.build_context(
            title=f"Permissions - {asset_name}",
            asset_name=asset_name,
            permissions=permissions,
        ),
    )


@router.get("/{chain_name}/asset/{asset_name}/holder/{address}/transactions", response_class=HTMLResponse, name="holder_transactions")
def holder_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    address: str = Path(..., min_length=26, max_length=35, description="Holder address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List transactions for a specific asset holder.
    """
    # Get transactions
    try:
        # Note: inefficient to fetch all address transactions to filter by asset.
        all_txs = service.call("listaddresstransactions", [address, 1000, 0, True])
        if not all_txs:
            all_txs = []
        # Filter transactions for this specific asset
        # Check vout for assetref or asset name
        transactions = [
            tx
            for tx in all_txs
            if any(
                item.get("assetref") == asset_name or item.get("asset") == asset_name
                for item in tx.get("vout", [])
            )
        ]
    except Exception:
        transactions = []

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(transactions),
        page=page,
        items_per_page=count,
    )

    paginated_txs = transactions[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/asset/{asset_name}/holder/{address}/transactions",
    }

    return templates.TemplateResponse(
        name="pages/asset_holder_transactions.html",
        context=context.build_context(
            title=f"Transactions - {asset_name} - {address[:16]}...",
            asset_name=asset_name,
            address=address,
            transactions=paginated_txs,
            **pagination_context
        ),
    )


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/assets", response_class=HTMLResponse, name="legacy_assets", include_in_schema=False)
def legacy_list_assets(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy assets list route."""
    return list_assets(request, chain, service, pagination, templates, context, query_params)


@router.get("/chain/{chain_name}/asset/{asset_name}", response_class=HTMLResponse, name="legacy_asset", include_in_schema=False)
def legacy_asset_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(..., min_length=1, max_length=32),
):
    """Legacy asset detail route."""
    return asset_detail(request, chain, service, templates, context, asset_name)
