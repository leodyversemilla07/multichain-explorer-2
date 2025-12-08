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

from typing import Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from handlers.chain_handler import ChainHandler
from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    get_query_params,
)

router = APIRouter(tags=["Chains"])


@router.get("/", response_class=HTMLResponse, name="chains")
async def list_chains(
    request: Request,
    templates: TemplatesDep,
):
    """
    List all configured chains (homepage).
    
    This is the main entry point of the explorer.
    """
    handler = ChainHandler()
    status, headers, body = handler.handle_chains(chain=None, query_params={})
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}", response_class=HTMLResponse, name="chain_home")
async def chain_home(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Chain homepage/dashboard.
    
    Shows overview of the blockchain including recent blocks,
    transaction count, and other statistics.
    """
    handler = ChainHandler()
    status, headers, body = handler.handle_chain_home(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/chain", response_class=HTMLResponse, name="chain_dashboard")
async def chain_dashboard(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Chain dashboard (alias for chain_home).
    """
    handler = ChainHandler()
    status, headers, body = handler.handle_chain_home(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/parameters", response_class=HTMLResponse, name="chain_parameters")
async def chain_parameters(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Display chain parameters.
    
    Shows blockchain configuration parameters like block size,
    mining settings, permissions, etc.
    """
    handler = ChainHandler()
    status, headers, body = handler.handle_chain_parameters(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/peers", response_class=HTMLResponse, name="peers")
async def list_peers(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List network peers.
    
    Shows connected nodes in the blockchain network.
    """
    handler = ChainHandler()
    status, headers, body = handler.handle_peers(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/miners", response_class=HTMLResponse, name="miners")
async def list_miners(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show mining statistics.
    
    Displays information about miners/validators in the network.
    """
    handler = ChainHandler()
    status, headers, body = handler.handle_miners(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}", response_class=HTMLResponse, name="legacy_chain_home", include_in_schema=False)
async def legacy_chain_home(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy chain home route."""
    handler = ChainHandler()
    status, headers, body = handler.handle_chain_home(chain, query_params)
    return HTMLResponse(content=body, status_code=status)
