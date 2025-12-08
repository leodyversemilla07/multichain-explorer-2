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

from typing import Dict

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import HTMLResponse

from handlers.address_handler import AddressHandler
from routers.dependencies import (
    ChainDep,
    get_query_params,
)

router = APIRouter(tags=["Addresses"])


@router.get("/{chain_name}/addresses", response_class=HTMLResponse, name="addresses")
async def list_addresses(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List addresses with balances.
    
    Displays addresses that have activity on the blockchain.
    """
    handler = AddressHandler()
    status, headers, body = handler.handle_addresses_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/address/{address}", response_class=HTMLResponse, name="address")
async def address_detail(
    request: Request,
    chain: ChainDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show address details.
    
    Displays comprehensive address information including:
    - Balance summary
    - Recent transactions
    - Asset holdings
    - Permissions
    """

    handler = AddressHandler()
    status, headers, body = handler.handle_address_detail(chain, address, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/address/{address}/transactions", response_class=HTMLResponse, name="address_transactions")
async def address_transactions(
    request: Request,
    chain: ChainDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List transactions for an address.
    
    Shows all transactions involving the specified address.
    """

    handler = AddressHandler()
    status, headers, body = handler.handle_address_transactions(chain, address, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/address/{address}/assets", response_class=HTMLResponse, name="address_assets")
async def address_assets(
    request: Request,
    chain: ChainDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List assets held by an address.
    
    Shows all assets and their quantities for the address.
    """

    handler = AddressHandler()
    status, headers, body = handler.handle_address_assets(chain, address, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/address/{address}/streams", response_class=HTMLResponse, name="address_streams")
async def address_streams(
    request: Request,
    chain: ChainDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List streams associated with an address.
    
    Shows streams where the address has published or has permissions.
    """

    handler = AddressHandler()
    status, headers, body = handler.handle_address_streams(chain, address, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/address/{address}/permissions", response_class=HTMLResponse, name="address_permissions")
async def address_permissions(
    request: Request,
    chain: ChainDep,
    address: str = Path(..., min_length=26, max_length=35, description="Blockchain address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List permissions for an address.
    
    Shows all permissions granted to the address.
    """

    handler = AddressHandler()
    status, headers, body = handler.handle_address_permissions(chain, address, query_params)
    return HTMLResponse(content=body, status_code=status)


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/addresses", response_class=HTMLResponse, name="legacy_addresses", include_in_schema=False)
async def legacy_list_addresses(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy addresses list route."""
    handler = AddressHandler()
    status, headers, body = handler.handle_addresses_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/chain/{chain_name}/address/{address}", response_class=HTMLResponse, name="legacy_address", include_in_schema=False)
async def legacy_address_detail(
    request: Request,
    chain: ChainDep,
    address: str = Path(..., min_length=26, max_length=35),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy address detail route."""

    handler = AddressHandler()
    status, headers, body = handler.handle_address_detail(chain, address, query_params)
    return HTMLResponse(content=body, status_code=status)
