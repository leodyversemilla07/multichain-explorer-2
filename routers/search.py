#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Search Router - FastAPI routes for search operations.

Handles:
- Search functionality across the blockchain
"""

import asyncio
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    CommonContextDep,
    get_query_params,
)

router = APIRouter(tags=["Search"])


def _get_result_url(chain: Any, result_type: str, result_id: str) -> str:
    """Generate URL for search result."""
    chain_path = chain.path_name

    # Note: Using standard routes defined in other routers
    url_map = {
        "block": f"/{chain_path}/block/{result_id}",
        "transaction": f"/{chain_path}/tx/{result_id}",
        "address": f"/{chain_path}/address/{result_id}",
        "asset": f"/{chain_path}/asset/{result_id}",
        "stream": f"/{chain_path}/stream/{result_id}",
    }

    return url_map.get(result_type, "/")


async def search_all(chain: Any, service: Any, query: str, limit: int = 10) -> Dict:
    """
    Search across all entity types.

    Args:
        chain: Chain object
        service: Blockchain service instance
        query: Search query
        limit: Maximum results per type

    Returns:
        Dictionary with results and total count
    """
    results_list = []
    
    if not query or len(query.strip()) < 2:
        return {"results": [], "total": 0}

    query = query.strip()
    
    # Define async search tasks
    
    async def search_block():
        """Search for blocks by height or hash."""
        found = []
        try:
            # Try as block height
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
            else:
                # Try as block hash
                if len(query) == 64:
                    block = await service.get_block_by_hash(query)
                    if block:
                        found.append(
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
                                "url": _get_result_url(
                                    chain, "block", str(block.get("height", ""))
                                ),
                            }
                        )
        except Exception:
            pass
        return found

    async def search_transaction():
        """Search for transaction by txid."""
        found = []
        if len(query) != 64:
            return found
            
        try:
            tx = await service.get_transaction(query)
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
        except Exception:
            pass
        return found

    async def search_address():
        """Search for address."""
        found = []
        try:
            addr_response = await service.call("validateaddress", [query])
            if addr_response:
                addr_info = addr_response
                if addr_info.get("isvalid", False):
                    # Get address balance
                    balances = await service.get_address_balances(query)
                    balance = 0
                    if balances:
                        for asset in balances:
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
        except Exception:
            pass
        return found

    async def search_assets():
        """Search for assets."""
        found = []
        try:
            asset_response = await service.call("listassets", [query, True])
            if asset_response:
                for asset in asset_response[:limit]:
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
        except Exception:
            pass
        return found

    async def search_streams():
        """Search for streams."""
        found = []
        try:
            stream_response = await service.call("liststreams", [query, True])
            if stream_response:
                for stream in stream_response[:limit]:
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
        except Exception:
            pass
        return found

    async def search_stream_keys():
        """Search for steam keys."""
        found = []
        try:
            # Expensive: list all streams then search keys. Limit parallel tasks?
            # We can parallelize the key search within streams.
            all_streams = await service.call("liststreams", ["*", True])
            if all_streams:
                
                async def check_stream_keys(stream):
                    s_found = []
                    stream_name = stream.get("name", "")
                    if not stream_name:
                        return s_found
                        
                    try:
                        keys = await service.call("liststreamkeys", [stream_name, query, False, limit, 0])
                        if keys:
                            for key_info in keys[:limit]:
                                key_name = key_info.get("key", "")
                                s_found.append(
                                    {
                                        "type": "stream_key",
                                        "id": key_name,
                                        "label": f"Key: {key_name}",
                                        "meta": {
                                            "stream": stream_name,
                                            "items": key_info.get("items", 0),
                                        },
                                        "url": f"/{chain.path_name}/stream/{stream_name}/key/{key_name}",
                                    }
                                )
                    except Exception:
                        pass
                    return s_found

                # Only check first 5 streams to avoid timeout
                tasks = [check_stream_keys(s) for s in all_streams[:5]]
                key_results = await asyncio.gather(*tasks)
                for res in key_results:
                    found.extend(res)
                    
        except Exception:
            pass
        return found

    # Execute all top-level searches in parallel
    results_groups = await asyncio.gather(
        search_block(),
        search_transaction(),
        search_address(),
        search_assets(),
        search_streams(),
        search_stream_keys(),
    )
    
    # Flatten results
    for group in results_groups:
        results_list.extend(group)

    return {"results": results_list, "total": len(results_list)}


@router.post("/{chain_name}/search", response_class=HTMLResponse, name="search")
async def search(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    search_value: str = Form(None, description="Search query"),
):
    """
    Search the blockchain.
    """
    # Prefer Form param, fallback to query param from request (legacy support)
    query = search_value
    
    # If using search_all logic
    results = await search_all(chain, service, query)
    
    # Check if single result for redirect
    if results["total"] == 1:
        # Get the URL from the single result
        redirect_url = results["results"][0]["url"]
        return RedirectResponse(url=redirect_url, status_code=302)
    
    return templates.TemplateResponse(
        name="pages/search_results.html",
        context=context.build_context(
            title=f"Search: {query} - {chain.display_name}",
            query=query,
            results=results.get("results", []),
            total=results.get("total", 0),
        ),
    )


@router.get("/{chain_name}/search", response_class=HTMLResponse, name="search_get")
async def search_get(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Search the blockchain (GET method).
    """
    query = query_params.get("q", "")

    results = await search_all(chain, service, query)
    
    # Check if single result for redirect
    if results["total"] == 1:
        # Get the URL from the single result
        redirect_url = results["results"][0]["url"]
        return RedirectResponse(url=redirect_url, status_code=302)

    return templates.TemplateResponse(
        name="pages/search_results.html",
        context=context.build_context(
            title=f"Search: {query} - {chain.display_name}",
            query=query,
            results=results.get("results", []),
            total=results.get("total", 0),
        ),
    )

@router.get("/{chain_name}/search/suggest", response_class=JSONResponse, name="search_suggest")
async def search_suggest(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Auto-suggest search results for dropdown.
    """
    query = query_params.get("term", "") # 'term' is often used by jQuery UI Autocomplete, or 'q'
    if not query:
        query = query_params.get("q", "")

    limit = 5
    
    # Reuse search_all but limit results
    # We might want a lighter version but search_all is what we have.
    search_results = await search_all(chain, service, query, limit=limit)

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
