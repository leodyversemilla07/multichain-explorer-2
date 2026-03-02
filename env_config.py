# -*- coding: utf-8 -*-

"""
MultiChain Explorer 2 - Environment Configuration

Loads configuration from .env file using pydantic-settings.
This replaces the legacy .ini file configuration.
"""

import os
from functools import lru_cache
from typing import Optional, List, Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Environment variables can be set in a .env file or directly in the environment.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # MultiChain Connection
    multichain_chain_name: str = Field(
        default="chain1",
        description="Name of the MultiChain blockchain",
    )
    multichain_rpc_host: str = Field(
        default="127.0.0.1",
        description="MultiChain RPC host address",
    )
    multichain_rpc_port: int = Field(
        default=8000,
        description="MultiChain RPC port",
    )
    multichain_rpc_username: str = Field(
        default="multichainrpc",
        description="MultiChain RPC username",
    )
    multichain_rpc_password: str = Field(
        default="",
        description="MultiChain RPC password",
    )
    
    # Explorer Settings
    explorer_host: str = Field(
        default="127.0.0.1",
        description="Host to bind the explorer to",
    )
    explorer_port: int = Field(
        default=8080,
        description="Port for the explorer web interface",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    
    # Optional: Base URL for reverse proxy setups
    base_url: str = Field(
        default="/",
        description="Base URL prefix for all routes",
    )

    # Cache backend selection
    cache_backend: str = Field(
        default="memory",
        description="Cache backend to use: 'memory' (default) or 'redis'",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL (used only when cache_backend=redis)",
    )
    
    @field_validator("multichain_rpc_host")
    @classmethod
    def validate_rpc_host(cls, v: str) -> str:
        """Ensure RPC host doesn't have scheme prefix."""
        if v.startswith("http://") or v.startswith("https://"):
            # Strip the scheme - we'll add it back when needed
            v = v.replace("https://", "").replace("http://", "")
        return v
    
    @property
    def multichain_url(self) -> str:
        """Get the full MultiChain RPC URL."""
        return f"http://{self.multichain_rpc_host}:{self.multichain_rpc_port}"
    
    @property
    def rpc_auth(self) -> tuple[str, str]:
        """Get RPC authentication tuple."""
        return (self.multichain_rpc_username, self.multichain_rpc_password)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Returns:
        Settings instance loaded from environment
    """
    return Settings()


def reload_settings() -> Settings:
    """
    Reload settings (clears cache).

    Returns:
        Fresh Settings instance
    """
    get_settings.cache_clear()
    return get_settings()


def get_all_chain_settings() -> List[Dict[str, str]]:
    """
    Discover all chain configurations from environment variables.

    Supports two patterns:
    1. Numbered multi-chain: CHAIN_1_NAME, CHAIN_1_HOST, CHAIN_1_PORT,
       CHAIN_1_USER, CHAIN_1_PASSWORD  (then CHAIN_2_*, CHAIN_3_*, ...)
    2. Single-chain fallback: MULTICHAIN_CHAIN_NAME, MULTICHAIN_RPC_HOST, etc.

    Returns:
        List of chain dicts with keys: name, host, port, user, password
    """
    chains: List[Dict[str, str]] = []

    # Scan for numbered CHAIN_N_NAME keys (case-insensitive via uppercase)
    env = {k.upper(): v for k, v in os.environ.items()}
    indices = sorted(
        int(k.split("_")[1])
        for k in env
        if k.startswith("CHAIN_") and k.endswith("_NAME") and k.split("_")[1].isdigit()
    )

    for n in indices:
        prefix = f"CHAIN_{n}_"
        name = env.get(f"{prefix}NAME", "")
        if not name:
            continue
        chains.append({
            "name": name,
            "host": env.get(f"{prefix}HOST", "127.0.0.1"),
            "port": env.get(f"{prefix}PORT", "8000"),
            "user": env.get(f"{prefix}USER", "multichainrpc"),
            "password": env.get(f"{prefix}PASSWORD", ""),
        })

    # Fall back to single-chain MULTICHAIN_* vars when no numbered chains found
    if not chains:
        settings = get_settings()
        chains.append({
            "name": settings.multichain_chain_name,
            "host": settings.multichain_rpc_host,
            "port": str(settings.multichain_rpc_port),
            "user": settings.multichain_rpc_username,
            "password": settings.multichain_rpc_password,
        })

    return chains
