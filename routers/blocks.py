#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Blocks Router - FastAPI routes for block-related operations.

Handles:
- Block listing
- Block details (by height or hash)
- Block transactions
"""

from typing import Dict

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from handlers.block_handler import BlockHandler
from routers.dependencies import (
    ChainDep,
    get_query_params,
)

router = APIRouter(tags=["Blocks"])


@router.get("/{chain_name}/blocks", response_class=HTMLResponse, name="blocks")
async def list_blocks(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List blocks in the blockchain.
    
    Displays paginated list of blocks with height, hash, time,
    and transaction count.
    """
    handler = BlockHandler()
    status, headers, body = handler.handle_blocks_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/block", response_class=RedirectResponse, name="block_redirect")
async def block_redirect(
    chain_name: str = Path(..., description="Chain path name"),
):
    """
    Redirect /block to /blocks (common typo handling).
    """
    return RedirectResponse(url=f"/{chain_name}/blocks", status_code=302)


@router.get("/{chain_name}/block/{height}", response_class=HTMLResponse, name="block")
async def block_by_height(
    request: Request,
    chain: ChainDep,
    height: int = Path(..., ge=0, description="Block height"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show block details by height.
    
    Displays comprehensive block information including:
    - Block header details
    - Miner information
    - Transactions in the block
    """

    handler = BlockHandler()
    status, headers, body = handler.handle_block_detail(chain, height, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/blockhash/{block_hash}", response_class=HTMLResponse, name="block_by_hash")
async def block_by_hash(
    request: Request,
    chain: ChainDep,
    block_hash: str = Path(..., min_length=64, max_length=64, description="Block hash"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show block details by hash.
    
    Alternative way to look up a block using its hash instead of height.
    """

    handler = BlockHandler()
    status, headers, body = handler.handle_block_by_hash(chain, block_hash, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/block/{height}/transactions", response_class=HTMLResponse, name="block_transactions")
async def block_transactions(
    request: Request,
    chain: ChainDep,
    height: int = Path(..., ge=0, description="Block height"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List transactions in a specific block.
    
    Shows all transactions included in the block with details.
    """

    handler = BlockHandler()
    status, headers, body = handler.handle_block_transactions(chain, height, query_params)
    return HTMLResponse(content=body, status_code=status)


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/blocks", response_class=HTMLResponse, name="legacy_blocks", include_in_schema=False)
async def legacy_list_blocks(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy blocks list route."""
    handler = BlockHandler()
    status, headers, body = handler.handle_blocks_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/chain/{chain_name}/block/{height}", response_class=HTMLResponse, name="legacy_block", include_in_schema=False)
async def legacy_block_by_height(
    request: Request,
    chain: ChainDep,
    height: int = Path(..., ge=0),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy block detail route."""

    handler = BlockHandler()
    status, headers, body = handler.handle_block_detail(chain, height, query_params)
    return HTMLResponse(content=body, status_code=status)
