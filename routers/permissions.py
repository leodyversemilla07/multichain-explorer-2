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

router = APIRouter(tags=["Permissions"])


@router.get(
    "/{chain_name}/permissions",
    response_class=HTMLResponse,
    name="permissions",
    summary="List all permissions",
)
async def list_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
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
    except Exception as exc:
        raise_backend_http_error(exc)

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

    page, count = get_page_count(query_params)
    paginated_permissions, page_info = pagination.paginate(
        permissions,
        page=page,
        items_per_page=count,
    )
    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/permissions",
        include_component_fields=True,
        total_items=len(permissions),
    )

    return templates.TemplateResponse(
        name="pages/permissions.html",
        context=context.build_context(
            title=f"Permissions - {chain.display_name}",
            permissions=paginated_permissions,
            global_count=global_count,
            address_count=len(unique_addresses),
            type_count=len(permission_types),
            pagination=page_info,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/permissions/global",
    response_class=HTMLResponse,
    name="global_permissions",
    summary="List global permissions",
)
async def global_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List global permissions.

    Shows only global (blockchain-level) permissions.
    """
    try:
        all_permissions = await service.call("listpermissions", ["*"])
        if not all_permissions:
            all_permissions = []
    except Exception as exc:
        raise_backend_http_error(exc)

    # Filter to only global permissions (not entity-specific)
    global_permissions = [
        p
        for p in all_permissions
        if not p.get("for") or p.get("for", {}).get("type") == "global"
    ]

    # Apply pagination
    page, count = get_page_count(query_params)

    paginated_perms, page_info = pagination.paginate(
        global_permissions,
        page=page,
        items_per_page=count,
    )

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/permissions/global",
        include_component_fields=True,
        total_items=len(global_permissions),
    )

    return templates.TemplateResponse(
        name="pages/global_permissions.html",
        context=context.build_context(
            title=f"Global Permissions - {chain.display_name}",
            permissions=paginated_perms,
            pagination=page_info,
            total_permissions=len(global_permissions),
            **pagination_context,
        ),
    )


# Legacy routes for backward compatibility
@router.get(
    "/chain/{chain_name}/permissions",
    response_class=HTMLResponse,
    name="legacy_permissions",
    include_in_schema=False,
)
async def legacy_list_permissions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """Legacy permissions list route."""
    return await list_permissions(
        request,
        chain,
        service,
        pagination,
        templates,
        context,
        query_params,
    )
