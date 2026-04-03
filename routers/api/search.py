"""API Search Router - JSON endpoints for search operations."""

from fastapi import APIRouter, Depends
from routers.dependencies import (
    ChainDep,
    BlockchainServiceDep,
    get_base_url_dep,
    get_query_params_dep,
    raise_backend_http_error,
)
from services.search_service import search_all_entities

router = APIRouter(tags=["API Search"])


@router.get("/{chain_name}/search", name="api_search")
async def search(
    chain: ChainDep,
    service: BlockchainServiceDep,
    query_params: dict = Depends(get_query_params_dep),
    base_url: str = Depends(get_base_url_dep),
):
    """
    Search the blockchain (JSON).
    """
    query = query_params.get("q", "")
    try:
        return await search_all_entities(
            chain,
            service,
            query,
            include_stream_keys=False,
            base_url=base_url,
        )
    except Exception as exc:
        raise_backend_http_error(exc)
