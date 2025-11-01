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

VERSION = "2.1"


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
    selected: Optional[Any] = None

    # Chains
    chains: List[Any] = field(default_factory=list)

    # Handlers (runtime)
    page_handler: Optional[Any] = None

    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration setting safely."""
        return self.settings.get(section, {}).get(key, default)

    def set_setting(self, section: str, key: str, value: Any) -> None:
        """Set configuration setting."""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value

    def get_chain_by_name(self, name: str) -> Optional[Any]:
        """Find chain by name or path-name."""
        for chain in self.chains:
            if hasattr(chain, "config"):
                if chain.config.get("name") == name or chain.config.get("path-name") == name:
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
        self.selected = None
        self.chains = []
        self.page_handler = None


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
]
