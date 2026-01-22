"""
Tests for multichain.py - MultiChain RPC client.
"""

import json
from unittest.mock import Mock, patch, MagicMock

import pytest

import app_state


class TestIsMissing:
    """Test is_missing helper function."""

    def test_missing_key(self):
        """Test with missing key."""
        from multichain import is_missing

        config = {"other": "value"}
        assert is_missing(config, "missing") is True

    def test_none_value(self):
        """Test with None value."""
        from multichain import is_missing

        config = {"key": None}
        assert is_missing(config, "key") is True

    def test_empty_string(self):
        """Test with empty string value."""
        from multichain import is_missing

        config = {"key": ""}
        assert is_missing(config, "key") is True

    def test_valid_value(self):
        """Test with valid value."""
        from multichain import is_missing

        config = {"key": "value"}
        assert is_missing(config, "key") is False

    def test_zero_value(self):
        """Test with zero value (should be valid)."""
        from multichain import is_missing

        config = {"key": 0}
        assert is_missing(config, "key") is False

    def test_empty_list(self):
        """Test with empty list (str conversion has length 2 for '[]')."""
        from multichain import is_missing

        config = {"key": []}
        # Note: is_missing uses len(str(config[key])), and str([]) == "[]" which has length 2
        assert is_missing(config, "key") is False


class TestMCEChain:
    """Test MCEChain class."""

    @pytest.fixture
    def chain_settings(self):
        """Set up chain settings in app_state."""
        settings = {
            "test-chain": {
                "name": "test-chain",
                "display-name": "Test Chain",
                "rpchost": "127.0.0.1",
                "rpcport": "8570",
                "rpcuser": "testuser",
                "rpcpassword": "testpass",
            }
        }
        app_state.get_state().settings = settings
        return settings

    def test_chain_initialization(self, chain_settings):
        """Test MCEChain initialization."""
        from multichain import MCEChain

        chain = MCEChain("test-chain")

        assert chain.name == "test-chain"
        assert chain.config["name"] == "test-chain"
        assert chain.config["ini-name"] == "test-chain"
        assert chain.config["path-name"] == "test-chain"
        assert chain.config["path-ini-name"] == "test-chain"

    def test_chain_initialize_creates_url_and_headers(self, chain_settings):
        """Test that initialize() creates RPC URL and headers."""
        from multichain import MCEChain

        chain = MCEChain("test-chain")
        result = chain.initialize()

        assert result is True
        assert chain.config["multichain-url"] == "http://127.0.0.1:8570"
        assert "multichain-headers" in chain.config
        assert chain.config["multichain-headers"]["Content-Type"] == "application/json"
        assert "Authorization" in chain.config["multichain-headers"]

    def test_chain_initialize_default_host(self):
        """Test initialize with missing rpchost uses default."""
        settings = {
            "test-chain": {
                "name": "test-chain",
                "rpcport": "8570",
                "rpcuser": "user",
                "rpcpassword": "pass",
            }
        }
        app_state.get_state().settings = settings

        from multichain import MCEChain

        chain = MCEChain("test-chain")
        chain.initialize()

        assert chain.config["multichain-url"] == "http://127.0.0.1:8570"

    def test_chain_path_name_url_encoded(self):
        """Test that path-name is URL encoded."""
        settings = {
            "chain with spaces": {
                "name": "chain with spaces",
                "rpchost": "localhost",
                "rpcport": "8570",
                "rpcuser": "user",
                "rpcpassword": "pass",
            }
        }
        app_state.get_state().settings = settings

        from multichain import MCEChain

        chain = MCEChain("chain with spaces")

        assert chain.config["path-name"] == "chain+with+spaces"

    def test_request_success(self, chain_settings):
        """Test successful RPC request."""
        from multichain import MCEChain

        chain = MCEChain("test-chain")
        chain.initialize()

        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {"result": {"blocks": 100}, "error": None, "id": 1}
        ).encode("utf-8")

        with patch("multichain.request.urlopen", return_value=mock_response):
            result = chain.request("getblockcount")

        assert result["result"] == {"blocks": 100}
        assert result["error"] is None

    def test_request_with_params(self, chain_settings):
        """Test RPC request with parameters."""
        from multichain import MCEChain

        chain = MCEChain("test-chain")
        chain.initialize()

        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {"result": "blockhash123", "error": None, "id": 1}
        ).encode("utf-8")

        with patch("multichain.request.urlopen", return_value=mock_response) as mock_urlopen:
            result = chain.request("getblockhash", [100])

        assert result["result"] == "blockhash123"
        # Verify the request was made with params
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        request_data = json.loads(request_obj.data.decode("utf-8"))
        assert request_data["method"] == "getblockhash"
        assert request_data["params"] == [100]

    def test_request_http_error(self, chain_settings):
        """Test RPC request with HTTP error (RPC error response)."""
        from multichain import MCEChain
        import urllib.error

        chain = MCEChain("test-chain")
        chain.initialize()

        error_response = json.dumps(
            {"result": None, "error": {"code": -5, "message": "Block not found"}, "id": 1}
        ).encode("utf-8")

        mock_error = urllib.error.HTTPError(
            url="http://localhost:8570",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=Mock(read=Mock(return_value=error_response)),
        )
        mock_error.read = Mock(return_value=error_response)

        with patch("multichain.request.urlopen", side_effect=mock_error):
            result = chain.request("getblock", ["invalidhash"])

        assert result["result"] is None
        assert "Error -5" in result["error"]

    def test_request_url_error(self, chain_settings):
        """Test RPC request with URL error (connection refused)."""
        from multichain import MCEChain
        import urllib.error

        chain = MCEChain("test-chain")
        chain.initialize()

        mock_error = urllib.error.URLError("Connection refused")

        with patch("multichain.request.urlopen", side_effect=mock_error):
            result = chain.request("getinfo")

        assert result["result"] is None
        assert "MultiChain is not running" in result["error"]
        assert result.get("connection-error") is True

    def test_request_preserves_order(self, chain_settings):
        """Test that response preserves JSON object order."""
        from multichain import MCEChain
        from collections import OrderedDict

        chain = MCEChain("test-chain")
        chain.initialize()

        # Response with specific key order
        response_str = '{"result": {"z": 1, "a": 2, "m": 3}, "error": null, "id": 1}'
        mock_response = Mock()
        mock_response.read.return_value = response_str.encode("utf-8")

        with patch("multichain.request.urlopen", return_value=mock_response):
            result = chain.request("test")

        # Should preserve order due to object_pairs_hook=OrderedDict
        keys = list(result["result"].keys())
        assert keys == ["z", "a", "m"]


class TestMCEChainIntegration:
    """Integration-style tests for MCEChain."""

    @pytest.fixture
    def configured_chain(self):
        """Create a fully configured chain."""
        settings = {
            "main-chain": {
                "name": "main-chain",
                "display-name": "Main Chain",
                "rpchost": "192.168.1.100",
                "rpcport": "9570",
                "rpcuser": "admin",
                "rpcpassword": "adminpass",
            }
        }
        app_state.get_state().settings = settings

        from multichain import MCEChain

        chain = MCEChain("main-chain")
        chain.initialize()
        return chain

    def test_auth_header_is_base64_encoded(self, configured_chain):
        """Test that authorization header is properly base64 encoded."""
        import base64

        auth_header = configured_chain.config["multichain-headers"]["Authorization"]
        assert auth_header.startswith("Basic ")

        # Decode and verify
        encoded_part = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(encoded_part).decode("ascii")
        assert decoded == "admin:adminpass"

    def test_headers_include_required_fields(self, configured_chain):
        """Test that headers include all required fields."""
        headers = configured_chain.config["multichain-headers"]

        assert headers["Content-Type"] == "application/json"
        assert headers["Connection"] == "close"
        assert "Authorization" in headers
