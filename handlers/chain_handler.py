#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Chain handler for MultiChain Explorer."""

from typing import Any, Dict, Optional, Tuple

import app_state
from handlers.base import BaseHandler, safe_int
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService
from template_engine import render_template


class ChainHandler(BaseHandler):
    """Handler for chain-related requests."""

    def handle_chains(
        self, chain: Any = None, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List all chains."""
        chains_data = []
        for c in app_state.get_state().chains:
            try:
                service = BlockchainService(c)
                info = service.get_blockchain_info()

                # Get additional stats
                listassets_result = c.request("listassets")
                assets_count = (
                    len(listassets_result.get("result", []))
                    if listassets_result.get("result")
                    else 0
                )

                liststreams_result = c.request("liststreams")
                streams_count = (
                    len(liststreams_result.get("result", []))
                    if liststreams_result.get("result")
                    else 0
                )

                listaddresses_result = c.request("listaddresses", ["*", False])
                addresses_count = (
                    len(listaddresses_result.get("result", []))
                    if listaddresses_result.get("result")
                    else 0
                )

                # Estimate transactions (blocks * average txs per block)
                block_count = info.get("blocks", 0)
                transactions_count = block_count  # Simplified estimate

                chains_data.append(
                    {
                        "name": c.config.get("display-name", "Unknown"),
                        "path": c.config.get("path-name", ""),
                        "blocks": info.get("blocks", 0),
                        "transactions": transactions_count,
                        "assets": assets_count,
                        "streams": streams_count,
                        "addresses": addresses_count,
                        "connected": True,
                    }
                )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error fetching chain data: {type(e).__name__}: {e}")
                import traceback

                logger.error(traceback.format_exc())

                error_msg = str(e) if str(e) else "Connection failed"
                chains_data.append(
                    {
                        "name": c.config.get("display-name", "Unknown"),
                        "path": c.config.get("path-name", ""),
                        "blocks": 0,
                        "transactions": 0,
                        "assets": 0,
                        "streams": 0,
                        "addresses": 0,
                        "connected": False,
                        "error": error_msg,
                    }
                )

        html = render_template(
            "pages/chains.html",
            {
                "title": "Blockchain Explorer",
                "chains": chains_data,
                "base_url": app_state.get_state().settings.get("main", {}).get("base", "/")
                if app_state.get_state().settings
                else "/",
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_chain_home(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show chain dashboard/home."""
        service = BlockchainService(chain)
        info = service.get_blockchain_info()

        # Get mining info and network stats
        mining_info = {}
        try:
            mining_info = service.rpc("getmininginfo", [])
        except Exception:
            pass

        # Get network hash rate
        networkhashps = None
        try:
            networkhashps = service.rpc("getnetworkhashps", [])
            if networkhashps:
                # Format as hash/s with appropriate unit
                if networkhashps >= 1_000_000_000_000:
                    networkhashps = f"{networkhashps / 1_000_000_000_000:.2f} TH/s"
                elif networkhashps >= 1_000_000_000:
                    networkhashps = f"{networkhashps / 1_000_000_000:.2f} GH/s"
                elif networkhashps >= 1_000_000:
                    networkhashps = f"{networkhashps / 1_000_000:.2f} MH/s"
                elif networkhashps >= 1_000:
                    networkhashps = f"{networkhashps / 1_000:.2f} KH/s"
                else:
                    networkhashps = f"{networkhashps:.2f} H/s"
        except Exception:
            # MultiChain doesn't use PoW, so network hashrate might not be applicable
            networkhashps = "N/A (Permission-based)"

        # Merge mining info into info dict
        if mining_info:
            info.update(mining_info)

        html = render_template(
            "pages/chain_home.html",
            {
                "title": f"{chain.config['display-name']} - Dashboard",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "info": info,
                "networkhashps": networkhashps,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_chain_parameters(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show chain parameters."""
        service = BlockchainService(chain)

        # Get blockchain parameters - service.rpc() returns result directly
        try:
            params = service.rpc("getblockchainparams", [])
            if not params:
                params = {}
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching blockchain params: {e}")
            params = {}

        html = render_template(
            "pages/chain_parameters.html",
            {
                "title": f"Parameters - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "params": params,  # Changed from "parameters" to "params" to match template
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_miners(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show mining statistics."""
        service = BlockchainService(chain)
        pagination = PaginationService()

        # Get recent blocks to analyze miners
        info = service.get_blockchain_info()
        current_height = info.get("blocks", 0)

        # Get last 100 blocks
        miner_stats = {}
        block_count = min(100, current_height + 1)

        for height in range(max(0, current_height - block_count + 1), current_height + 1):
            block = service.get_block_by_height(height)
            if block and "miner" in block:
                miner = block["miner"]
                if miner not in miner_stats:
                    miner_stats[miner] = {"count": 0, "percentage": 0}
                miner_stats[miner]["count"] += 1

        # Calculate percentages
        for miner in miner_stats:
            miner_stats[miner]["percentage"] = miner_stats[miner]["count"] / block_count * 100

        # Convert to list and sort by count
        miners_list = [{"address": miner, **stats} for miner, stats in miner_stats.items()]
        miners_list.sort(key=lambda x: x["count"], reverse=True)

        html = render_template(
            "pages/miners.html",
            {
                "title": f"Mining Statistics - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "miners": miners_list,
                "block_count": block_count,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_peers(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show network peers."""
        service = BlockchainService(chain)

        # Get peer info - service.rpc() returns result directly
        try:
            peers = service.rpc("getpeerinfo", [])
            if not peers:
                peers = []
        except Exception:
            peers = []

        html = render_template(
            "pages/peers.html",
            {
                "title": f"Network Peers - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "peers": peers,
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )
