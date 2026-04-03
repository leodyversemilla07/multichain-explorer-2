#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chains Router - FastAPI routes for chain-related operations.

Handles:
- Chain listing (homepage)
- Chain home/dashboard
- Chain parameters
- Peers
- Miners
"""

import asyncio
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from routers.dependencies import (
    ChainDep,
    StateDep,
    TemplatesDep,
    BlockchainServiceDep,
    CommonContextDep,
    get_query_params_dep,
    raise_backend_http_error,
)
from services.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chains"])


async def get_chain_summary(chain_config: Any, client: Any = None) -> Dict[str, Any]:
    """Helper to get summary for a single chain."""
    service = BlockchainService(chain_config, client=client)
    try:
        info = await service.get_blockchain_info()

        # Get additional stats - best effort
        # We can run these concurrently
        results = await asyncio.gather(
            service.get_all_assets(),
            service.get_all_streams(),
            service.get_all_addresses(),
            return_exceptions=True,
        )

        assets_count = 0
        streams_count = 0
        addresses_count = 0

        for label, result in zip(
            ("assets", "streams", "addresses"),
            results,
            strict=False,
        ):
            if isinstance(result, Exception):
                logger.warning(
                    "Error fetching %s summary for %s: %s",
                    label,
                    chain_config.name,
                    result,
                )
                continue

            if label == "assets":
                assets_count = len(result) if result else 0
            elif label == "streams":
                streams_count = len(result) if result else 0
            else:
                addresses_count = len(result) if result else 0

        block_count = info.get("blocks", 0)
        transactions_count = block_count  # Simplified estimate

        return {
            "name": chain_config.config.get("display-name", "Unknown"),
            "path": chain_config.config.get("path-name", ""),
            "blocks": block_count,
            "transactions": transactions_count,
            "assets": assets_count,
            "streams": streams_count,
            "addresses": addresses_count,
            "connected": True,
        }
    except Exception as e:
        logger.error("Error fetching chain data for %s: %s", chain_config.name, e)
        return {
            "name": chain_config.config.get("display-name", "Unknown"),
            "path": chain_config.config.get("path-name", ""),
            "blocks": 0,
            "transactions": 0,
            "assets": 0,
            "streams": 0,
            "addresses": 0,
            "connected": False,
            "error": str(e) if str(e) else "Connection failed",
        }
    finally:
        await service.close()


@router.get("/", response_class=HTMLResponse, name="chains", summary="List all chains")
async def list_chains(
    request: Request,
    state: StateDep,
    templates: TemplatesDep,
):
    """
    List all configured chains (homepage).

    This is the main entry point of the explorer.
    """
    chains = state.chains or []
    http_client = getattr(request.app.state, "http_client", None)

    # Run all chain summaries concurrently
    chains_data = await asyncio.gather(
        *[get_chain_summary(c, client=http_client) for c in chains]
    )

    base_url = state.get_setting("main", "base", "/")

    return templates.TemplateResponse(
        name="pages/chains.html",
        context={
            "request": request,
            "title": "Blockchain Explorer",
            "chains": chains_data,
            "base_url": base_url,
        },
    )


@router.get(
    "/{chain_name}",
    response_class=HTMLResponse,
    name="chain_home",
    summary="Chain dashboard",
)
async def chain_home(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    Chain homepage/dashboard.

    Shows overview of the blockchain including recent blocks,
    transaction count, and other statistics.
    """
    info = await service.get_blockchain_info()
    recent_blocks = []
    latest_height = max(info.get("blocks", 0) - 1, 0)

    if info.get("blocks", 0) > 0:
        recent_count = min(10, info.get("blocks", 0))
        start_height = max(0, latest_height - recent_count + 1)
        try:
            recent_blocks = await service.get_recent_blocks(start_height, recent_count)
            recent_blocks.sort(key=lambda block: block.get("height", 0), reverse=True)
        except Exception as exc:
            logger.warning("Error fetching recent blocks for %s: %s", chain.name, exc)
            recent_blocks = []

    # Get mining info and network stats
    mining_info = {}
    try:
        mining_info = await service.get_mining_info()
    except Exception as exc:
        logger.warning("Error fetching mining info for %s: %s", chain.name, exc)

    # Get network hash rate
    networkhashps = None
    try:
        # Note: getnetworkhashps returns a number directly
        hashrate = await service.get_network_hashrate()
        if hashrate:
            # Format as hash/s with appropriate unit
            if hashrate >= 1_000_000_000_000:
                networkhashps = f"{hashrate / 1_000_000_000_000:.2f} TH/s"
            elif hashrate >= 1_000_000_000:
                networkhashps = f"{hashrate / 1_000_000_000:.2f} GH/s"
            elif hashrate >= 1_000_000:
                networkhashps = f"{hashrate / 1_000_000:.2f} MH/s"
            elif hashrate >= 1_000:
                networkhashps = f"{hashrate / 1_000:.2f} KH/s"
            else:
                networkhashps = f"{hashrate:.2f} H/s"
    except Exception as exc:
        logger.warning("Error fetching network hash rate for %s: %s", chain.name, exc)
        # MultiChain doesn't use PoW, so network hashrate might not be applicable
        networkhashps = "N/A (Permission-based)"

    # Merge mining info into info dict
    if mining_info:
        info.update(mining_info)

    return templates.TemplateResponse(
        name="pages/chain_home.html",
        context=context.build_context(
            title=f"{chain.display_name} - Dashboard",
            info=info,
            chain_description=info.get("description"),
            networkhashps=networkhashps,
            recent_blocks=recent_blocks,
        ),
    )


