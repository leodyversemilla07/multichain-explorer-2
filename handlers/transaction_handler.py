#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Transaction handler for MultiChain Explorer."""

from typing import Any, Dict, Optional, Tuple

import app_state
from handlers.base import BaseHandler
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService
from template_engine import render_template


class TransactionHandler(BaseHandler):
    """Handler for transaction-related requests."""

    def handle_transactions_list(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List recent transactions."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get recent transactions from mempool and recent blocks - service.rpc() returns result directly
        try:
            mempool_data = service.rpc("getrawmempool", [True])
            if mempool_data and isinstance(mempool_data, dict):
                mempool_txs = []
                for txid, data in mempool_data.items():
                    tx = {"txid": txid}
                    tx.update(data)
                    # Mempool transactions don't have blockheight or confirmations
                    # They should already have 'time' field
                    mempool_txs.append(tx)
            else:
                mempool_txs = []
        except Exception:
            mempool_txs = []

        # Get recent confirmed transactions
        info = service.get_blockchain_info()
        current_height = info.get("blocks", 0)

        recent_txs = []
        # Get transactions from last 10 blocks
        for height in range(max(0, current_height - 10), current_height + 1):
            block = service.get_block_by_height(height)
            if block and "tx" in block:
                for txid in block["tx"][:5]:  # First 5 from each block
                    tx = service.get_transaction(txid)
                    if tx:
                        # Ensure block info is present
                        if "blockheight" not in tx and "height" in block:
                            tx["blockheight"] = block["height"]
                        if "confirmations" not in tx:
                            tx["confirmations"] = current_height - block.get("height", 0) + 1
                        if "time" not in tx and "time" in block:
                            tx["time"] = block["time"]
                        recent_txs.append(tx)

        all_txs = mempool_txs + recent_txs

        # Apply pagination
        query_params = query_params or {}
        page_info = pagination.get_pagination_info(
            total=len(all_txs),
            start=int(query_params.get("start", 0)),
            count=int(query_params.get("count", 20)),
        )

        paginated_txs = all_txs[page_info["start"] : page_info["start"] + page_info["count"]]

        context = {
            "title": f"Recent Transactions - {chain.config['display-name']}",
            "chain_name": chain.config["display-name"],
            "chain_path": chain.config["path-name"],
            "transactions": paginated_txs,
            "base_url": app_state.get_state().settings["main"].get("base", "/"),
        }

        # Unpack pagination info for template
        context.update(
            self.unpack_pagination(page_info, f"/{chain.config['path-name']}/transactions")
        )

        html = render_template("pages/transactions.html", context)
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_transaction_detail(
        self, chain: Any, txid: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show transaction details."""
        service = BlockchainService(chain)
        transaction = service.get_transaction(txid)

        if not transaction:
            return self.not_found(f"Transaction {txid} not found")

        # Debug: log what fields are available
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Transaction fields: {list(transaction.keys())}")
        logger.info(
            f"Block info - blockhash: {transaction.get('blockhash')}, height: {transaction.get('height')}, blockheight: {transaction.get('blockheight')}, blockindex: {transaction.get('blockindex')}"
        )
        if transaction.get("vout"):
            logger.info(f"First vout: {transaction['vout'][0]}")

        html = render_template(
            "pages/transaction.html",
            {
                "title": f"Transaction {txid[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "txid": txid,
                "tx": transaction,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_raw_transaction(
        self, chain: Any, txid: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show raw transaction data (JSON)."""
        service = BlockchainService(chain)

        # Get raw transaction with verbose=1 for JSON - service.rpc() returns result directly
        try:
            transaction = service.rpc("getrawtransaction", [txid, 1])
            if not transaction:
                return self.not_found(f"Transaction {txid} not found")
        except Exception:
            return self.not_found(f"Transaction {txid} not found")

        html = render_template(
            "pages/raw_transaction.html",
            {
                "title": f"Raw Transaction - {txid[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "txid": txid,
                "transaction": transaction,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_raw_transaction_hex(
        self, chain: Any, txid: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show raw transaction hex."""
        service = BlockchainService(chain)

        # Get raw transaction with verbose=0 for hex - service.rpc() returns result directly
        try:
            hex_data = service.rpc("getrawtransaction", [txid, 0])
            if not hex_data:
                return self.not_found(f"Transaction {txid} not found")
        except Exception:
            return self.not_found(f"Transaction {txid} not found")

        html = render_template(
            "pages/raw_transaction_hex.html",
            {
                "title": f"Raw TX Hex - {txid[:16]}...",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "txid": txid,
                "hex": hex_data,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_tx_output_data(
        self, chain: Any, txid: str, vout: int, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show transaction output data."""
        service = BlockchainService(chain)

        # Get transaction
        transaction = service.get_transaction(txid)
        if not transaction:
            return self.not_found(f"Transaction {txid} not found")

        # Get specific output
        vouts = transaction.get("vout", [])
        if vout >= len(vouts):
            return self.not_found(f"Output {vout} not found in transaction")

        output = vouts[vout]

        html = render_template(
            "pages/tx_output_data.html",
            {
                "title": f"TX Output - {txid[:16]}... #{vout}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "txid": txid,
                "vout": vout,
                "output": output,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )
