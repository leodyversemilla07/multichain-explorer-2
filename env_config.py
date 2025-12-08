# -*- coding: utf-8 -*-

"""
MultiChain Explorer 2 - Environment Configuration

Loads configuration from .env file using pydantic-settings.
This replaces the legacy .ini file configuration.
"""

import os
from functools import lru_cache
from typing import Optional

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
