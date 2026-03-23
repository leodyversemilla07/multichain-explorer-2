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
    raise_backend_http_error,
)
from services.search_service import search_all_entities

router = APIRouter(tags=["Search"])


async def _run_search(
    chain: ChainDep,
    service: BlockchainServiceDep,
    query: str,
    *,
    limit: int | None = None,
) -> dict:
    """Execute shared search and preserve backend HTTP semantics."""
    try:
        return await search_all_entities(
            chain,
            service,
            query,
            limit=limit,
            include_stream_keys=True,
        )
    except Exception as exc:
        raise_backend_http_error(exc)


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
    query = search_value

    results = await _run_search(chain, service, query)
    
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

    results = await _run_search(chain, service, query)
    
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
    query = query_params.get("term", "")
    if not query:
        query = query_params.get("q", "")

    limit = 5

    search_results = await _run_search(chain, service, query, limit=limit)

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
