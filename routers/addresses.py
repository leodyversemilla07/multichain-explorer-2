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

router = APIRouter(tags=["Addresses"])


@router.get("/{chain_name}/addresses", response_class=HTMLResponse, name="addresses")
def list_addresses(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List addresses with balances.
    
    Displays addresses that have activity on the blockchain.
    """
    # Get total address count
    try:
        addresses = service.call("listaddresses", ["*", True])
        if not addresses:
            addresses = []
    except Exception:
        addresses = []

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(addresses),
        page=page,
        items_per_page=count,
    )

    paginated_addresses = addresses[
        page_info["start"] : page_info["start"] + page_info["count"]
    ]

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/addresses",
    }

    return templates.TemplateResponse(
        name="pages/addresses.html",
        context=context.build_context(
            title=f"Addresses - {chain.config['display-name']}",
            addresses=paginated_addresses,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/address/{address}", response_class=HTMLResponse, name="address")
def address_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
):
    """
    Show address details.
    """
    address_info = service.get_address_info(address)

    if not address_info:
        raise HTTPException(status_code=404, detail=f"Address {address} not found")

    # Get balances
    balances = service.get_address_balances(address)

    # Get permissions
    permissions = service.get_address_permissions(address)

    # Get recent transactions (last 10)
    try:
        transactions = service.call("listaddresstransactions", [address, 10, 0, True])
        if not transactions:
            transactions = []
    except Exception:
        transactions = []

    # Get total transaction count
    # Note: listaddresstransactions behavior may vary by chain/version.
    # Fetching all to count is expensive.
    # The handler did this:
    try:
        all_transactions = service.call("listaddresstransactions", [address, 9999999, 0, False])
        transactions_count = len(all_transactions) if all_transactions else 0
    except Exception:
        transactions_count = 0

    return templates.TemplateResponse(
        name="pages/address.html",
        context=context.build_context(
            title=f"Address - {chain.config['display-name']}",
            address=address,
            address_info=address_info,
            address_data=address_info, # Both keys used in template?
            balances=balances,
            assets=balances, # Alias
            permissions=permissions,
            transactions=transactions,
            transactions_count=transactions_count,
        ),
    )


@router.get("/{chain_name}/address/{address}/transactions", response_class=HTMLResponse, name="address_transactions")
def address_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List transactions for an address.
    """
    # Get all transactions to count them
    try:
        all_transactions = service.call("listaddresstransactions", [address, 9999999, 0, False])
        if not all_transactions:
            all_transactions = []
        total_count = len(all_transactions)
    except Exception:
        all_transactions = []
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
        # Get transactions for this page
        # listaddresstransactions args: address, count, skip, verbose
        try:
            transactions = service.call(
                "listaddresstransactions",
                [address, page_info["count"], page_info["start"], True],
            )
            if not transactions:
                transactions = []
        except Exception:
            transactions = []

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/address/{address}/transactions",
    }

    return templates.TemplateResponse(
        name="pages/address_transactions.html",
        context=context.build_context(
            title=f"Transactions - {address[:16]}...",
            address=address,
            transactions=transactions,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/address/{address}/assets", response_class=HTMLResponse, name="address_assets")
def address_assets(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
):
    """
    List assets held by an address.
    """
    # Get address balances
    balances = service.get_address_balances(address)

    return templates.TemplateResponse(
        name="pages/address_assets.html",
        context=context.build_context(
            title=f"Assets - {address[:16]}...",
            address=address,
            assets=balances or [],
        ),
    )


@router.get("/{chain_name}/address/{address}/streams", response_class=HTMLResponse, name="address_streams")
def address_streams(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List streams associated with an address.
    """
    # Get all streams to count them
    try:
        # Note: explorerlistaddressstreams is a custom RPC or extended one?
        # The handler used it. If not available, it might fail.
        # Fallback to standard liststreams? No, that lists all.
        # Check if listaddressstreams exists? usually it's liststreampublisher...
        # But let's assume the handler was correct about the method name.
        all_streams = service.call("explorerlistaddressstreams", [address, True, 9999999, 0])
        if not all_streams or not isinstance(all_streams, list):
            all_streams = []

        total_count = len(all_streams)
    except Exception:
        # If the RPC call fails, just show empty list
        all_streams = []
        total_count = 0

    page_info = None
    streams = []

    if total_count > 0:
        # Apply pagination
        page = int(query_params.get("page", 1))
        count = int(query_params.get("count", 20))

        page_info = pagination.get_pagination_info(
            total=total_count,
            page=page,
            items_per_page=count,
        )

        # Get streams for this page
        try:
            streams = service.call(
                "explorerlistaddressstreams",
                [address, True, page_info["count"], page_info["start"]],
            )
            if not streams:
                streams = []
        except Exception:
            streams = []

    pagination_context = {}
    if page_info:
        pagination_context = {
            "page": page_info["page"],
            "page_count": page_info["page_count"],
            "has_next": page_info["has_next"],
            "has_prev": page_info["has_prev"],
            "next_page": page_info["next_page"],
            "prev_page": page_info["prev_page"],
            "url_base": f"/{chain.config['path-name']}/address/{address}/streams",
        }

    return templates.TemplateResponse(
        name="pages/address_streams.html",
        context=context.build_context(
            title=f"Streams - {address[:16]}...",
            address=address,
            streams=streams,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/address/{address}/permissions", response_class=HTMLResponse, name="address_permissions")
def address_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
):
    """
    List permissions for an address.
    """
    # Get permissions
    permissions = service.get_address_permissions(address)

    return templates.TemplateResponse(
        name="pages/address_permissions.html",
        context=context.build_context(
            title=f"Permissions - {address[:16]}...",
            address=address,
            permissions=permissions or [],
        ),
    )


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/addresses", response_class=HTMLResponse, name="legacy_addresses", include_in_schema=False)
def legacy_list_addresses(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy addresses list route."""
    return list_addresses(request, chain, service, pagination, templates, context, query_params)


@router.get("/chain/{chain_name}/address/{address}", response_class=HTMLResponse, name="legacy_address", include_in_schema=False)
def legacy_address_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    address: str = Path(..., min_length=26, max_length=35),
):
    """Legacy address detail route."""
    return address_detail(request, chain, service, templates, context, address)
