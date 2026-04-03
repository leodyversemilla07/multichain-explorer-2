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

from typing import Dict, Any

from fastapi import APIRouter, Depends, Path, Request, HTTPException
from fastapi.responses import HTMLResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    CommonContextDep,
    get_query_params_dep,
    get_page_count,
    raise_backend_http_error,
)

router = APIRouter(tags=["Assets"])


async def _get_asset_or_raise(
    service: BlockchainServiceDep, asset_name: str
) -> Dict[str, Any]:
    """Load an asset and raise a typed HTTP error when it is unavailable."""
    try:
        asset = await service.get_asset(asset_name)
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Asset {asset_name} not found")

    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_name} not found")

    return asset


async def _validate_address(service: BlockchainServiceDep, address: str) -> None:
    """Validate holder addresses before rendering dependent pages."""
    try:
        address_info = await service.call("validateaddress", [address])
    except Exception as exc:
        raise_backend_http_error(exc)

    if not address_info or not address_info.get("isvalid"):
        raise HTTPException(status_code=404, detail=f"Address {address} not found")


async def _count_asset_transactions(
    service: BlockchainServiceDep, asset_name: str
) -> int:
    """Count asset transactions using the shared bounded list-count fallback."""
    return await service.count_asset_transactions(asset_name)


@router.get(
    "/{chain_name}/assets",
    response_class=HTMLResponse,
    name="assets",
    summary="List assets",
)
async def list_assets(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List all assets on the blockchain.
    """
    try:
        assets = await service.get_all_assets()
    except Exception as exc:
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    paginated_assets, page_info = pagination.paginate(
        assets,
        page=page,
        items_per_page=count,
    )

    pagination_context = pagination.build_context(
        page_info, f"/{chain.path_name}/assets"
    )

    return templates.TemplateResponse(
        name="pages/assets.html",
        context=context.build_context(
            title=f"Assets - {chain.display_name}",
            assets=paginated_assets,
            pagination=page_info,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/asset/{asset_name}",
    response_class=HTMLResponse,
    name="asset",
    summary="Asset details",
)
async def asset_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(
        ..., min_length=1, max_length=32, description="Asset name or reference"
    ),
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


@router.get(
    "/{chain_name}/asset/{asset_name}/holders",
    response_class=HTMLResponse,
    name="asset_holders",
    summary="Asset holders",
)
async def asset_holders(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(
        ..., min_length=1, max_length=32, description="Asset name or reference"
    ),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List asset holders.
    """
    await _get_asset_or_raise(service, asset_name)

    try:
        holders = await service.get_asset_holders(asset_name)
    except Exception as exc:
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    page_info = pagination.get_pagination_info(
        total=len(holders),
        page=page,
        items_per_page=count,
    )

    paginated_holders = holders[
        page_info["start"] : page_info["start"] + page_info["count"]
    ]

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
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/asset/{asset_name}/transactions",
    response_class=HTMLResponse,
    name="asset_transactions",
    summary="Asset transaction history",
)
async def asset_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(
        ..., min_length=1, max_length=32, description="Asset name or reference"
    ),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
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
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/asset/{asset_name}/issues",
    response_class=HTMLResponse,
    name="asset_issues",
    summary="Asset issuances",
)
async def asset_issues(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(
        ..., min_length=1, max_length=32, description="Asset name or reference"
    ),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
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

    paginated_issues = issues[
        page_info["start"] : page_info["start"] + page_info["count"]
    ]

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
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/asset/{asset_name}/permissions",
    response_class=HTMLResponse,
    name="asset_permissions",
    summary="Asset permissions",
)
async def asset_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(
        ..., min_length=1, max_length=32, description="Asset name or reference"
    ),
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


@router.get(
    "/{chain_name}/asset/{asset_name}/holder/{address}/transactions",
    response_class=HTMLResponse,
    name="holder_transactions",
    summary="Holder transaction history",
)
async def holder_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    asset_name: str = Path(
        ..., min_length=1, max_length=32, description="Asset name or reference"
    ),
    address: str = Path(
        ..., min_length=26, max_length=52, description="Holder address"
    ),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List transactions for a specific asset holder.
    """
    await _get_asset_or_raise(service, asset_name)
    await _validate_address(service, address)

    # Get transactions
    try:
        transactions = await service.get_asset_holder_transactions(asset_name, address)
    except Exception as exc:
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    page_info = pagination.get_pagination_info(
        total=len(transactions),
        page=page,
        items_per_page=count,
    )

    paginated_txs = transactions[
        page_info["start"] : page_info["start"] + page_info["count"]
    ]

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
            **pagination_context,
        ),
    )


# Legacy routes for backward compatibility
@router.get(
    "/chain/{chain_name}/assets",
    response_class=HTMLResponse,
    name="legacy_assets",
    include_in_schema=False,
)
async def legacy_list_assets(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """Legacy assets list route."""
    return await list_assets(
        request, chain, service, pagination, templates, context, query_params
    )


@router.get(
    "/chain/{chain_name}/asset/{asset_name}",
    response_class=HTMLResponse,
    name="legacy_asset",
    include_in_schema=False,
)
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
