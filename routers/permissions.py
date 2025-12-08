#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Permissions Router - FastAPI routes for permission-related operations.

Handles:
- Permission listing
- Global permissions
"""

from typing import Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from handlers.permission_handler import PermissionHandler
from routers.dependencies import (
    ChainDep,
    get_query_params,
)

router = APIRouter(tags=["Permissions"])


@router.get("/{chain_name}/permissions", response_class=HTMLResponse, name="permissions")
async def list_permissions(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List all permissions on the blockchain.
    
    Displays permissions for all addresses.
    """
    handler = PermissionHandler()
    status, headers, body = handler.handle_permissions_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/permissions/global", response_class=HTMLResponse, name="global_permissions")
async def global_permissions(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List global permissions.
    
    Shows only global (blockchain-level) permissions.
    """
    handler = PermissionHandler()
    status, headers, body = handler.handle_global_permissions(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/permissions", response_class=HTMLResponse, name="legacy_permissions", include_in_schema=False)
async def legacy_list_permissions(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy permissions list route."""
    handler = PermissionHandler()
    status, headers, body = handler.handle_permissions_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)
