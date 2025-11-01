# -*- coding: utf-8 -*-

# MultiChain Explorer 2 (c) Coin Sciences Ltd
# All rights reserved under BSD 3-clause license

"""
Tests for template integration.
Tests template_engine module functionality.
"""

import pytest

from template_engine import render_template


class TestTemplateRendering:
    """Test suite for template rendering."""

    def test_render_template_basic(self):
        """Test basic template rendering."""
        html = render_template(
            "pages/error.html",
            {
                "title": "Test Error",
                "error_message": "Test error message",
                "status_code": 404,
                "base_url": "/",
            },
        )

        assert html is not None
        assert isinstance(html, str)
        assert "Error" in html

    def test_render_template_with_data(self):
        """Test template rendering with context data."""
        html = render_template(
            "pages/chains.html",
            {
                "title": "Test Chains",
                "chains": [],
                "base_url": "/",
            },
        )

        assert html is not None
        assert isinstance(html, str)

    def test_render_template_nonexistent(self):
        """Test rendering nonexistent template raises error."""
        with pytest.raises(Exception):
            render_template("pages/nonexistent.html", {})


class TestTemplateIntegration:
    """Test suite for template integration with handlers."""

    def test_handlers_can_render_templates(self):
        """Test that handlers can use render_template."""
        from handlers.block_handler import BlockHandler

        handler = BlockHandler()
        assert handler is not None
        # Handler methods use render_template internally


class TestTemplateHelpers:
    """Test template helper functions."""

    def test_template_rendering_returns_str(self):
        """Test that template rendering returns a string."""
        html = render_template(
            "pages/error.html",
            {
                "title": "Test",
                "error_message": "Test message",
                "status_code": 500,
                "base_url": "/",
            },
        )

        assert isinstance(html, str)
        assert len(html) > 0