@router.get(
    "/{chain_name}/chain",
    response_class=HTMLResponse,
    name="chain_dashboard",
    summary="Chain dashboard (alias)",
)
async def chain_dashboard(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    Chain dashboard (alias for chain_home).
    """
    return await chain_home(request, chain, service, templates, context, query_params)


@router.get(
    "/{chain_name}/parameters",
    response_class=HTMLResponse,
    name="chain_parameters",
    summary="Chain parameters",
)
async def chain_parameters(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
):
    """
    Display chain parameters.

    Shows blockchain configuration parameters like block size,
    mining settings, permissions, etc.
    """
    try:
        params = await service.call("getblockchainparams") or {}
    except Exception as exc:
        raise_backend_http_error(exc)

    return templates.TemplateResponse(
        name="pages/chain_parameters.html",
        context=context.build_context(
            title=f"Parameters - {chain.display_name}",
            params=params,
        ),
    )


@router.get(
    "/{chain_name}/peers",
    response_class=HTMLResponse,
    name="peers",
    summary="Network peers",
)
async def list_peers(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
):
    """
    List network peers.

    Shows connected nodes in the blockchain network.
    """
    try:
        peers = await service.call("getpeerinfo") or []
    except Exception as exc:
        raise_backend_http_error(exc)

    return templates.TemplateResponse(
        name="pages/peers.html",
        context=context.build_context(
            title=f"Network Peers - {chain.display_name}",
            peers=peers,
        ),
    )


@router.get(
    "/{chain_name}/miners",
    response_class=HTMLResponse,
    name="miners",
    summary="Mining statistics",
)
async def list_miners(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
):
    """
    Show mining statistics.

    Displays information about miners/validators in the network.
    """
    # Get recent blocks to analyze miners
    info = await service.get_blockchain_info()
    current_height = info.get("blocks", 0)

    # Get last 100 blocks
    miner_stats = {}
    block_count = min(100, current_height + 1)

    # Semaphore caps concurrent RPC calls at 10 — avoids overwhelming the node
    # with 100 simultaneous requests (skill ref: fastapi-agents > performance > async patterns)
    sem = asyncio.Semaphore(10)

    async def fetch_block_safe(height: int):
        async with sem:
            return await service.get_block_by_height(height)

    tasks = [
        fetch_block_safe(h)
        for h in range(max(0, current_height - block_count + 1), current_height + 1)
    ]

    blocks = await asyncio.gather(*tasks, return_exceptions=True)

    for block in blocks:
        if isinstance(block, Exception) or not block or "miner" not in block:
            continue
        miner = block["miner"]
        if miner not in miner_stats:
            miner_stats[miner] = {"blocks": 0, "percentage": 0}
        miner_stats[miner]["blocks"] += 1

    # Calculate percentages
    for miner in miner_stats:
        miner_stats[miner]["percentage"] = (
            miner_stats[miner]["blocks"] / block_count * 100
        )

    # Convert to list and sort by blocks
    miners_list = [{"address": miner, **stats} for miner, stats in miner_stats.items()]
    miners_list.sort(key=lambda x: x["blocks"], reverse=True)

    return templates.TemplateResponse(
        name="pages/miners.html",
        context=context.build_context(
            title=f"Mining Statistics - {chain.display_name}",
            miners=miners_list,
            total_blocks=block_count,
        ),
    )


# Legacy routes for backward compatibility
@router.get(
    "/chain/{chain_name}",
    response_class=HTMLResponse,
    name="legacy_chain_home",
    include_in_schema=False,
)
async def legacy_chain_home(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """Legacy chain home route."""
    return await chain_home(request, chain, service, templates, context, query_params)
