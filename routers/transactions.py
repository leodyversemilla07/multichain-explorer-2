#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Transactions Router - FastAPI routes for transaction-related operations.

Handles:
- Transaction listing
- Transaction details
- Raw transaction data
- Transaction output data
"""

import asyncio
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Path, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    CommonContextDep,
    get_query_params,
    get_page_count,
    raise_backend_http_error,
)

router = APIRouter(tags=["Transactions"])


def _raise_transaction_http_error(txid: str, exc: Exception) -> None:
    """Map backend transaction errors to the correct HTTP response."""
    raise_backend_http_error(exc, not_found_detail=f"Transaction {txid} not found")


@router.get("/{chain_name}/transactions", response_class=HTMLResponse, name="transactions",
            summary="List recent transactions")
async def list_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List recent transactions.
    
    Displays paginated list of transactions across the blockchain.
    """
    # Apply pagination first to minimize work
    page, count = get_page_count(query_params)
    
    # Get recent confirmed transactions (newest blocks first)
    info = await service.get_blockchain_info()
    current_height = info.get("blocks", 0)

    # Calculate how many transactions we need to fetch
    # We need enough to fill the current page plus know if there's a next page
    needed = page * count + 1
    max_txs = min(needed, 200)  # Cap at 200 to prevent excessive fetching
    
    recent_txs = []
    # Scan recent blocks — fetch in parallel batches for performance
    max_blocks_to_scan = 50
    scan_end = max(current_height - max_blocks_to_scan, -1)
    heights_to_scan = list(range(current_height, scan_end, -1))

    # Fetch blocks in parallel
    block_results = await asyncio.gather(
        *[service.get_block_by_height(h) for h in heights_to_scan],
        return_exceptions=True,
    )

    block_errors = [result for result in block_results if isinstance(result, Exception)]
    if block_errors and len(block_errors) == len(block_results):
        raise_backend_http_error(block_errors[0])

    for i, block in enumerate(block_results):
        if len(recent_txs) >= max_txs:
            break

        if isinstance(block, Exception):
            continue

        if block and "tx" in block:
            block_time = block.get("time")
            block_height = block.get("height", heights_to_scan[i])
            confirmations = current_height - block_height + 1

            for txid in block["tx"]:
                if len(recent_txs) >= max_txs:
                    break
                recent_txs.append({
                    "txid": txid,
                    "blockheight": block_height,
                    "confirmations": confirmations,
                    "time": block_time,
                })

    all_txs = recent_txs

    page_info = pagination.get_pagination_info(
        total=len(all_txs),
        page=page,
        items_per_page=count,
    )

    paginated_txs = all_txs[page_info["start"] : page_info["start"] + page_info["count"]]

    pagination_context = pagination.build_context(
        page_info,
        f"/{chain.path_name}/transactions",
        include_component_fields=True,
        total_items=len(all_txs),
    )

    return templates.TemplateResponse(
        name="pages/transactions.html",
        context=context.build_context(
            title=f"Recent Transactions - {chain.display_name}",
            transactions=paginated_txs,
            pagination=page_info,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/tx/{txid}", response_class=HTMLResponse, name="transaction",
            summary="Transaction details")
async def transaction_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    txid: str = Path(..., min_length=64, max_length=64, description="Transaction ID"),
):
    """
    Show transaction details.
    """
    try:
        transaction = await service.get_transaction(txid)
    except Exception as exc:
        _raise_transaction_http_error(txid, exc)

    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction {txid} not found")

    return templates.TemplateResponse(
        name="pages/transaction.html",
        context=context.build_context(
            title=f"Transaction {txid[:16]}...",
            txid=txid,
            tx=transaction,
        ),
    )


@router.get("/{chain_name}/tx/{txid}/raw", response_class=JSONResponse, name="raw_transaction",
            summary="Raw transaction JSON")
async def raw_transaction(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    txid: str = Path(..., min_length=64, max_length=64, description="Transaction ID"),
):
    """
    Get raw transaction data as JSON.
    """
    try:
        transaction = await service.call("getrawtransaction", [txid, 1])
        if not transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction {txid} not found")
    except Exception as exc:
        _raise_transaction_http_error(txid, exc)

    # If the client accepts JSON, return JSON. Otherwise return the HTML view of the JSON.
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return transaction

    # Default to HTML view of the raw JSON
    return templates.TemplateResponse(
        name="pages/raw_transaction.html",
        context=context.build_context(
            title=f"Raw Transaction - {txid[:16]}...",
            txid=txid,
            transaction=transaction,
        ),
    )


@router.get("/{chain_name}/tx/{txid}/hex", response_class=HTMLResponse, name="raw_transaction_hex",
            summary="Raw transaction hex")
async def raw_transaction_hex(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    txid: str = Path(..., min_length=64, max_length=64, description="Transaction ID"),
):
    """
    Get raw transaction hex data.
    """
    try:
        hex_data = await service.call("getrawtransaction", [txid, 0])
        if not hex_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction {txid} not found")
    except Exception as exc:
        _raise_transaction_http_error(txid, exc)

    return templates.TemplateResponse(
        name="pages/raw_transaction_hex.html",
        context=context.build_context(
            title=f"Raw TX Hex - {txid[:16]}...",
            txid=txid,
            hex=hex_data,
        ),
    )


@router.get("/{chain_name}/tx/{txid}/output/{n}", response_class=HTMLResponse, name="tx_output_data",
            summary="Transaction output data")
async def transaction_output(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    txid: str = Path(..., min_length=64, max_length=64, description="Transaction ID"),
    n: int = Path(..., ge=0, description="Output index"),
):
    """
    Get transaction output data.
    """
    try:
        transaction = await service.get_transaction(txid)
    except Exception as exc:
        _raise_transaction_http_error(txid, exc)

    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")

    # Get specific output
    vouts = transaction.get("vout", [])
    if n >= len(vouts):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Output {n} not found in transaction")

    output = vouts[n]

    return templates.TemplateResponse(
        name="pages/tx_output_data.html",
        context=context.build_context(
            title=f"TX Output - {txid[:16]}... #{n}",
            txid=txid,
            vout=n,
            output=output,
        ),
    )


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/transactions", response_class=HTMLResponse, name="legacy_transactions", include_in_schema=False)
async def legacy_list_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy transactions list route."""
    return await list_transactions(request, chain, service, pagination, templates, context, query_params)


@router.get("/chain/{chain_name}/tx/{txid}", response_class=HTMLResponse, name="legacy_transaction", include_in_schema=False)
async def legacy_transaction_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    txid: str = Path(..., min_length=64, max_length=64),
):
    """Legacy transaction detail route."""
    return await transaction_detail(request, chain, service, templates, context, txid)
