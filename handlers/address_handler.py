#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Address handler for MultiChain Explorer."""

from typing import Any, Dict, Optional, Tuple

import app_state
from handlers.base import BaseHandler
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService
from template_engine import render_template


class AddressHandler(BaseHandler):
    """Handler for address-related requests."""

    def handle_addresses_list(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List all addresses."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get total address count
        addresses = service.rpc("listaddresses", ["*", True])
        if not addresses:
            addresses = []

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(addresses),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_addresses = addresses[
            page_info["start"] : page_info["start"] + page_info["count"]
        ]

        html = render_template(
            "pages/addresses.html",
            {
                "title": f"Addresses - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "addresses": paginated_addresses,
                **self.unpack_pagination(page_info, f"/{chain.config['path-name']}/addresses"),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_address_detail(
        self, chain: Any, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show address details."""
        service = BlockchainService(chain)
        address_info = service.get_address_info(address)

        if not address_info:
            html = render_template(
                "pages/error.html",
                {
                    "title": "Address Not Found",
                    "error_code": 404,
                    "error_message": f"Address {address} not found",
                    "base_url": app_state.get_state().settings["main"].get("base", "/"),
                },
            )
            return (
                404,
                [("Content-Type", "text/html; charset=utf-8")],
                html.encode("utf-8"),
            )

        # Get balances
        balances = service.get_address_balances(address)

        # Get permissions
        permissions = service.get_address_permissions(address)

        # Get recent transactions (last 10)
        transactions = service.rpc("listaddresstransactions", [address, 10, 0, True])
        if not transactions:
            transactions = []

        # Get total transaction count
        all_transactions = service.rpc("listaddresstransactions", [address, 9999999, 0, False])
        transactions_count = len(all_transactions) if all_transactions else 0

        html = render_template(
            "pages/address.html",
            {
                "title": f"Address - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "address": address,
                "address_info": address_info,
                "address_data": address_info,
                "balances": balances,
                "assets": balances,
                "permissions": permissions,
                "transactions": transactions,
                "transactions_count": transactions_count,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_address_transactions(
        self, chain: Any, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List transactions for an address."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get all transactions to count them
        # Note: listaddresstransactions doesn't provide a total count,
        # so we need to fetch all to know the total
        all_transactions = service.rpc("listaddresstransactions", [address, 9999999, 0, False])
        if not all_transactions:
            all_transactions = []

        total_count = len(all_transactions)

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=total_count,
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        transactions = []
        if total_count > 0:
            # Get transactions for this page
            transactions = service.rpc(
                "listaddresstransactions",
                [address, page_info["count"], page_info["start"], True],
            )
            if not transactions:
                transactions = []

        html = render_template(
            "pages/address_transactions.html",
            {
                "title": f"Transactions - {address[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "address": address,
                "transactions": transactions,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/address/{address}/transactions"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_address_assets(
        self, chain: Any, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List assets owned by an address."""
        service = BlockchainService(chain)

        # Get address balances
        balances = service.get_address_balances(address)

        html = render_template(
            "pages/address_assets.html",
            {
                "title": f"Assets - {address[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "address": address,
                "assets": balances or [],
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_address_streams(
        self, chain: Any, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List streams an address has published to."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get all streams to count them
        try:
            all_streams = service.rpc("explorerlistaddressstreams", [address, True, 9999999, 0])
            if not all_streams or not isinstance(all_streams, list):
                all_streams = []

            total_count = len(all_streams)
        except Exception:
            # If the RPC call fails, just show empty list
            all_streams = []
            total_count = 0

        if total_count == 0:
            streams = []
            page_info = None
        else:
            # Apply pagination
            query_params = query_params or {}
            page_info = pagination.get_pagination_info(
                total=total_count,
                start=int(query_params.get("start", 0)),
                count=int(query_params.get("count", 20)),
            )

            # Get streams for this page
            streams = service.rpc(
                "explorerlistaddressstreams",
                [address, True, page_info["count"], page_info["start"]],
            )
            if not streams:
                streams = []

        html = render_template(
            "pages/address_streams.html",
            {
                "title": f"Streams - {address[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "address": address,
                "streams": streams,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/address/{address}/streams"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_address_permissions(
        self, chain: Any, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show permissions for an address."""
        service = BlockchainService(chain)

        # Get permissions
        permissions = service.get_address_permissions(address)

        html = render_template(
            "pages/address_permissions.html",
            {
                "title": f"Permissions - {address[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "address": address,
                "permissions": permissions or [],
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )
