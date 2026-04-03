#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Blocks Router - FastAPI routes for block-related operations.

Handles:
- Block listing
- Block details (by height or hash)
- Block transactions
"""

import asyncio
from typing import Dict

from fastapi import APIRouter, Depends, Path, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    CommonContextDep,
    get_query_params_dep,
    get_page_info_from_query,
    get_page_info_from_start_count,
    get_start_count,
    raise_backend_http_error,
)

router = APIRouter(tags=["Blocks"])


@router.get(
    "/{chain_name}/blocks",
    response_class=HTMLResponse,
    name="blocks",
    summary="List blocks",
)
async def list_blocks(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List blocks in the blockchain.

    Displays paginated list of blocks with height, hash, time,
    and transaction count.
    """
    # Get blockchain info for total blocks
    info = await service.get_blockchain_info()
    total_blocks = info.get("blocks", 0)

    page_info = get_page_info_from_query(
        pagination,
        query_params,
        total=total_blocks,
    )

    blocks = await service.get_newest_blocks_page(
        total_blocks,
        start=page_info["start"],
        count=page_info["count"],
    )

    # Prepare pagination context
    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/blocks",
        include_component_fields=True,
        total_items=total_blocks,
    )

    return templates.TemplateResponse(
        name="pages/blocks.html",
        context=context.build_context(
            title=f"Blocks - {chain.display_name}",
            blocks=blocks,
            pagination=page_info,
            **pagination_context,
        ),
    )


@router.get(
    "/{chain_name}/block",
    response_class=RedirectResponse,
    name="block_redirect",
    summary="Redirect /block to /blocks",
)
async def block_redirect(
    chain_name: str = Path(..., description="Chain path name"),
):
    """
    Redirect /block to /blocks (common typo handling).
    """
    return RedirectResponse(
        url=f"/{chain_name}/blocks", status_code=status.HTTP_302_FOUND
    )


@router.get(
    "/{chain_name}/block/{identifier}",
    response_class=HTMLResponse,
    name="block",
    summary="Block details by height or hash",
)
async def block_by_identifier(
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
    try:
        if identifier.isdigit():
            height = int(identifier)
            block = await service.get_block_by_height(height)
        elif len(identifier) == 64:
            block = await service.get_block_by_hash(identifier)
            height = block.get("height") if block else None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid block identifier. Must be a height or 64-character hash.",
            )
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Block {identifier} not found")

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {identifier} not found",
        )

    height = block.get("height", 0)

    # Fetch full transaction details including size
    tx_ids = block.get("tx", [])
    tx_details = []

    results = await service.get_transactions_by_ids(tx_ids, return_exceptions=True)
    for res in results:
        if isinstance(res, dict):
            tx_details.append(res)

    return templates.TemplateResponse(
        name="pages/block.html",
        context=context.build_context(
            title=f"Block #{height}",
            block=block,
            tx_details=tx_details,
        ),
    )


@router.get(
    "/{chain_name}/blockhash/{block_hash}",
    response_class=HTMLResponse,
    name="block_by_hash",
    summary="Block details by hash",
)
async def block_by_hash(
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
    try:
        block = await service.get_block_by_hash(block_hash)
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Block {block_hash} not found")

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block {block_hash} not found",
        )

    return templates.TemplateResponse(
        name="pages/block.html",
        context=context.build_context(
            title=f"Block {block_hash[:16]}...",
            block=block,
        ),
    )


@router.get(
    "/{chain_name}/block/{height}/transactions",
    response_class=HTMLResponse,
    name="block_transactions",
    summary="Transactions in a block",
)
async def block_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    height: int = Path(..., ge=0, description="Block height"),
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """
    List transactions in a specific block.
    """
    # Get block
    try:
        block = await service.get_block_by_height(height)
    except Exception as exc:
        raise_backend_http_error(exc, not_found_detail=f"Block #{height} not found")
    if not block:
        raise HTTPException(status_code=404, detail=f"Block #{height} not found")

    # Get transactions
    tx_ids = block.get("tx", [])

    # Apply pagination
    start, count = get_start_count(query_params)
    page_info = get_page_info_from_start_count(
        pagination,
        total=len(tx_ids),
        start=start,
        count=count,
    )

    paginated_tx_ids, page_info = pagination.paginate(
        tx_ids,
        page=page_info["page"],
        items_per_page=page_info["count"],
    )

    results = await service.get_transactions_by_ids(
        paginated_tx_ids,
        return_exceptions=True,
    )
    transactions = [res for res in results if isinstance(res, dict)]

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/block/{height}/transactions",
    )

    return templates.TemplateResponse(
        name="pages/block_transactions.html",
        context=context.build_context(
            title=f"Transactions in Block #{height}",
            block_height=height,
            transactions=transactions,
            pagination=page_info,
            **pagination_context,
        ),
    )


# Legacy routes for backward compatibility
@router.get(
    "/chain/{chain_name}/blocks",
    response_class=HTMLResponse,
    name="legacy_blocks",
    include_in_schema=False,
)
async def legacy_list_blocks(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params_dep),
):
    """Legacy blocks list route."""
    return await list_blocks(
        request, chain, service, pagination, templates, context, query_params
    )


@router.get(
    "/chain/{chain_name}/block/{identifier}",
    response_class=HTMLResponse,
    name="legacy_block",
    include_in_schema=False,
)
async def legacy_block_by_identifier(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    identifier: str = Path(...),
):
    """Legacy block detail route."""
    return await block_by_identifier(
        request, chain, service, templates, context, identifier
    )
