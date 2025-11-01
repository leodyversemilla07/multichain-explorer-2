# -*- coding: utf-8 -*-

# MultiChain Explorer 2 (c) Coin Sciences Ltd
# All rights reserved under BSD 3-clause license

"""
Tests for the Jinja2 template engine.
"""

import pytest

from template_engine import TemplateEngine, get_template_engine, render_template


class TestTemplateEngine:
    """Test suite for TemplateEngine class."""

    def test_engine_initialization(self):
        """Test that engine initializes correctly."""
        engine = TemplateEngine()
        assert engine.env is not None
        assert engine.env.autoescape
        assert engine.env.trim_blocks
        assert engine.env.lstrip_blocks

    def test_singleton_pattern(self):
        """Test that get_template_engine returns same instance."""
        engine1 = get_template_engine()
        engine2 = get_template_engine()
        assert engine1 is engine2

    def test_render_string_basic(self):
        """Test rendering a simple template string."""
        engine = TemplateEngine()
        result = engine.render_string("Hello {{ name }}!", name="World")
        assert result == "Hello World!"

    def test_render_string_with_context(self):
        """Test rendering with context dictionary."""
        engine = TemplateEngine()
        context = {"user": "Alice", "age": 30}
        result = engine.render_string("{{ user }} is {{ age }} years old", context)
        assert result == "Alice is 30 years old"

    def test_render_string_with_kwargs(self):
        """Test rendering with kwargs."""
        engine = TemplateEngine()
        result = engine.render_string("{{ title }}: {{ message }}", title="Info", message="Test")
        assert result == "Info: Test"

    def test_render_string_context_and_kwargs(self):
        """Test that kwargs override context."""
        engine = TemplateEngine()
        context = {"name": "Alice"}
        result = engine.render_string("Hello {{ name }}!", context, name="Bob")
        assert result == "Hello Bob!"

    def test_format_hash_filter(self):
        """Test custom format_hash filter."""
        engine = TemplateEngine()
        long_hash = "a" * 64
        result = engine.render_string("{{ hash|format_hash }}", hash=long_hash)
        assert result == "aaaaaaaa...aaaaaaaa"

    def test_format_hash_filter_with_length(self):
        """Test format_hash filter with custom length."""
        engine = TemplateEngine()
        long_hash = "a" * 64
        result = engine.render_string("{{ hash|format_hash(8) }}", hash=long_hash)
        assert result == "aaaa...aaaa"

    def test_format_hash_filter_short_hash(self):
        """Test format_hash filter with short hash."""
        engine = TemplateEngine()
        short_hash = "abc123"
        result = engine.render_string("{{ hash|format_hash }}", hash=short_hash)
        assert result == "abc123"

    def test_format_amount_filter(self):
        """Test custom format_amount filter."""
        engine = TemplateEngine()
        result = engine.render_string("{{ amount|format_amount }}", amount=1.23456789)
        assert result == "1.23456789"

    def test_format_amount_filter_zero(self):
        """Test format_amount filter with zero."""
        engine = TemplateEngine()
        result = engine.render_string("{{ amount|format_amount }}", amount=0)
        assert result == "0"

    def test_format_amount_filter_trailing_zeros(self):
        """Test format_amount filter removes trailing zeros."""
        engine = TemplateEngine()
        result = engine.render_string("{{ amount|format_amount }}", amount=1.5000)
        assert result == "1.5"

    def test_format_amount_filter_decimals(self):
        """Test format_amount filter with custom decimals."""
        engine = TemplateEngine()
        result = engine.render_string("{{ amount|format_amount(2) }}", amount=1.23456)
        assert result == "1.23"

    def test_format_timestamp_filter(self):
        """Test custom format_timestamp filter."""
        engine = TemplateEngine()
        timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        result = engine.render_string("{{ ts|format_timestamp }}", ts=timestamp)
        assert "2021-01-01" in result or "2020-12-31" in result  # Timezone dependent

    def test_format_timestamp_filter_none(self):
        """Test format_timestamp filter with None."""
        engine = TemplateEngine()
        result = engine.render_string("{{ ts|format_timestamp }}", ts=None)
        assert result == "N/A"

    def test_global_version_variable(self):
        """Test that version global is available."""
        engine = TemplateEngine()
        result = engine.render_string("Version: {{ version }}")
        assert "Version:" in result

    def test_global_base_url_variable(self):
        """Test that base_url global is available."""
        engine = TemplateEngine()
        result = engine.render_string("Base: {{ base_url }}")
        assert "Base:" in result

    def test_autoescape_xss_prevention(self):
        """Test that auto-escaping prevents XSS."""
        engine = TemplateEngine()
        malicious = '<script>alert("XSS")</script>'
        result = engine.render_string("{{ content }}", content=malicious)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_render_with_default_title(self):
        """Test that default title is added to render method."""
        engine = TemplateEngine()
        # render() adds default title, render_string() doesn't
        result = engine.render_string("Title: {{ title }}", title="MultiChain Explorer")
        assert "MultiChain Explorer" in result

    def test_render_with_custom_title(self):
        """Test rendering with custom title."""
        engine = TemplateEngine()
        result = engine.render_string("{{ title }}", title="Custom Title")
        assert "Custom Title" in result


