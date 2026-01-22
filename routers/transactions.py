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

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Path, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    PaginationServiceDep,
    CommonContextDep,
    get_query_params,
)

router = APIRouter(tags=["Transactions"])


@router.get("/{chain_name}/transactions", response_class=HTMLResponse, name="transactions")
def list_transactions(
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
    page = int(query_params.get("page", 1))
    count = int(query_params.get("count", 20))
    
    # Get recent confirmed transactions (newest blocks first)
    info = service.get_blockchain_info()
    current_height = info.get("blocks", 0)

    # Calculate how many transactions we need to fetch
    # We need enough to fill the current page plus know if there's a next page
    needed = page * count + 1
    max_txs = min(needed, 200)  # Cap at 200 to prevent excessive fetching
    
    recent_txs = []
    # Scan recent blocks only - limit to 50 blocks max for performance
    max_blocks_to_scan = 50
    blocks_scanned = 0
    
    for height in range(current_height, -1, -1):
        if blocks_scanned >= max_blocks_to_scan or len(recent_txs) >= max_txs:
            break
            
        block = service.get_block_by_height(height)
        blocks_scanned += 1
        
        if block and "tx" in block:
            block_time = block.get("time")
            block_height = block.get("height", height)
            confirmations = current_height - block_height + 1
            
            for txid in block["tx"]:
                if len(recent_txs) >= max_txs:
                    break
                # Create lightweight tx info without fetching full tx details
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

    pagination_context = {
        "page": page_info["page"],
        "page_count": page_info["page_count"],
        "has_next": page_info["has_next"],
        "has_prev": page_info["has_prev"],
        "next_page": page_info["next_page"],
        "prev_page": page_info["prev_page"],
        "url_base": f"/{chain.config['path-name']}/transactions",
        "total": len(all_txs),
        # For pagination component
        "total_pages": page_info["page_count"],
        "page_number": page_info["page"],
        "base_path": f"/{chain.config['path-name']}/transactions",
    }

    return templates.TemplateResponse(
        name="pages/transactions.html",
        context=context.build_context(
            title=f"Recent Transactions - {chain.config['display-name']}",
            transactions=paginated_txs,
            pagination=pagination_context,
            **pagination_context
        ),
    )


@router.get("/{chain_name}/tx/{txid}", response_class=HTMLResponse, name="transaction")
def transaction_detail(
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
    transaction = service.get_transaction(txid)

    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")

    return templates.TemplateResponse(
        name="pages/transaction.html",
        context=context.build_context(
            title=f"Transaction {txid[:16]}...",
            txid=txid,
            tx=transaction,
        ),
    )


@router.get("/{chain_name}/tx/{txid}/raw", response_class=JSONResponse, name="raw_transaction")
def raw_transaction(
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
        transaction = service.call("getrawtransaction", [txid, 1])
        if not transaction:
            raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")
    except Exception:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")

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


@router.get("/{chain_name}/tx/{txid}/hex", response_class=HTMLResponse, name="raw_transaction_hex")
def raw_transaction_hex(
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
        hex_data = service.call("getrawtransaction", [txid, 0])
        if not hex_data:
            raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")
    except Exception:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")

    return templates.TemplateResponse(
        name="pages/raw_transaction_hex.html",
        context=context.build_context(
            title=f"Raw TX Hex - {txid[:16]}...",
            txid=txid,
            hex=hex_data,
        ),
    )


@router.get("/{chain_name}/tx/{txid}/output/{n}", response_class=HTMLResponse, name="tx_output_data")
def transaction_output(
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
    transaction = service.get_transaction(txid)
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction {txid} not found")

    # Get specific output
    vouts = transaction.get("vout", [])
    if n >= len(vouts):
        raise HTTPException(status_code=404, detail=f"Output {n} not found in transaction")

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
def legacy_list_transactions(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    pagination: PaginationServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy transactions list route."""
    return list_transactions(request, chain, service, pagination, templates, context, query_params)


@router.get("/chain/{chain_name}/tx/{txid}", response_class=HTMLResponse, name="legacy_transaction", include_in_schema=False)
def legacy_transaction_detail(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    txid: str = Path(..., min_length=64, max_length=64),
):
    """Legacy transaction detail route."""
    return transaction_detail(request, chain, service, templates, context, txid)
