#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Search handler for MultiChain Explorer."""

from typing import Any, Dict, Optional, Tuple

import app_state
from handlers.base import BaseHandler, safe_int
from services.blockchain_service import BlockchainService
from template_engine import render_template


class SearchHandler(BaseHandler):
    """Handler for search-related requests."""

    def handle_search(
        self, chain: Any, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Handle search requests."""
        query = query_params.get("q", "") if query_params else ""

        if not query or len(query.strip()) < 2:
            html = render_template(
                "pages/search_results.html",
                {
                    "title": f"Search - {chain.config['display-name']}",
                    "chain_name": chain.config["display-name"],
                    "chain_path": chain.config["path-name"],
                    "query": query,
                    "results": [],
                    "base_url": app_state.get_state().settings["main"].get("base", "/"),
                },
            )
            return (
                200,
                [("Content-Type", "text/html; charset=utf-8")],
                html.encode("utf-8"),
            )

        # Perform search
        results = self.search_all(chain, query)

        html = render_template(
            "pages/search_results.html",
            {
                "title": f"Search: {query} - {chain.config['display-name']}",
                "chain_name": chain.config["display-name"],
                "chain_path": chain.config["path-name"],
                "query": query,
                "results": results.get("results", []),
                "total": results.get("total", 0),
                "base_url": app_state.get_state().settings["main"].get("base", "/"),
            },
        )
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def search_all(self, chain: Any, query: str, limit: int = 10) -> Dict:
        """
        Search across all entity types.

        Args:
            chain: Chain object
            query: Search query
            limit: Maximum results per type

        Returns:
            Dictionary with results and total count
        """
        service = BlockchainService(chain)
        results = {"results": [], "total": 0}

        if not query or len(query.strip()) < 2:
            return results

        query = query.strip()

        # Search blocks (by height or hash)
        try:
            # Try as block height
            if query.isdigit():
                height = int(query)
                block = service.get_block_by_height(height)
                if block:
                    results["results"].append(
                        {
                            "type": "block",
                            "id": str(height),
                            "label": f"Block #{height}",
                            "meta": {
                                "hash": block.get("hash", ""),
                                "miner": block.get("miner", ""),
                                "time": block.get("time", 0),
                                "txcount": len(block.get("tx", [])),
                            },
                            "url": self._get_result_url(chain, "block", str(height)),
                        }
                    )
                    results["total"] += 1
            else:
                # Try as block hash
                block = service.get_block_by_hash(query)
                if block:
                    results["results"].append(
                        {
                            "type": "block",
                            "id": str(block.get("height", "")),
                            "label": f"Block #{block.get('height', '')}",
                            "meta": {
                                "hash": query,
                                "miner": block.get("miner", ""),
                                "time": block.get("time", 0),
                                "txcount": len(block.get("tx", [])),
                            },
                            "url": self._get_result_url(
                                chain, "block", str(block.get("height", ""))
                            ),
                        }
                    )
                    results["total"] += 1
        except Exception:
            pass

        # Search transactions (by txid)
        try:
            tx = service.get_transaction(query)
            if tx:
                results["results"].append(
                    {
                        "type": "transaction",
                        "id": query,
                        "label": f"Transaction {query[:16]}...",
                        "meta": {
                            "txid": query,
                            "confirmations": tx.get("confirmations", 0),
                            "time": tx.get("time", 0),
                            "vincount": len(tx.get("vin", [])),
                            "voutcount": len(tx.get("vout", [])),
                        },
                        "url": self._get_result_url(chain, "transaction", query),
                    }
                )
                results["total"] += 1
        except Exception:
            pass

        # Search addresses
        try:
            addr_response = service.rpc("validateaddress", [query])
            if addr_response and "result" in addr_response:
                addr_info = addr_response["result"]
                if addr_info.get("isvalid", False):
                    # Get address balance
                    balances = service.get_address_balances(query)
                    balance = 0
                    if balances:
                        for asset in balances:
                            if asset.get("assetref") == "0-0-0":
                                balance = asset.get("qty", 0)
                                break

                    results["results"].append(
                        {
                            "type": "address",
                            "id": query,
                            "label": f"Address {query[:16]}...",
                            "meta": {
                                "address": query,
                                "ismine": addr_info.get("ismine", False),
                                "balance": balance,
                            },
                            "url": self._get_result_url(chain, "address", query),
                        }
                    )
                    results["total"] += 1
        except Exception:
            pass

        # Search assets (by name or reference)
        try:
            asset_response = service.rpc("listassets", [query, True])
            if asset_response and "result" in asset_response:
                for asset in asset_response["result"][:limit]:
                    results["results"].append(
                        {
                            "type": "asset",
                            "id": asset.get("assetref", ""),
                            "label": asset.get("name", "Unknown Asset"),
                            "meta": {
                                "name": asset.get("name", ""),
                                "assetref": asset.get("assetref", ""),
                                "issuer": asset.get("issueaddress", ""),
                                "units": asset.get("units", 1),
                            },
                            "url": self._get_result_url(chain, "asset", asset.get("name", "")),
                        }
                    )
                    results["total"] += 1
        except Exception:
            pass

        # Search streams (by name)
        try:
            stream_response = service.rpc("liststreams", [query, True])
            if stream_response and "result" in stream_response:
                for stream in stream_response["result"][:limit]:
                    results["results"].append(
                        {
                            "type": "stream",
                            "id": stream.get("name", ""),
                            "label": stream.get("name", "Unknown Stream"),
                            "meta": {
                                "name": stream.get("name", ""),
                                "createtxid": stream.get("createtxid", ""),
                                "items": stream.get("items", 0),
                            },
                            "url": self._get_result_url(chain, "stream", stream.get("name", "")),
                        }
                    )
                    results["total"] += 1
        except Exception:
            pass

        return results

    def search_suggest(self, chain: Any, query: str, limit: int = 5) -> Dict:
        """
        Auto-suggest search results for dropdown.

        Args:
            chain: Chain object
            query: Partial search query
            limit: Maximum suggestions

        Returns:
            Dictionary with suggestions
        """
        if not query or len(query.strip()) < 2:
            return {"suggestions": []}

        # Reuse search_all but limit results
        search_results = self.search_all(chain, query, limit=limit)

        suggestions = []
        for result in search_results["results"][:limit]:
            suggestions.append(
                {
                    "type": result["type"],
                    "id": result["id"],
                    "label": result["label"],
                    "url": result.get("url", "/"),
                }
            )

        return {"suggestions": suggestions}

    def _get_result_url(self, chain: Any, result_type: str, result_id: str) -> str:
        """Generate URL for search result."""
        chain_path = chain.config.get("path-name", "")

        url_map = {
            "block": f"/{chain_path}/block-height-{result_id}",
            "transaction": f"/{chain_path}/tx/{result_id}",
            "address": f"/{chain_path}/address/{result_id}",
            "asset": f"/{chain_path}/asset/{result_id}",
            "stream": f"/{chain_path}/stream/{result_id}",
        }

        return url_map.get(result_type, "/")
