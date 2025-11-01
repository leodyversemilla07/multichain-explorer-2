#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Permission handler for MultiChain Explorer."""

from typing import Any, Dict, Optional, Tuple

import app_state
from handlers.base import BaseHandler
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService
from template_engine import render_template


class PermissionHandler(BaseHandler):
    """Handler for permission-related requests."""

    def handle_permissions_list(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List global permissions (existing method)."""
        service = BlockchainService(chain)

        # Get all global permissions - service.rpc() returns result directly
        try:
            permissions = service.rpc("listpermissions", ["*"])
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
            if not perm.get("for") or perm.get("for", {}).get("type") == "global":
                global_count += 1

        html = render_template(
            "pages/permissions.html",
            {
                "title": f"Permissions - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "permissions": permissions,
                "global_count": global_count,
                "address_count": len(unique_addresses),
                "type_count": len(permission_types),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_global_permissions(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show global blockchain permissions."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get global permissions - service.rpc() returns result directly
        try:
            all_permissions = service.rpc("listpermissions", ["*"])
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
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(global_permissions),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_perms = global_permissions[
            page_info["start"] : page_info["start"] + page_info["count"]
        ]

        html = render_template(
            "pages/global_permissions.html",
            {
                "title": f"Global Permissions - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "permissions": paginated_perms,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/permissions/global"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )
