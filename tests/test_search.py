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

    def test_search_block_by_height(self):
        """Test searching for a block by height."""
        self.mock_chain.request = MagicMock(
            side_effect=[
                {"result": "blockhash123"},  # getblockhash
                {
                    "result": {  # getblock
                        "height": 100,
                        "hash": "blockhash123",
                        "miner": "miner_address",
                        "time": 1234567890,
                        "tx": ["tx1", "tx2", "tx3"],
                    }
                },
            ]
        )

        result = self.handler.search_all(self.mock_chain, "100")

        assert result["total"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["type"] == "block"
        assert result["results"][0]["id"] == "100"
        assert result["results"][0]["meta"]["hash"] == "blockhash123"
        assert result["results"][0]["meta"]["txcount"] == 3

    def test_search_block_by_hash(self):
        """Test searching for a block by hash."""
        block_hash = "0123456789abcdef"
        self.mock_chain.request = MagicMock(
            side_effect=[
                {
                    "result": {  # getblock
                        "height": 150,
                        "hash": block_hash,
                        "miner": "miner_address",
                        "time": 1234567890,
                        "tx": ["tx1", "tx2"],
                    }
                },
                {"error": "not found"},  # getrawtransaction (fails)
                {"result": {"isvalid": False}},  # validateaddress (invalid)
                {"result": []},  # listassets (no results)
            ]
        )

        result = self.handler.search_all(self.mock_chain, block_hash)

        assert result["total"] >= 1
        block_results = [r for r in result["results"] if r["type"] == "block"]
        assert len(block_results) == 1
        assert block_results[0]["id"] == "150"
        assert block_results[0]["meta"]["hash"] == block_hash

    def test_search_transaction_by_txid(self):
        """Test searching for a transaction by txid."""
        txid = "tx123456789"
        self.mock_chain.request = MagicMock(
            return_value={
                "result": {
                    "txid": txid,
                    "confirmations": 10,
                    "time": 1234567890,
                    "vin": [{"txid": "input1"}],
                    "vout": [{"value": 100}, {"value": 50}],
                }
            }
        )

        result = self.handler.search_all(self.mock_chain, txid)

        assert result["total"] >= 1
        tx_results = [r for r in result["results"] if r["type"] == "transaction"]
        assert len(tx_results) == 1
        assert tx_results[0]["id"] == txid
        assert tx_results[0]["meta"]["confirmations"] == 10

    def test_search_address(self):
        """Test searching for an address."""
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        self.mock_chain.request = MagicMock(
            side_effect=[
                {"error": "not found"},  # getblock (fails - not a block hash)
                {"error": "not found"},  # getrawtransaction (fails - not a txid)
                {"result": {"isvalid": True, "ismine": False}},  # validateaddress
                {"result": [{"assetref": "0-0-0", "qty": 1000}]},  # getaddressbalances
                {"result": []},  # listassets (no results)
            ]
        )

        result = self.handler.search_all(self.mock_chain, address)

        assert result["total"] >= 1
        addr_results = [r for r in result["results"] if r["type"] == "address"]
        assert len(addr_results) == 1
        assert addr_results[0]["id"] == address
        assert addr_results[0]["meta"]["balance"] == 1000

    def test_search_asset(self):
        """Test searching for an asset."""
        self.mock_chain.request = MagicMock(
            return_value={
                "result": [
                    {
                        "name": "TestAsset",
                        "assetref": "123-456-789",
                        "issuerawqty": 1000000,
                        "units": 1,
                    }
                ]
            }
        )

        result = self.handler.search_all(self.mock_chain, "TestAsset")

        assert result["total"] >= 1
        asset_results = [r for r in result["results"] if r["type"] == "asset"]
        assert len(asset_results) == 1
        assert asset_results[0]["meta"]["name"] == "TestAsset"

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

    def test_multi_type_search(self):
        """Test search that returns multiple types of results."""
        # Mock responses for different entity types
        self.mock_chain.request = MagicMock(
            side_effect=[
                {"result": "hash123"},  # getblockhash
                {
                    "result": {
                        "height": 100,
                        "hash": "hash123",
                        "miner": "addr",
                        "time": 123,
                        "tx": [],
                    }
                },  # getblock
                {
                    "result": {
                        "txid": "100",
                        "confirmations": 5,
                        "time": 123,
                        "vin": [],
                        "vout": [],
                    }
                },  # getrawtransaction
                {"result": {"isvalid": False}},  # validateaddress (invalid)
                {"result": []},  # listassets (no results)
            ]
        )

        result = self.handler.search_all(self.mock_chain, "100")

        # Should find block and potentially transaction
        assert result["total"] >= 1
        assert any(r["type"] == "block" for r in result["results"])

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
