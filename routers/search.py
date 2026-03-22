#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Search Router - FastAPI routes for search operations."""

from typing import Dict

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from routers.dependencies import (
    ChainDep,
    TemplatesDep,
    BlockchainServiceDep,
    CommonContextDep,
    get_query_params,
)
from services.search_service import search_all_entities

router = APIRouter(tags=["Search"])


@router.post("/{chain_name}/search", response_class=HTMLResponse, name="search")
async def search(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    search_value: str = Form(None, description="Search query"),
):
    """
    Search the blockchain.
    """
    # Prefer Form param, fallback to query param from request (legacy support)
    query = search_value
    
    # If using search_all logic
    results = await search_all_entities(chain, service, query, include_stream_keys=True)
    
    # Check if single result for redirect
    if results["total"] == 1:
        # Get the URL from the single result
        redirect_url = results["results"][0]["url"]
        return RedirectResponse(url=redirect_url, status_code=302)
    
    return templates.TemplateResponse(
        name="pages/search_results.html",
        context=context.build_context(
            title=f"Search: {query} - {chain.display_name}",
            query=query,
            results=results.get("results", []),
            total=results.get("total", 0),
        ),
    )


@router.get("/{chain_name}/search", response_class=HTMLResponse, name="search_get",
            summary="Search the blockchain")
async def search_get(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    templates: TemplatesDep,
    context: CommonContextDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Search the blockchain (GET method).
    """
    query = query_params.get("q", "")

    results = await search_all_entities(chain, service, query, include_stream_keys=True)
    
    # Check if single result for redirect
    if results["total"] == 1:
        # Get the URL from the single result
        redirect_url = results["results"][0]["url"]
        return RedirectResponse(url=redirect_url, status_code=302)

    return templates.TemplateResponse(
        name="pages/search_results.html",
        context=context.build_context(
            title=f"Search: {query} - {chain.display_name}",
            query=query,
            results=results.get("results", []),
            total=results.get("total", 0),
        ),
    )

@router.get("/{chain_name}/search/suggest", response_class=JSONResponse, name="search_suggest",
            summary="Search suggestions (autocomplete)")
async def search_suggest(
    request: Request,
    chain: ChainDep,
    service: BlockchainServiceDep,
    query_params: Dict[str, str] = Depends(get_query_params),
):
    """
    Auto-suggest search results for dropdown.
    """
    query = query_params.get("term", "") # 'term' is often used by jQuery UI Autocomplete, or 'q'
    if not query:
        query = query_params.get("q", "")

    limit = 5
    
    # Reuse search_all but limit results
    # We might want a lighter version but search_all is what we have.
    search_results = await search_all_entities(
        chain,
        service,
        query,
        limit=limit,
        include_stream_keys=True,
    )

    suggestions = []
    for result in search_results["results"][:limit]:
        suggestions.append(
            {
                "type": result["type"],
                "id": result["id"],
                "label": result["label"],
                "url": result.get("url", "/"),
            }
        )

    return {"suggestions": suggestions}
