#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MultiChain Explorer - Configuration Module (Compatibility Layer)

DEPRECATED: This module is kept for backward compatibility only.
New code should use 'app_state' module instead.

This module re-exports everything from app_state to maintain
compatibility with existing code that imports 'cfg'.
"""

import warnings

from app_state import *  # noqa: F401, F403
from app_state import get_state as _get_state

# Show deprecation warning on first import
warnings.warn(
    "Module 'cfg' is deprecated. Use 'app_state' instead.", DeprecationWarning, stacklevel=2
)


# Backward compatibility: expose state attributes as module-level
def __getattr__(name: str):
    """Provide backward compatibility for module-level access."""
    from app_state import VERSION, get_state

    state = get_state()

    # Special handling for version
    if name == "version":
        return VERSION

    # Handle deprecated data_handler
    if name == "data_handler":
        return state.page_handler

    # Delegate to state
    if hasattr(state, name):
        value = getattr(state, name)
        # Convert Path objects to strings for backward compatibility
        from pathlib import Path

        if isinstance(value, Path):
            return str(value)
        return value

    raise AttributeError(f"module 'cfg' has no attribute '{name}'")


def __setattr__(name: str, value):
    """Provide backward compatibility for module-level setting."""
    from pathlib import Path

    from app_state import VERSION, get_state

    state = get_state()

    # Prevent setting version
    if name in ("version", "VERSION"):
        raise AttributeError("Cannot modify version constant")

    # Handle deprecated data_handler
    if name == "data_handler":
        state.page_handler = value
        return

    # Convert string paths to Path objects
    if name in ("feed_dir", "ini_dir") and isinstance(value, str):
        value = Path(value)

    # Set on state
    if hasattr(state, name):
        setattr(state, name, value)
    else:
        raise AttributeError(f"module 'cfg' has no attribute '{name}'")
