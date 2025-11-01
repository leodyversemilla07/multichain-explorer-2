# -*- coding: utf-8 -*-

# MultiChain Explorer 2 (c) Coin Sciences Ltd
# All rights reserved under BSD 3-clause license

"""
Template rendering engine using Jinja2.

This module provides a centralized template rendering system that replaces
the old string-based template system in pages.py.
"""

import os
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

import app_state

# Template directory
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


class TemplateEngine:
    """
    Jinja2-based template engine for rendering HTML pages.

    Features:
    - Auto-escaping for XSS protection
    - Template caching for performance
    - Custom filters for MultiChain data
    - Component-based architecture
    """

    def __init__(self, template_dir: str = TEMPLATE_DIR):
        """
        Initialize the template engine.

        Args:
            template_dir: Path to templates directory
        """
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filters
        self._register_filters()

        # Register global variables
        self._register_globals()

    def _register_filters(self):
        """Register custom Jinja2 filters for MultiChain data."""

        def format_hash(value: str, length: int = 16) -> str:
            """Format a hash for display (truncate with ellipsis)."""
            if not value or len(value) <= length:
                return value
            half = length // 2
            return f"{value[:half]}...{value[-half:]}"

        def format_amount(value: float, decimals: int = 8) -> str:
            """Format an amount with proper decimals."""
            if value == 0:
                return "0"
            return f"{value:.{decimals}f}".rstrip("0").rstrip(".")

        def format_timestamp(value: int) -> str:
            """Format a Unix timestamp to human-readable date."""
            from datetime import datetime

            if not value:
                return "N/A"
            return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")

        # Register filters
        self.env.filters["format_hash"] = format_hash
        self.env.filters["format_amount"] = format_amount
        self.env.filters["format_timestamp"] = format_timestamp

    def _register_globals(self):
        """Register global variables available to all templates."""
        state = app_state.get_state()
        base_url = "/"
        if state.settings:  # type: ignore[truthy-bool]
            try:
                base_url = str(state.settings["main"]["base"])
            except (KeyError, TypeError):
                pass

        self.env.globals.update(
            {
                "version": getattr(state, "version", "2.0"),
                "base_url": base_url,
            }
        )

    def render(self, template_name: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template file (e.g., 'pages/chains.html')
            context: Dictionary of variables to pass to template
            **kwargs: Additional variables to pass to template

        Returns:
            Rendered HTML string

        Example:
            engine.render('pages/chains.html', {'chains': chain_list})
        """
        if context is None:
            context = {}

        # Merge context and kwargs
        template_vars = {**context, **kwargs}

        # Add default variables
        if "title" not in template_vars:
            template_vars["title"] = "MultiChain Explorer"

        # Render template
        template = self.env.get_template(template_name)
        result: str = template.render(**template_vars)
        return result

    def render_string(
        self, template_string: str, context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> str:
        """
        Render a template from a string.

        Args:
            template_string: Template string
            context: Dictionary of variables to pass to template
            **kwargs: Additional variables to pass to template

        Returns:
            Rendered HTML string
        """
        if context is None:
            context = {}

        template_vars = {**context, **kwargs}
        template = self.env.from_string(template_string)
        result: str = template.render(**template_vars)
        return result


# Global template engine instance
_template_engine: Optional[TemplateEngine] = None


def get_template_engine() -> TemplateEngine:
    """
    Get or create the global template engine instance.

    Returns:
        Singleton TemplateEngine instance
    """
    global _template_engine
    if _template_engine is None:
        _template_engine = TemplateEngine()
    return _template_engine


def render_template(template_name: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    """
    Convenience function to render a template.

    Args:
        template_name: Name of the template file
        context: Dictionary of variables to pass to template
        **kwargs: Additional variables to pass to template

    Returns:
        Rendered HTML string

    Example:
        html = render_template('pages/chains.html', chains=chain_list)
    """
    engine = get_template_engine()
    return engine.render(template_name, context, **kwargs)
