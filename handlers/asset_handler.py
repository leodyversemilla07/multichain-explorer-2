#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Asset handler for MultiChain Explorer."""

from typing import Any, Dict, Optional, Tuple

import app_state
from handlers.base import BaseHandler
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService
from template_engine import render_template


class AssetHandler(BaseHandler):
    """Handler for asset-related requests."""

    def handle_assets_list(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List all assets."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get assets - service.rpc() returns result directly
        try:
            assets = service.rpc("listassets", ["*", True])
            if not assets:
                assets = []
        except Exception as e:
            return self.error(f"Failed to get assets: {e}")

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(assets),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_assets = assets[page_info["start"] : page_info["start"] + page_info["count"]]

        html = render_template(
            "pages/assets.html",
            {
                "title": f"Assets - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "assets": paginated_assets,
                **self.unpack_pagination(page_info, f"/{chain.config['path-name']}/assets"),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_asset_detail(
        self, chain: Any, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show asset details."""
        service = BlockchainService(chain)

        # Get asset info - service.rpc() returns result directly
        try:
            assets = service.rpc("listassets", [asset_name, True])
            if not assets or len(assets) == 0:
                return self.not_found(f"Asset {asset_name} not found")
            asset = assets[0]
        except Exception:
            return self.not_found(f"Asset {asset_name} not found")

        html = render_template(
            "pages/asset.html",
            {
                "title": f"Asset {asset_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "asset": asset,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_asset_transactions(
        self, chain: Any, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List transactions for an asset."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get transaction count - service.rpc() returns result directly
        try:
            count_txs = service.rpc("listassettransactions", [asset_name, False, 1, 0])
            total_count = len(count_txs) if count_txs else 0
        except Exception:
            total_count = 0

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=total_count,
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        transactions = []
        if total_count > 0:
            try:
                transactions = service.rpc(
                    "listassettransactions",
                    [asset_name, True, page_info["count"], page_info["start"]],
                )
            except Exception:
                transactions = []

        html = render_template(
            "pages/asset_transactions.html",
            {
                "title": f"Transactions - {asset_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "asset_name": asset_name,
                "transactions": transactions,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/asset/{asset_name}/transactions"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_asset_holders(
        self, chain: Any, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List holders of an asset."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get holders - service.rpc() returns result directly
        try:
            holders = service.rpc("listassetholders", [asset_name])
            if not holders:
                holders = []
        except Exception:
            holders = []

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(holders),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_holders = holders[page_info["start"] : page_info["start"] + page_info["count"]]

        html = render_template(
            "pages/asset_holders.html",
            {
                "title": f"Holders - {asset_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "asset_name": asset_name,
                "holders": paginated_holders,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/asset/{asset_name}/holders"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_holder_transactions(
        self, chain: Any, asset_name: str, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List transactions for a specific asset holder."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get transactions - service.rpc() returns result directly
        try:
            all_txs = service.rpc("listaddresstransactions", [address, 1000, 0, True])
            if not all_txs:
                all_txs = []
            # Filter transactions for this specific asset
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
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(transactions),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_txs = transactions[page_info["start"] : page_info["start"] + page_info["count"]]

        html = render_template(
            "pages/asset_holder_transactions.html",
            {
                "title": f"Transactions - {asset_name} - {address[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "asset_name": asset_name,
                "address": address,
                "transactions": paginated_txs,
                **self.unpack_pagination(
                    page_info,
                    f"/{chain.config['path-name']}/asset/{asset_name}/holder/{address}/transactions",
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_asset_issues(
        self, chain: Any, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List issuance transactions for an asset."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get asset info to find issuances - service.rpc() returns result directly
        try:
            assets = service.rpc("listassets", [asset_name, True])
            if assets and len(assets) > 0:
                asset = assets[0]
                issues = asset.get("issues", [])
            else:
                issues = []
        except Exception:
            issues = []

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(issues),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_issues = issues[page_info["start"] : page_info["start"] + page_info["count"]]

        html = render_template(
            "pages/asset_issues.html",
            {
                "title": f"Issuances - {asset_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "asset_name": asset_name,
                "issues": paginated_issues,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/asset/{asset_name}/issues"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_asset_permissions(
        self, chain: Any, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show permissions for an asset."""
        service = BlockchainService(chain)

        # Get asset info and permissions - service.rpc() returns result directly
        try:
            assets = service.rpc("listassets", [asset_name, True])
            if not assets or len(assets) == 0:
                permissions = []
            else:
                # Get addresses with permissions for this asset
                permissions = service.rpc("listpermissions", [asset_name])
                if not permissions:
                    permissions = []
        except Exception:
            permissions = []

        html = render_template(
            "pages/asset_permissions.html",
            {
                "title": f"Permissions - {asset_name}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "asset_name": asset_name,
                "permissions": permissions,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )
