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

from typing import Dict

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import HTMLResponse, JSONResponse

from handlers.transaction_handler import TransactionHandler
from routers.dependencies import (
    ChainDep,
    get_query_params,
)

router = APIRouter(tags=["Transactions"])


@router.get("/{chain_name}/transactions", response_class=HTMLResponse, name="transactions")
async def list_transactions(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    List recent transactions.
    
    Displays paginated list of transactions across the blockchain.
    """
    handler = TransactionHandler()
    status, headers, body = handler.handle_transactions_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/tx/{txid}", response_class=HTMLResponse, name="transaction")
async def transaction_detail(
    request: Request,
    chain: ChainDep,
    txid: str = Path(..., min_length=64, max_length=64, description="Transaction ID"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Show transaction details.
    
    Displays comprehensive transaction information including:
    - Inputs and outputs
    - Asset transfers
    - Stream operations
    - Permissions changes
    """

    handler = TransactionHandler()
    status, headers, body = handler.handle_transaction_detail(chain, txid, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/tx/{txid}/raw", response_class=JSONResponse, name="raw_transaction")
async def raw_transaction(
    request: Request,
    chain: ChainDep,
    txid: str = Path(..., min_length=64, max_length=64, description="Transaction ID"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Get raw transaction data as JSON.
    
    Returns the complete transaction data in JSON format.
    """

    handler = TransactionHandler()
    status, headers, body = handler.handle_raw_transaction(chain, txid, query_params)
    
    # Check content type from headers
    content_type = "application/json"
    for header_name, header_value in headers:
        if header_name.lower() == "content-type":
            content_type = header_value
            break
    
    if "json" in content_type.lower():
        return JSONResponse(content=body.decode("utf-8") if isinstance(body, bytes) else body, status_code=status)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/tx/{txid}/hex", response_class=HTMLResponse, name="raw_transaction_hex")
async def raw_transaction_hex(
    request: Request,
    chain: ChainDep,
    txid: str = Path(..., min_length=64, max_length=64, description="Transaction ID"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Get raw transaction hex data.
    
    Returns the raw transaction in hexadecimal format.
    """

    handler = TransactionHandler()
    status, headers, body = handler.handle_raw_transaction_hex(chain, txid, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/tx/{txid}/output/{n}", response_class=HTMLResponse, name="tx_output_data")
async def transaction_output(
    request: Request,
    chain: ChainDep,
    txid: str = Path(..., min_length=64, max_length=64, description="Transaction ID"),
    n: int = Path(..., ge=0, description="Output index"),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Get transaction output data.
    
    Returns data for a specific output in a transaction.
    """

    handler = TransactionHandler()
    status, headers, body = handler.handle_tx_output_data(chain, txid, n, query_params)
    return HTMLResponse(content=body, status_code=status)


# Legacy routes for backward compatibility
@router.get("/chain/{chain_name}/transactions", response_class=HTMLResponse, name="legacy_transactions", include_in_schema=False)
async def legacy_list_transactions(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy transactions list route."""
    handler = TransactionHandler()
    status, headers, body = handler.handle_transactions_list(chain, query_params)
    return HTMLResponse(content=body, status_code=status)


@router.get("/chain/{chain_name}/tx/{txid}", response_class=HTMLResponse, name="legacy_transaction", include_in_schema=False)
async def legacy_transaction_detail(
    request: Request,
    chain: ChainDep,
    txid: str = Path(..., min_length=64, max_length=64),
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """Legacy transaction detail route."""

    handler = TransactionHandler()
    status, headers, body = handler.handle_transaction_detail(chain, txid, query_params)
    return HTMLResponse(content=body, status_code=status)
