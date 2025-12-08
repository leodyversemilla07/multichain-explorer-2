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

from typing import Dict

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import HTMLResponse

from handlers.asset_handler import AssetHandler
from routers.dependencies import (
    ChainDep,
    get_query_params,
)

router = APIRouter(tags=["Assets"])


@router.get("/{chain_name}/assets", response_class=HTMLResponse, name="assets")
async def list_assets(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List all assets on the blockchain.
    
    Displays all issued assets with their details.
    """
    handler = AssetHandler()
    status, headers, body = handler.handle_assets_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/asset/{asset_name}", response_class=HTMLResponse, name="asset")
async def asset_detail(
    request: Request,
    chain: ChainDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show asset details.
    
    Displays comprehensive asset information including:
    - Issuance details
    - Total supply
    - Holder count
    - Recent transactions
    """

    handler = AssetHandler()
    status, headers, body = handler.handle_asset_detail(chain, asset_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/asset/{asset_name}/holders", response_class=HTMLResponse, name="asset_holders")
async def asset_holders(
    request: Request,
    chain: ChainDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List asset holders.
    
    Shows all addresses holding this asset with their balances.
    """

    handler = AssetHandler()
    status, headers, body = handler.handle_asset_holders(chain, asset_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/asset/{asset_name}/transactions", response_class=HTMLResponse, name="asset_transactions")
async def asset_transactions(
    request: Request,
    chain: ChainDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List asset transactions.
    
    Shows all transactions involving this asset.
    """

    handler = AssetHandler()
    status, headers, body = handler.handle_asset_transactions(chain, asset_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/asset/{asset_name}/issues", response_class=HTMLResponse, name="asset_issues")
async def asset_issues(
    request: Request,
    chain: ChainDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show asset issuance history.
    
    Displays all issuance events for this asset.
    """

    handler = AssetHandler()
    status, headers, body = handler.handle_asset_issues(chain, asset_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/asset/{asset_name}/permissions", response_class=HTMLResponse, name="asset_permissions")
async def asset_permissions(
    request: Request,
    chain: ChainDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show asset permissions.
    
    Displays permission settings for this asset.
    """

    handler = AssetHandler()
    status, headers, body = handler.handle_asset_permissions(chain, asset_name, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/asset/{asset_name}/holder/{address}/transactions", response_class=HTMLResponse, name="holder_transactions")
async def holder_transactions(
    request: Request,
    chain: ChainDep,
    asset_name: str = Path(..., min_length=1, max_length=32, description="Asset name or reference"),
    address: str = Path(..., min_length=26, max_length=35, description="Holder address"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List transactions for a specific asset holder.
    
    Shows all transactions of this asset for a specific address.
    """

    handler = AssetHandler()
    status, headers, body = handler.handle_holder_transactions(chain, asset_name, address, query_params)
    return HTMLResponse(content=body, status_code=status)


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/assets", response_class=HTMLResponse, name="legacy_assets", include_in_schema=False)
async def legacy_list_assets(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy assets list route."""
    handler = AssetHandler()
    status, headers, body = handler.handle_assets_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/chain/{chain_name}/asset/{asset_name}", response_class=HTMLResponse, name="legacy_asset", include_in_schema=False)
async def legacy_asset_detail(
    request: Request,
    chain: ChainDep,
    asset_name: str = Path(..., min_length=1, max_length=32),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy asset detail route."""

    handler = AssetHandler()
    status, headers, body = handler.handle_asset_detail(chain, asset_name, query_params)
    return HTMLResponse(content=body, status_code=status)
