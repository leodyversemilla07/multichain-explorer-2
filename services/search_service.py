"""
Search service shared by HTML and JSON routers.

Provides a single implementation for multi-entity blockchain search to avoid
drift between the rendered UI and API search behavior.
"""

import asyncio
from typing import Any, Dict, List
from exceptions import is_rpc_not_found_error


def _get_chain_path(chain: Any) -> str:
    """Resolve a chain path from either attributes or legacy config dicts."""
    path_name = getattr(chain, "path_name", None)
    if isinstance(path_name, str) and path_name:
        return path_name

    config = getattr(chain, "config", {}) or {}
    config_path = config.get("path-name", "")
    return config_path if isinstance(config_path, str) else ""


def _get_result_url(chain: Any, result_type: str, result_id: str) -> str:
    """Generate a canonical URL for a search result."""
    chain_path = _get_chain_path(chain)
    url_map = {
        "block": f"/{chain_path}/block/{result_id}",
        "transaction": f"/{chain_path}/tx/{result_id}",
        "address": f"/{chain_path}/address/{result_id}",
        "asset": f"/{chain_path}/asset/{result_id}",
        "stream": f"/{chain_path}/stream/{result_id}",
    }
    return url_map.get(result_type, "/")


async def search_all_entities(
    chain: Any,
    service: Any,
    query: str,
    limit: int = 10,
    include_stream_keys: bool = True,
) -> Dict[str, Any]:
    """
    Search across the supported entity types for a given query.

    Args:
        chain: Chain object or compatible mock.
        service: Blockchain service instance.
        query: Search string.
        limit: Maximum results per entity type.
        include_stream_keys: Whether to perform stream key lookup.

    Returns:
        Dict with `results` and `total`.
    """
    results_list: List[Dict[str, Any]] = []

    if not query or len(query.strip()) < 2:
        return {"results": [], "total": 0}

    query = query.strip()

    async def search_block() -> List[Dict[str, Any]]:
        found = []
        if query.isdigit():
            height = int(query)
            block = await service.get_block_by_height(height)
            if block:
                found.append(
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
                        "url": _get_result_url(chain, "block", str(height)),
                    }
                )
        elif len(query) == 64:
            block = await service.get_block_by_hash(query)
            if block:
                block_height = str(block.get("height", ""))
                found.append(
                    {
                        "type": "block",
                        "id": block_height,
                        "label": f"Block #{block_height}",
                        "meta": {
                            "hash": query,
                            "miner": block.get("miner", ""),
                            "time": block.get("time", 0),
                            "txcount": len(block.get("tx", [])),
                        },
                        "url": _get_result_url(chain, "block", block_height),
                    }
                )
        return found

    async def search_transaction() -> List[Dict[str, Any]]:
        found = []
        if len(query) != 64:
            return found

        try:
            tx = await service.get_transaction(query)
        except Exception as exc:
            if is_rpc_not_found_error(exc):
                return found
            raise

        if tx:
            found.append(
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
                    "url": _get_result_url(chain, "transaction", query),
                }
            )
        return found

    async def search_address() -> List[Dict[str, Any]]:
        found = []
        addr_info = await service.call("validateaddress", [query])
        if addr_info and addr_info.get("isvalid", False):
            balances = await service.get_address_balances(query)
            balance = 0
            for asset in balances or []:
                if asset.get("assetref") == "0-0-0":
                    balance = asset.get("qty", 0)
                    break

            found.append(
                {
                    "type": "address",
                    "id": query,
                    "label": f"Address {query[:16]}...",
                    "meta": {
                        "address": query,
                        "ismine": addr_info.get("ismine", False),
                        "balance": balance,
                    },
                    "url": _get_result_url(chain, "address", query),
                }
            )
        return found

    async def search_assets() -> List[Dict[str, Any]]:
        found = []
        asset_response = await service.call("listassets", [query, True])
        for asset in (asset_response or [])[:limit]:
            found.append(
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
                    "url": _get_result_url(chain, "asset", asset.get("name", "")),
                }
            )
        return found

    async def search_streams() -> List[Dict[str, Any]]:
        found = []
        stream_response = await service.call("liststreams", [query, True])
        for stream in (stream_response or [])[:limit]:
            found.append(
                {
                    "type": "stream",
                    "id": stream.get("name", ""),
                    "label": stream.get("name", "Unknown Stream"),
                    "meta": {
                        "name": stream.get("name", ""),
                        "createtxid": stream.get("createtxid", ""),
                        "items": stream.get("items", 0),
                    },
                    "url": _get_result_url(chain, "stream", stream.get("name", "")),
                }
            )
        return found

    async def search_stream_keys() -> List[Dict[str, Any]]:
        found = []
        if not include_stream_keys:
            return found

        all_streams = await service.call("liststreams", ["*", True])

        async def check_stream_keys(stream: Dict[str, Any]) -> List[Dict[str, Any]]:
            stream_name = stream.get("name", "")
            if not stream_name:
                return []

            keys = await service.call(
                "liststreamkeys", [stream_name, query, False, limit, 0]
            )

            results = []
            for key_info in (keys or [])[:limit]:
                key_name = key_info.get("key", "")
                results.append(
                    {
                        "type": "stream_key",
                        "id": key_name,
                        "label": f"Key: {key_name}",
                        "meta": {
                            "stream": stream_name,
                            "items": key_info.get("items", 0),
                        },
                        "url": f"/{_get_chain_path(chain)}/stream/{stream_name}/key/{key_name}",
                    }
                )
            return results

        tasks = [check_stream_keys(stream) for stream in (all_streams or [])[:5]]
        key_results = await asyncio.gather(*tasks)
        for group in key_results:
            found.extend(group)
        return found

    results_groups = await asyncio.gather(
        search_block(),
        search_transaction(),
        search_address(),
        search_assets(),
        search_streams(),
        search_stream_keys(),
    )

    for group in results_groups:
        results_list.extend(group)

    return {"results": results_list, "total": len(results_list)}
