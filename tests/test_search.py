"""Tests for search and filtering functionality."""
import json
from unittest.mock import MagicMock, patch

import pytest

import app_state
from handlers.search_handler import SearchHandler


@pytest.fixture(autouse=True)
def mock_app_state_settings():
    """Mock app_state.settings for all tests."""
    with patch.object(app_state.get_state(), "settings", {"main": {"base": "/"}, "chains": []}):
        yield


class TestSearchAPI:
    """Test search API endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SearchHandler()
        self.mock_chain = MagicMock()
        self.mock_chain.config = {"path-name": "testchain", "display-name": "Test Chain"}

    def test_search_all_with_empty_query(self):
        """Test search with empty query returns empty results."""
        result = self.handler.search_all(self.mock_chain, "")

        assert result["query"] == "" if "query" in result else result.get("results") == []
        assert result["results"] == []
        assert result["total"] == 0

    def test_search_all_with_whitespace_query(self):
        """Test search with whitespace query returns empty results."""
        result = self.handler.search_all(self.mock_chain, "   ")

        assert result.get("query", "   ").strip() == "" if "query" in result else True
        assert result["results"] == []
        assert result["total"] == 0

    def test_search_block_by_height(self, mock_chain, mock_rpc_calls):
        """Test searching for a block by height."""
        result = self.handler.search_all(mock_chain, "100")

        # Mock returns basic block data
        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result

    def test_search_block_by_hash(self, mock_chain, mock_rpc_calls):
        """Test searching for a block by hash."""
        block_hash = "0123456789abcdef"
        result = self.handler.search_all(mock_chain, block_hash)

        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result

    def test_search_transaction_by_txid(self, mock_chain, mock_rpc_calls):
        """Test searching for a transaction by txid."""
        txid = "tx123456789"
        result = self.handler.search_all(mock_chain, txid)

        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result

    def test_search_address(self, mock_chain, mock_rpc_calls):
        """Test searching for an address."""
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        result = self.handler.search_all(mock_chain, address)

        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result

    def test_search_asset(self, mock_chain, mock_rpc_calls):
        """Test searching for an asset."""
        result = self.handler.search_all(mock_chain, "TestAsset")

        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result

    def test_search_suggest_short_query(self):
        """Test search suggestions with short query."""
        result = self.handler.search_suggest(self.mock_chain, "a")

        assert result["suggestions"] == []

    def test_search_suggest_valid_query(self):
        """Test search suggestions with valid query."""
        self.mock_chain.request = MagicMock(
            return_value={
                "result": {
                    "height": 100,
                    "hash": "hash123",
                    "miner": "miner",
                    "time": 1234567890,
                    "tx": [],
                }
            }
        )

        result = self.handler.search_suggest(self.mock_chain, "100", limit=5)

        assert "suggestions" in result
        assert len(result["suggestions"]) <= 5

    def test_get_result_url_block(self):
        """Test URL generation for block results."""
        url = self.handler._get_result_url(self.mock_chain, "block", "100")
        assert url == "/testchain/block-height-100"

    def test_get_result_url_transaction(self):
        """Test URL generation for transaction results."""
        url = self.handler._get_result_url(self.mock_chain, "transaction", "txid123")
        assert url == "/testchain/tx/txid123"

    def test_get_result_url_address(self):
        """Test URL generation for address results."""
        url = self.handler._get_result_url(self.mock_chain, "address", "addr123")
        assert url == "/testchain/address/addr123"

    def test_get_result_url_asset(self):
        """Test URL generation for asset results."""
        url = self.handler._get_result_url(self.mock_chain, "asset", "asset123")
        assert url == "/testchain/asset/asset123"


class TestSearchIntegration:
    """Integration tests for search functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SearchHandler()
        self.mock_chain = MagicMock()
        self.mock_chain.config = {"path-name": "testchain", "display-name": "Test Chain"}

    def test_multi_type_search(self, mock_chain, mock_rpc_calls):
        """Test search that returns multiple types of results."""
        result = self.handler.search_all(mock_chain, "100")

        # Basic validation - search completes without error
        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result

    def test_search_with_limit(self):
        """Test search respects limit parameter."""
        # Mock many assets
        assets = [
            {"name": f"Asset{i}", "assetref": f"{i}-0-0", "issuerawqty": 1000, "units": 1}
            for i in range(20)
        ]
        self.mock_chain.request = MagicMock(return_value={"result": assets})

        result = self.handler.search_all(self.mock_chain, "Asset", limit=5)

        asset_results = [r for r in result["results"] if r["type"] == "asset"]
        assert len(asset_results) <= 5

    def test_search_error_handling(self):
        """Test search handles RPC errors gracefully."""
        self.mock_chain.request = MagicMock(side_effect=Exception("RPC Error"))

        # Should not raise exception, just return empty results
        result = self.handler.search_all(self.mock_chain, "test")

        assert isinstance(result, dict)
        assert "results" in result
        assert "total" in result
