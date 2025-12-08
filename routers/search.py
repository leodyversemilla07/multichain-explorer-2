#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Search Router - FastAPI routes for search operations.

Handles:
- Search functionality across the blockchain
"""

from typing import Dict

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from handlers.search_handler import SearchHandler
from routers.dependencies import (
    ChainDep,
    get_query_params,
)

router = APIRouter(tags=["Search"])


@router.post("/{chain_name}/search", response_class=HTMLResponse, name="search")
async def search(
    request: Request,
    chain: ChainDep,
    search_value: str = Form(None, description="Search query"),
):
    """
    Search the blockchain.
    
    Searches across blocks, transactions, addresses, assets, and streams.
    Automatically redirects to the found entity if there's an exact match.
    """
    # Get form data
    form_data = await request.form()
    query_params = dict(form_data)
    
    handler = SearchHandler()
    status, headers, body = handler.handle_search(chain, query_params)
    
    # Check if we need to redirect
    for header_name, header_value in headers:
        if header_name.lower() == "location":
            return RedirectResponse(url=header_value, status_code=302)
    
    return HTMLResponse(content=body, status_code=status)


@router.get("/{chain_name}/search", response_class=HTMLResponse, name="search_get")
async def search_get(
    request: Request,
    chain: ChainDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Search the blockchain (GET method).
    
    Alternative search endpoint using query parameters.
    """
    handler = SearchHandler()
    status, headers, body = handler.handle_search(chain, query_params)
    
    # Check if we need to redirect
    for header_name, header_value in headers:
        if header_name.lower() == "location":
            return RedirectResponse(url=header_value, status_code=302)
    
    return HTMLResponse(content=body, status_code=status)
