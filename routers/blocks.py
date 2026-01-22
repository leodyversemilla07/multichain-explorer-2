#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Blocks Router - FastAPI routes for block-related operations.

Handles:
- Block listing
- Block details (by height or hash)
- Block transactions
"""

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Path, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    CommonContextDep,
    get_query_params,
)

router = APIRouter(tags=["Blocks"])


@router.get("/{chain_name}/blocks", response_class=HTMLResponse, name="blocks")
def list_blocks(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List blocks in the blockchain.
    
    Displays paginated list of blocks with height, hash, time,
    and transaction count.
    """
    # Get blockchain info for total blocks
    info = service.get_blockchain_info()
    total_blocks = info.get("blocks", 0)

    # Apply pagination
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=total_blocks,
        page=page,
        items_per_page=count,
    )

    # Calculate block range for newest-first display
    # Page 1 shows the newest blocks, page 2 shows older ones, etc.
    end_height = total_blocks - 1 - page_info["start"]
    start_height = max(0, end_height - page_info["count"] + 1)
    blocks_to_fetch = end_height - start_height + 1
    
    # Use list_blocks API for batch fetching (much faster than individual calls)
    if blocks_to_fetch > 0 and start_height <= end_height:
        blocks = service.list_blocks(start_height, blocks_to_fetch)
        # Sort blocks by height descending (newest first)
        blocks.sort(key=lambda x: x.get("height", 0), reverse=True)
    else:
        blocks = []

    # Prepare pagination context
    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/blocks",
    }

    return templates.TemplateResponse(
        name="pages/blocks.html",
        context=context.build_context(
            title=f"Blocks - {chain.config['display-name']}",
            blocks=blocks,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/block", response_class=RedirectResponse, name="block_redirect")
def block_redirect(
    chain_name: str = Path(..., description="Chain path name"),
):
    """
    Redirect /block to /blocks (common typo handling).
    """
    return RedirectResponse(url=f"/{chain_name}/blocks", status_code=302)


@router.get("/{chain_name}/block/{identifier}", response_class=HTMLResponse, name="block")
def block_by_identifier(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    identifier: str = Path(..., description="Block height or hash"),
):
    """
    Show block details by height or hash.
    """
    # Determine if identifier is a height (numeric) or hash (64 hex chars)
    if identifier.isdigit():
        height = int(identifier)
        block = service.get_block_by_height(height)
    elif len(identifier) == 64:
        block = service.get_block_by_hash(identifier)
        height = block.get("height") if block else None
    else:
        raise HTTPException(status_code=400, detail="Invalid block identifier. Must be a height or 64-character hash.")

    if not block:
        raise HTTPException(status_code=404, detail=f"Block {identifier} not found")

    height = block.get("height", 0)
    
    # Fetch full transaction details including size
    tx_ids = block.get("tx", [])
    tx_details = []
    # Limit tx details fetching to avoid timeout on large blocks?
    # Existing handler fetched all.
    for txid in tx_ids:
        tx = service.get_transaction(txid)
        if tx:
            tx_details.append(tx)

    return templates.TemplateResponse(
        name="pages/block.html",
        context=context.build_context(
            title=f"Block #{height}",
            block=block,
            tx_details=tx_details,
        ),
    )


@router.get("/{chain_name}/blockhash/{block_hash}", response_class=HTMLResponse, name="block_by_hash")
def block_by_hash(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    block_hash: str = Path(..., min_length=64, max_length=64, description="Block hash"),
):
    """
    Show block details by hash.
    """
    block = service.get_block_by_hash(block_hash)

    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_hash} not found")

    return templates.TemplateResponse(
        name="pages/block.html",
        context=context.build_context(
            title=f"Block {block_hash[:16]}...",
            block=block,
        ),
    )


@router.get("/{chain_name}/block/{height}/transactions", response_class=HTMLResponse, name="block_transactions")
def block_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    height: int = Path(..., ge=0, description="Block height"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List transactions in a specific block.
    """
    # Get block
    block = service.get_block_by_height(height)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block #{height} not found")

    # Get transactions
    tx_ids = block.get("tx", [])

    # Apply pagination
    start = int(query_params.get("start", 0))
    count = int(query_params.get("count", 20))

    page_info = pagination.get_pagination_info(
        total=len(tx_ids),
        start=start,
        count=count,
    )

    # Get transaction details
    transactions = []
    paginated_tx_ids = tx_ids[page_info["start"] : page_info["start"] + page_info["count"]]
    for txid in paginated_tx_ids:
        tx = service.get_transaction(txid)
        if tx:
            transactions.append(tx)

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/block/{height}/transactions",
    }

    # Override url_base for offset-based pagination if that's what pagination_service expects
    # The existing logic used `start` and `count` for this one route, but `page` for others.
    # checking pagination service might be needed.

    # If the pagination service returns 'start'/'count' based navigation, the context needs to match.
    # But for now, sticking to the dict unpacking should work if templates are consistent.

    return templates.TemplateResponse(
        name="pages/block_transactions.html",
        context=context.build_context(
            title=f"Transactions in Block #{height}",
            block_height=height,
            transactions=transactions,
            **pagination_context
        ),
    )


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/blocks", response_class=HTMLResponse, name="legacy_blocks", include_in_schema=False)
def legacy_list_blocks(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy blocks list route."""
    return list_blocks(request, chain, service, pagination, templates, context, query_params)


@router.get("/chain/{chain_name}/block/{identifier}", response_class=HTMLResponse, name="legacy_block", include_in_schema=False)
def legacy_block_by_identifier(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    identifier: str = Path(...),
):
    """Legacy block detail route."""
    return block_by_identifier(request, chain, service, templates, context, identifier)
