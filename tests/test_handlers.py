# -*- coding: utf-8 -*-

# MultiChain Explorer 2 (c) Coin Sciences Ltd
# All rights reserved under BSD 3-clause license

"""
Unit tests for handler base class.

Tests the common functionality provided by BaseHandler.
"""

import pytest

from handlers.base import BaseHandler


class TestBaseHandler:
    """Test suite for BaseHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a base handler instance for testing."""
        return BaseHandler(
            chain_name="test-chain",
            base_url="/explorer",
            use_new_templates=True,
        )

    def test_initialization(self, handler):
        """Test handler initialization."""
        assert handler.chain_name == "test-chain"
        assert handler.base_url == "/explorer"
        assert isinstance(handler.use_new_templates, bool)

    def test_error_response_generation(self, handler):
        """Test error response generation."""
        html = handler.error_response(404, "Not Found", "Resource not found", "Check the URL")
        assert "404" in html
        assert "Not Found" in html
        assert "Resource not found" in html

    def test_not_found_response(self, handler):
        """Test 404 not found response."""
        html = handler.not_found_response("block", "12345")
        assert "404" in html
        assert "Block Not Found" in html or "block" in html.lower()
        assert "12345" in html

    def test_json_response(self, handler):
        """Test JSON response generation."""
        data = {"test": "value", "number": 123}
        json_str = handler.json_response(data)
        assert '"test": "value"' in json_str
        assert '"number": 123' in json_str

    def test_build_url_without_params(self, handler):
        """Test URL building without parameters."""
        url = handler.build_url("/test/path")
        assert url == "/test/path"

    def test_build_url_with_params(self, handler):
        """Test URL building with parameters."""
        url = handler.build_url("/test/path", {"page": 2, "limit": 50})
        assert "/test/path?" in url
        assert "page=2" in url
        assert "limit=50" in url

    def test_build_url_filters_none_values(self, handler):
        """Test URL building filters out None values."""
        url = handler.build_url("/test/path", {"page": 2, "empty": None})
        assert "/test/path?" in url
        assert "page=2" in url
        assert "empty" not in url

    def test_format_hash_short(self, handler):
        """Test hash formatting for short hashes."""
        short_hash = "abcd1234"
        formatted = handler.format_hash(short_hash, length=16)
        assert formatted == short_hash

    def test_format_hash_long(self, handler):
        """Test hash formatting for long hashes."""
        long_hash = "a" * 64
        formatted = handler.format_hash(long_hash, length=8)
        assert "..." in formatted
        assert formatted.startswith("aaaaaaaa")
        assert formatted.endswith("aaaaaaaa")

    def test_format_amount_integer(self, handler):
        """Test amount formatting for integers."""
        formatted = handler.format_amount(100.0, decimals=8)
        assert formatted == "100"

    def test_format_amount_decimal(self, handler):
        """Test amount formatting with decimals."""
        formatted = handler.format_amount(100.12345678, decimals=8)
        assert "100.12345678" in formatted

    def test_create_pagination_context_first_page(self, handler):
        """Test pagination context for first page."""
        context = handler.create_pagination_context(
            current_page=1, total_items=100, items_per_page=20, base_path="/blocks"
        )
        assert context["current_page"] == 1
        assert context["total_pages"] == 5
        assert context["has_prev"] is False
        assert context["has_next"] is True
        assert context["next_page"] == 2
        assert context["prev_page"] is None

    def test_create_pagination_context_middle_page(self, handler):
        """Test pagination context for middle page."""
        context = handler.create_pagination_context(
            current_page=3, total_items=100, items_per_page=20, base_path="/blocks"
        )
        assert context["current_page"] == 3
        assert context["total_pages"] == 5
        assert context["has_prev"] is True
        assert context["has_next"] is True
        assert context["prev_page"] == 2
        assert context["next_page"] == 4

    def test_create_pagination_context_last_page(self, handler):
        """Test pagination context for last page."""
        context = handler.create_pagination_context(
            current_page=5, total_items=100, items_per_page=20, base_path="/blocks"
        )
        assert context["current_page"] == 5
        assert context["total_pages"] == 5
        assert context["has_prev"] is True
        assert context["has_next"] is False
        assert context["prev_page"] == 4
        assert context["next_page"] is None

    def test_create_pagination_context_out_of_bounds(self, handler):
        """Test pagination context handles out of bounds page numbers."""
        context = handler.create_pagination_context(
            current_page=999, total_items=100, items_per_page=20, base_path="/blocks"
        )
        # Should clamp to last page
        assert context["current_page"] == 5
        assert context["total_pages"] == 5

    def test_create_pagination_context_empty_results(self, handler):
        """Test pagination context with no results."""
        context = handler.create_pagination_context(
            current_page=1, total_items=0, items_per_page=20, base_path="/blocks"
        )
        assert context["total_pages"] == 1
        assert context["current_page"] == 1


class TestBaseHandlerWithoutTemplates:
    """Test BaseHandler behavior when templates are not available."""

    @pytest.fixture
    def handler(self):
        """Create a handler with templates disabled."""
        return BaseHandler(
            chain_name="test-chain",
            base_url="/explorer",
            use_new_templates=False,  # Disable templates
        )

    def test_error_response_fallback(self, handler):
        """Test error response falls back to HTML when templates disabled."""
        html = handler.error_response(404, "Not Found", "Resource not found")
        assert "404" in html
        assert "Not Found" in html
        assert "<html>" in html.lower()
        assert "</html>" in html.lower()

    def test_render_template_response_fallback(self, handler):
        """Test template rendering falls back when templates disabled."""
        fallback = "<h1>Fallback HTML</h1>"
        result = handler.render_template_response(
            "test.html", {"data": "value"}, fallback_html=fallback
        )
        assert result == fallback
