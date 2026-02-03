"""
API Search Router - JSON endpoints for search operations.
"""

import asyncio
from typing import Dict, Any, List

from fastapi import APIRouter, Depends
from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    get_query_params,
)

router = APIRouter(tags=["API Search"])


async def search_all(chain: Any, service: Any, query: str, limit: int = 10) -> Dict:
    """
    Search across all entity types (Shared Logic).
    """
    results_list = []
    
    if not query or len(query.strip()) < 2:
        return {"results": [], "total": 0}

    query = query.strip()
    
    # Define async search tasks
    
    async def search_block():
        found = []
        try:
            if query.isdigit():
                height = int(query)
                block = await service.get_block_by_height(height)
                if block:
                    found.append({
                        "type": "block",
                        "id": str(height),
                        "label": f"Block #{height}",
                        "meta": block
                    })
            else:
                if len(query) == 64:
                    block = await service.get_block_by_hash(query)
                    if block:
                        found.append({
                            "type": "block",
                            "id": str(block.get("height", "")),
                            "label": f"Block #{block.get('height', '')}",
                            "meta": block
                        })
        except Exception:
            pass
        return found

    async def search_transaction():
        found = []
        if len(query) != 64:
            return found
        try:
            tx = await service.get_transaction(query)
            if tx:
                found.append({
                    "type": "transaction",
                    "id": query,
                    "label": f"Transaction {query[:16]}...",
                    "meta": tx
                })
        except Exception:
            pass
        return found

    async def search_address():
        found = []
        try:
            addr_response = await service.call("validateaddress", [query])
            if addr_response and addr_response.get("isvalid", False):
                found.append({
                    "type": "address",
                    "id": query,
                    "label": f"Address {query[:16]}...",
                    "meta": addr_response
                })
        except Exception:
            pass
        return found

    async def search_assets():
        found = []
        try:
            asset_response = await service.call("listassets", [query, True])
            if asset_response:
                for asset in asset_response[:limit]:
                    found.append({
                        "type": "asset",
                        "id": asset.get("assetref", ""),
                        "label": asset.get("name", "Unknown Asset"),
                        "meta": asset
                    })
        except Exception:
            pass
        return found

    async def search_streams():
        found = []
        try:
            stream_response = await service.call("liststreams", [query, True])
            if stream_response:
                for stream in stream_response[:limit]:
                    found.append({
                        "type": "stream",
                        "id": stream.get("name", ""),
                        "label": stream.get("name", "Unknown Stream"),
                        "meta": stream
                    })
        except Exception:
            pass
        return found
    
    # Execute all in parallel
    results_groups = await asyncio.gather(
        search_block(),
        search_transaction(),
        search_address(),
        search_assets(),
        search_streams(),
        return_exceptions=True
    )
    
    for group in results_groups:
        if isinstance(group, list):
            results_list.extend(group)

    return {"results": results_list, "total": len(results_list)}


@router.get("/{chain_name}/search", name="api_search")
async def search(
    chain: ChainDep,
    service: BlockchainServiceDep,
    query_params: dict = Depends(get_query_params),
):
    """
    Search the blockchain (JSON).
    """
    query = query_params.get("q", "")
    return await search_all(chain, service, query)
