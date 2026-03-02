#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MultiChain Explorer - Application State Manager

Modern configuration and state management using a singleton pattern.
Provides a clean, type-safe interface for application-wide state.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import ChainConfig

VERSION = "2.1.0"


def init_from_env() -> bool:
    """
    Initialize application state from .env file.

    Supports both single-chain (MULTICHAIN_*) and multi-chain (CHAIN_N_*)
    environment variable patterns.

    Returns:
        True if initialization successful, False otherwise
    """
    from env_config import get_settings, get_all_chain_settings

    try:
        settings = get_settings()
        chain_defs = get_all_chain_settings()  # returns 1..N chains
        state = get_state()

        # Build settings dict for backward compatibility
        chains_section = {cd["name"]: "on" for cd in chain_defs}
        state.settings = {
            "main": {
                "host": settings.explorer_host,
                "port": settings.explorer_port,
                "base": settings.base_url,
                "ini_dir": str(Path.cwd()),
            },
            "chains": chains_section,
        }
        # Add per-chain sections
        for cd in chain_defs:
            state.settings[cd["name"]] = {
                "name": cd["name"],
                "display-name": cd["name"],
                "rpchost": cd["host"],
                "rpcport": cd["port"],
                "rpcuser": cd["user"],
                "rpcpassword": cd["password"],
            }

        state.explorer_name = "multichain-explorer"
        state.ini_dir = Path.cwd()
        state.log_file = str(state.ini_dir / "explorer.log")
        state.pid_file = str(state.ini_dir / "explorer.pid")

        # Build ChainConfig objects for every discovered chain
        state.chains = [
            ChainConfig(
                name=cd["name"],
                display_name=cd["name"],
                path_name=cd["name"],
                ini_name=f"{cd['name']}.ini",
                rpc_host=cd["host"],
                rpc_port=int(cd["port"]),
                rpc_user=cd["user"],
                rpc_password=cd["password"],
            )
            for cd in chain_defs
        ]

        return True

    except Exception as e:
        print(f"Error initializing from .env: {e}")
        return False


@dataclass
class ApplicationState:
    """
    Central application state container.

    This class encapsulates all application configuration and runtime state
    in a structured, type-safe manner.
    """

    # Version
    version: str = VERSION

    # Configuration
    settings: Dict[str, Any] = field(default_factory=dict)

    # Paths
    feed_dir: Path = field(default_factory=Path)
    ini_dir: Path = field(default_factory=Path)
    ini_file: str = ""
    log_file: str = ""
    pid_file: str = ""

    # Metadata
    explorer_name: str = ""
    action: Optional[str] = None

    # Chains
    chains: List[ChainConfig] = field(default_factory=list)

    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration setting safely."""
        return self.settings.get(section, {}).get(key, default)

    def set_setting(self, section: str, key: str, value: Any) -> None:
        """Set configuration setting."""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value

    def get_chain_by_name(self, name: str) -> Optional[ChainConfig]:
        """Find chain by name or path-name."""
        for chain in self.chains:
            if chain.name == name or chain.path_name == name:
                return chain
        return None

    def is_configured(self) -> bool:
        """Check if application is configured."""
        return bool(self.settings)

    def reset(self) -> None:
        """Reset state to defaults."""
        self.settings = {}
        self.feed_dir = Path()
        self.ini_dir = Path()
        self.ini_file = ""
        self.log_file = ""
        self.pid_file = ""
        self.explorer_name = ""
        self.action = None
        self.chains = []


# Singleton instance
_state: Optional[ApplicationState] = None


def get_state() -> ApplicationState:
    """Get the global application state (singleton)."""
    global _state
    if _state is None:
        _state = ApplicationState()
    return _state


def reset_state() -> None:
    """Reset the global state."""
    global _state
    if _state:
        _state.reset()
    else:
        _state = ApplicationState()


# Convenience functions
def get_setting(section: str, key: str, default: Any = None) -> Any:
    """Get a configuration setting."""
    return get_state().get_setting(section, key, default)


def set_setting(section: str, key: str, value: Any) -> None:
    """Set a configuration setting."""
    get_state().set_setting(section, key, value)


def is_configured() -> bool:
    """Check if application is configured."""
    return get_state().is_configured()


def get_chain_count() -> int:
    """Get number of configured chains."""
    return len(get_state().chains)


def get_chain_by_name(name: str) -> Optional[Any]:
    """Find chain by name or path-name."""
    return get_state().get_chain_by_name(name)


def reset() -> None:
    """Reset application state."""
    reset_state()


__all__ = [
    "VERSION",
    "ApplicationState",
    "get_state",
    "reset_state",
    "get_setting",
    "set_setting",
    "is_configured",
    "get_chain_count",
    "get_chain_by_name",
    "reset",
    "init_from_env",
]
