from fastapi import APIRouter
from routers.api import blocks, transactions, addresses, assets, streams, search

api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(blocks.router)
api_router.include_router(transactions.router)
api_router.include_router(addresses.router)
api_router.include_router(assets.router)
api_router.include_router(streams.router)
api_router.include_router(search.router)
