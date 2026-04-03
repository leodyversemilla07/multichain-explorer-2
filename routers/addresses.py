#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Addresses Router - FastAPI routes for address-related operations.

Handles:
- Address listing
- Address details
- Address transactions
- Address assets
- Address streams
- Address permissions
"""

import asyncio
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

router = APIRouter(tags=["Addresses"])


async def _validate_address(
    service: BlockchainServiceDep, address: str
) -> Dict[str, Any]:
    """Validate an address before rendering dependent pages."""
    try:
        address_info = await service.call("validateaddress", [address])
    except Exception as exc:
        raise_backend_http_error(exc)

    if not address_info or not address_info.get("isvalid"):
        raise HTTPException(status_code=404, detail=f"Address {address} not found")

    return address_info


@router.get("/{chain_name}/addresses", response_class=HTMLResponse, name="addresses")
async def list_addresses(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List addresses with balances.

    Displays addresses that have activity on the blockchain.
    """
    # Get total address count
    try:
        addresses = await service.call("listaddresses", ["*", True])
        if not addresses:
            addresses = []
    except Exception as exc:
        raise_backend_http_error(exc)

    # Apply pagination
    page, count = get_page_count(query_params)

    paginated_addresses, page_info = pagination.paginate(
        addresses,
        page=page,
        items_per_page=count,
    )

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/addresses",
        include_component_fields=True,
        total_items=len(addresses),
    )

    return templates.TemplateResponse(
        name="pages/addresses.html",
        context=context.build_context(
            title=f"Addresses - {chain.display_name}",
            addresses=paginated_addresses,
            pagination=page_info,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/address/{address}", response_class=HTMLResponse, name="address"
)
async def address_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(
        ..., min_length=26, max_length=52, description="Blockchain address"
    ),
):
    """
    Show address details.
    """
    address_info = await _validate_address(service, address)

    # Fetch dependent address data in parallel after validation.
    async def fetch_balances():
        return await service.get_address_balances(address)

    async def fetch_permissions():
        return await service.get_address_permissions(address)

    async def fetch_transactions():
        return await service.call("listaddresstransactions", [address, 10, 0, True])

    async def fetch_tx_count():
        return await service.count_address_transactions(address)

    results = await asyncio.gather(
        fetch_balances(),
        fetch_permissions(),
        fetch_transactions(),
        fetch_tx_count(),
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            raise_backend_http_error(result)

    balances = results[0] or []
    permissions = results[1] or []
    transactions = results[2] or []
    transactions_count = results[3] or 0

    address_summary = dict(address_info)
    address_summary["balances"] = balances
    address_summary["permissions"] = permissions

    return templates.TemplateResponse(
        name="pages/address.html",
        context=context.build_context(
            title=f"Address - {chain.display_name}",
            address=address,
            address_info=address_summary,
            address_data=address_summary,
            balances=balances,
            assets=balances,
            permissions=permissions,
            transactions=transactions,
            transactions_count=transactions_count,
        ),
    )


@router.get(
    "/{chain_name}/address/{address}/transactions",
    response_class=HTMLResponse,
    name="address_transactions",
)
async def address_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(
        ..., min_length=26, max_length=52, description="Blockchain address"
    ),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List transactions for an address.
    """
    await _validate_address(service, address)

    # Get total count first
    try:
        total_count = await service.count_address_transactions(address)
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
        # Get transactions for this page
        try:
            transactions = await service.call(
                "listaddresstransactions",
                [address, page_info["count"], page_info["start"], True],
            )
            if not transactions:
                transactions = []
        except Exception as exc:
            raise_backend_http_error(exc)

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/address/{address}/transactions",
        include_component_fields=True,
        total_items=total_count,
    )

    return templates.TemplateResponse(
        name="pages/address_transactions.html",
        context=context.build_context(
            title=f"Transactions - {address[:16]}...",
            address=address,
            transactions=transactions,
            pagination=page_info,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/address/{address}/assets",
    response_class=HTMLResponse,
    name="address_assets",
)
async def address_assets(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(
        ..., min_length=26, max_length=52, description="Blockchain address"
    ),
):
    """
    List assets held by an address.
    """
    await _validate_address(service, address)

    try:
        balances = await service.get_address_balances(address)
    except Exception as exc:
        raise_backend_http_error(exc)

    return templates.TemplateResponse(
        name="pages/address_assets.html",
        context=context.build_context(
            title=f"Assets - {address[:16]}...",
            address=address,
            assets=balances or [],
        ),
    )


@router.get(
    "/{chain_name}/address/{address}/streams",
    response_class=HTMLResponse,
    name="address_streams",
)
async def address_streams(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(
        ..., min_length=26, max_length=52, description="Blockchain address"
    ),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List streams associated with an address.
    """
    await _validate_address(service, address)

    # Get all streams to count them
    try:
        total_count = await service.count_address_streams(address)
    except Exception as exc:
        raise_backend_http_error(exc)

    page, count = get_page_count(query_params)
    page_info = pagination.get_pagination_info(
        total=total_count,
        page=page,
        items_per_page=count,
    )
    streams = []

    if total_count > 0:
        # Get streams for this page
        try:
            streams = await service.call(
                "explorerlistaddressstreams",
                [address, True, page_info["count"], page_info["start"]],
            )
            if not streams:
                streams = []
        except Exception as exc:
            raise_backend_http_error(exc)

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/address/{address}/streams",
        include_component_fields=True,
        total_items=total_count,
    )

    return templates.TemplateResponse(
        name="pages/address_streams.html",
        context=context.build_context(
            title=f"Streams - {address[:16]}...",
            address=address,
            streams=streams,
            pagination=page_info,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/address/{address}/permissions",
    response_class=HTMLResponse,
    name="address_permissions",
)
async def address_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(
        ..., min_length=26, max_length=52, description="Blockchain address"
    ),
):
    """
    List permissions for an address.
    """
    await _validate_address(service, address)

    try:
        permissions = await service.call("listpermissions", ["*", address])
    except Exception as exc:
        raise_backend_http_error(exc)

    return templates.TemplateResponse(
        name="pages/address_permissions.html",
        context=context.build_context(
            title=f"Permissions - {address[:16]}...",
            address=address,
            permissions=permissions or [],
        ),
    )


# Legacy routes for backward compatibility
@router.get(
    "/chain/{chain_name}/addresses",
    response_class=HTMLResponse,
    name="legacy_addresses",
    include_in_schema=False,
)
async def legacy_list_addresses(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """Legacy addresses list route."""
    return await list_addresses(
        request, chain, service, pagination, templates, context, query_params
    )


@router.get(
    "/chain/{chain_name}/address/{address}",
    response_class=HTMLResponse,
    name="legacy_address",
    include_in_schema=False,
)
async def legacy_address_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(..., min_length=26, max_length=52),
):
    """Legacy address detail route."""
    return await address_detail(request, chain, service, templates, context, address)
