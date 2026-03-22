#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Permissions Router - FastAPI routes for permission-related operations.

Handles:
- Permission listing
- Global permissions
"""

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    CommonContextDep,
    get_query_params,
    safe_int,
)

router = APIRouter(tags=["Permissions"])


@router.get("/{chain_name}/permissions", response_class=HTMLResponse, name="permissions",
            summary="List all permissions")
async def list_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
):
    """
    List all permissions on the blockchain.
    
    Displays permissions for all addresses.
    """
    # Get all global permissions
    try:
        permissions = await service.call("listpermissions", ["*"])
        if not permissions:
            permissions = []
    except Exception:
        permissions = []

    # Calculate statistics
    unique_addresses = set()
    permission_types = set()
    global_count = 0

    for perm in permissions:
        # Count unique addresses
        if perm.get("address"):
            unique_addresses.add(perm["address"])

        # Count permission types
        if perm.get("type"):
            permission_types.add(perm["type"])

        # Count global permissions (not specific to entity)
        # Assuming 'for' key presence determines if it's specific or global
        if not perm.get("for") or perm.get("for", {}).get("type") == "global":
            global_count += 1

    return templates.TemplateResponse(
        name="pages/permissions.html",
        context=context.build_context(
            title=f"Permissions - {chain.display_name}",
            permissions=permissions,
            global_count=global_count,
            address_count=len(unique_addresses),
            type_count=len(permission_types),
        ),
    )


@router.get("/{chain_name}/permissions/global", response_class=HTMLResponse, name="global_permissions",
            summary="List global permissions")
async def global_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List global permissions.
    
    Shows only global (blockchain-level) permissions.
    """
    try:
        all_permissions = await service.call("listpermissions", ["*"])
        if not all_permissions:
            all_permissions = []
    except Exception:
        all_permissions = []

    # Filter to only global permissions (not entity-specific)
    global_permissions = [
        p
        for p in all_permissions
        if not p.get("for") or p.get("for", {}).get("type") == "global"
    ]

    # Apply pagination
    page = safe_int(query_params.get("page", 1), 1)
    count = safe_int(query_params.get("count", 20), 20)

    page_info = pagination.get_pagination_info(
        total=len(global_permissions),
        page=page,
        items_per_page=count,
    )

    paginated_perms = global_permissions[
        page_info["start"] : page_info["start"] + page_info["count"]
    ]

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/permissions/global",
    )

    return templates.TemplateResponse(
        name="pages/global_permissions.html",
        context=context.build_context(
            title=f"Global Permissions - {chain.display_name}",
            permissions=paginated_perms,
            **pagination_context
        ),
    )


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/permissions", response_class=HTMLResponse, name="legacy_permissions", include_in_schema=False)
async def legacy_list_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy permissions list route."""
    return await list_permissions(request, chain, service, templates, context)