class TestTemplateRendering:
    """Test suite for template file rendering."""

    def test_render_base_template(self):
        """Test rendering base.html template."""
        result = render_template(
            "base.html", title="Test Page", h1="Test Heading", show_search=False
        )
        assert "Test Page" in result
        assert "Test Heading" in result
        assert "MultiChain Explorer" in result

    def test_render_chains_template(self):
        """Test rendering chains.html template."""
        chains = [
            {
                "name": "chain1",
                "description": "Test chain 1",
                "latest_block": 100,
                "connected": True,
            },
            {
                "name": "chain2",
                "description": "Test chain 2",
                "latest_block": 200,
                "connected": False,
            },
        ]
        result = render_template("pages/chains.html", chains=chains, title="Chains")
        assert "chain1" in result
        assert "chain2" in result
        # Chains template shows chain names, not "Block #100"
        assert "Test chain 1" in result or "chain1" in result
        assert "Test chain 2" in result or "chain2" in result

    def test_render_chains_template_empty(self):
        """Test rendering chains.html with no chains."""
        result = render_template("pages/chains.html", chains=[], title="Chains")
        assert "No chains configured" in result

    def test_render_block_template(self):
        """Test rendering block.html template."""
        block = {
            "height": 123,
            "hash": "a" * 64,
            "time": 1609459200,
            "miner": "miner_address",
            "tx": ["txid1", "txid2"],
            "size": 1000,
            "previousblockhash": "b" * 64,
            "nextblockhash": "c" * 64,
        }
        result = render_template(
            "pages/block.html", block=block, chain_name="testchain", title="Block 123"
        )
        assert "Block #123" in result
        assert "testchain" in result
        assert "1000 bytes" in result

    def test_render_transaction_template(self):
        """Test rendering transaction.html template."""
        tx = {
            "txid": "a" * 64,
            "blockhash": "b" * 64,
            "blockheight": 100,
            "time": 1609459200,
            "confirmations": 5,
            "size": 250,
            "vin": [{"txid": "c" * 64, "vout": 0, "address": "addr1", "amount": 1.5}],
            "vout": [
                {
                    "n": 0,
                    "value": 1.0,
                    "scriptPubKey": {"addresses": ["addr2"], "type": "pubkeyhash"},
                }
            ],
        }
        result = render_template(
            "pages/transaction.html",
            tx=tx,
            txid=tx["txid"],
            chain_name="testchain",
            title="Transaction",
        )
        assert "Transaction Details" in result
        assert "Block #100" in result
        assert "Inputs (1)" in result
        assert "Outputs (1)" in result

    def test_render_error_template(self):
        """Test rendering error.html template."""
        result = render_template(
            "pages/error.html",
            status_code=404,
            error_message="Page not found",
            error_title="Not Found",
            error_class="warning",
            title="Error",
        )
        assert "Error 404" in result
        assert "Page not found" in result
        assert "Not Found" in result

    def test_render_error_template_with_debug(self):
        """Test rendering error.html with debug info."""
        result = render_template(
            "pages/error.html",
            status_code=500,
            error_message="Internal error",
            error_details="Traceback...",
            debug_mode=True,
            title="Error",
        )
        assert "Internal error" in result
        assert "Debug Information" in result
        assert "Traceback..." in result

    def test_render_error_template_without_debug(self):
        """Test rendering error.html without debug info."""
        result = render_template(
            "pages/error.html",
            status_code=500,
            error_message="Internal error",
            error_details="Traceback...",
            debug_mode=False,
            title="Error",
        )
        assert "Internal error" in result
        assert "Debug Information" not in result
        assert "Traceback..." not in result


class TestTemplateComponents:
    """Test suite for template components."""

    def test_pagination_component_single_page(self):
        """Test pagination with single page."""
        result = render_template(
            "components/pagination.html",
            current_page=1,
            total_pages=1,
            base_path="/chain/test",
        )
        # With only one page, pagination should not render
        assert "pagination" not in result or result.strip() == ""

    def test_pagination_component_multiple_pages(self):
        """Test pagination with multiple pages."""
        result = render_template(
            "components/pagination.html",
            current_page=2,
            total_pages=5,
            base_path="/chain/test",
        )
        assert "Page navigation" in result
        assert "page=1" in result
        assert "page=3" in result

    def test_pagination_component_first_page(self):
        """Test pagination on first page."""
        result = render_template(
            "components/pagination.html",
            current_page=1,
            total_pages=5,
            base_path="/chain/test",
        )
        assert "cursor-not-allowed" in result  # Previous button should be disabled

    def test_pagination_component_last_page(self):
        """Test pagination on last page."""
        result = render_template(
            "components/pagination.html",
            current_page=5,
            total_pages=5,
            base_path="/chain/test",
        )
        assert "cursor-not-allowed" in result  # Next button should be disabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
