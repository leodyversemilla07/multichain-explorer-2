"""
FastAPI Routers for MultiChain Explorer 2.

This package contains modular routers for different entity types.
"""

from routers import (
    chains,
    blocks,
    transactions,
    addresses,
    assets,
    streams,
    search,
    permissions,
)

__all__ = [
    "chains",
    "blocks",
    "transactions",
    "addresses",
    "assets",
    "streams",
    "search",
    "permissions",
]
