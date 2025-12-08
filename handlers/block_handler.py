#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Block handler for MultiChain Explorer."""

from typing import Any, Dict, Optional, Tuple

import app_state
from handlers.base import BaseHandler, safe_int
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService
from template_engine import render_template


class BlockHandler(BaseHandler):
    """Handler for block-related requests."""

    def handle_blocks_list(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List blocks."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get blockchain info for total blocks
        info = service.get_blockchain_info()
        total_blocks = info.get("blocks", 0)

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=total_blocks,
            page=safe_int(query_params.get("page"), 1),
            items_per_page=safe_int(query_params.get("count"), 20),
        )

        # Get blocks
        blocks = []
        for height in range(
            page_info["start"], min(page_info["start"] + page_info["count"], total_blocks)
        ):
            block = service.get_block_by_height(height)
            if block:
                blocks.append(block)

        html = render_template(
            "pages/blocks.html",
            {
                "title": f"Blocks - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "blocks": blocks,
                **self.unpack_pagination(page_info, f"/{chain.config['path-name']}/blocks"),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_block_detail(
        self, chain: Any, height: int, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show block details."""
        service = BlockchainService(chain)
        block = service.get_block_by_height(height)

        if not block:
            return self.not_found(f"Block #{height} not found")

        # Fetch full transaction details including size
        tx_ids = block.get("tx", [])
        tx_details = []
        for txid in tx_ids:
            tx = service.get_transaction(txid)
            if tx:
                tx_details.append(tx)

        html = render_template(
            "pages/block.html",
            {
                "title": f"Block #{height}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "block": block,
                "tx_details": tx_details,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_block_by_hash(
        self, chain: Any, block_hash: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show block by hash."""
        service = BlockchainService(chain)
        block = service.get_block_by_hash(block_hash)

        if not block:
            return self.not_found(f"Block {block_hash} not found")

        html = render_template(
            "pages/block.html",
            {
                "title": f"Block {block_hash[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "block": block,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_block_transactions(
        self, chain: Any, height: int, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List transactions in a block."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get block
        block = service.get_block_by_height(height)
        if not block:
            return self.not_found(f"Block #{height} not found")

        # Get transactions
        tx_ids = block.get("tx", [])

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(tx_ids),
            start=safe_int(query_params.get("start"), 0),
            count=safe_int(query_params.get("count"), 20),
        )

        # Get transaction details
        transactions = []
        paginated_tx_ids = tx_ids[page_info["start"] : page_info["start"] + page_info["count"]]
        for txid in paginated_tx_ids:
            tx = service.get_transaction(txid)
            if tx:
                transactions.append(tx)

        html = render_template(
            "pages/block_transactions.html",
            {
                "title": f"Transactions in Block #{height}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "block_height": height,
                "transactions": transactions,
                **self.unpack_pagination(
                    page_info, f"/{chain.config['path-name']}/block/{height}/transactions"
                ),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )
