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

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

import app_state
from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    CommonContextDep,
    get_query_params,
)
from services.blockchain_service import BlockchainService
from services.pagination_service import PaginationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chains"])


def get_chain_summary(chain_config: Any) -> Dict[str, Any]:
    """Helper to get summary for a single chain."""
    try:
        service = BlockchainService(chain_config)
        info = service.get_blockchain_info()

        # Get additional stats - best effort
        try:
            listassets_result = service.call("listassets")
            assets_count = len(listassets_result) if listassets_result else 0
        except Exception:
            assets_count = 0

        try:
            liststreams_result = service.call("liststreams")
            streams_count = len(liststreams_result) if liststreams_result else 0
        except Exception:
            streams_count = 0

        try:
            listaddresses_result = service.call("listaddresses", ["*", False])
            addresses_count = len(listaddresses_result) if listaddresses_result else 0
        except Exception:
            addresses_count = 0

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
        logger.error(f"Error fetching chain data for {chain_config.name}: {e}")
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


@router.get("/", response_class=HTMLResponse, name="chains")
def list_chains(
    request: Request,
    templates: TemplatesDep,
):
    """
    List all configured chains (homepage).
    
    This is the main entry point of the explorer.
    """
    chains = app_state.get_state().chains or []
    chains_data = [get_chain_summary(c) for c in chains]

    base_url = app_state.get_state().settings.get("main", {}).get("base", "/")

    return templates.TemplateResponse(
        name="pages/chains.html",
        context={
            "request": request,
            "title": "Blockchain Explorer",
            "chains": chains_data,
            "base_url": base_url,
        },
    )


@router.get("/{chain_name}", response_class=HTMLResponse, name="chain_home")
def chain_home(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Chain homepage/dashboard.
    
    Shows overview of the blockchain including recent blocks,
    transaction count, and other statistics.
    """
    info = service.get_blockchain_info()

    # Get mining info and network stats
    mining_info = {}
    try:
        mining_info = service.call("getmininginfo")
    except Exception:
        pass

    # Get network hash rate
    networkhashps = None
    try:
        # Note: getnetworkhashps returns a number directly
        hashrate = service.call("getnetworkhashps")
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
    except Exception:
        # MultiChain doesn't use PoW, so network hashrate might not be applicable
        networkhashps = "N/A (Permission-based)"

    # Merge mining info into info dict
    if mining_info:
        info.update(mining_info)

    return templates.TemplateResponse(
        name="pages/chain_home.html",
        context=context.build_context(
            title=f"{chain.config['display-name']} - Dashboard",
            info=info,
            networkhashps=networkhashps,
        ),
    )


@router.get("/{chain_name}/chain", response_class=HTMLResponse, name="chain_dashboard")
def chain_dashboard(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Chain dashboard (alias for chain_home).
    """
    return chain_home(request, chain, service, templates, context, query_params)


@router.get("/{chain_name}/parameters", response_class=HTMLResponse, name="chain_parameters")
def chain_parameters(
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
        params = service.call("getblockchainparams") or {}
    except Exception as e:
        logger.error(f"Error fetching blockchain params: {e}")
        params = {}

    return templates.TemplateResponse(
        name="pages/chain_parameters.html",
        context=context.build_context(
            title=f"Parameters - {chain.config['display-name']}",
            params=params,
        ),
    )


@router.get("/{chain_name}/peers", response_class=HTMLResponse, name="peers")
def list_peers(
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
        peers = service.call("getpeerinfo") or []
    except Exception:
        peers = []

    return templates.TemplateResponse(
        name="pages/peers.html",
        context=context.build_context(
            title=f"Network Peers - {chain.config['display-name']}",
            peers=peers,
        ),
    )


@router.get("/{chain_name}/miners", response_class=HTMLResponse, name="miners")
def list_miners(
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

    return templates.TemplateResponse(
        name="pages/miners.html",
        context=context.build_context(
            title=f"Mining Statistics - {chain.config['display-name']}",
            miners=miners_list,
            block_count=block_count,
        ),
    )


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}", response_class=HTMLResponse, name="legacy_chain_home", include_in_schema=False)
def legacy_chain_home(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy chain home route."""
    return chain_home(request, chain, service, templates, context, query_params)
