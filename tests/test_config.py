"""
Tests for Type-Safe Configuration System
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (  # noqa: E402
    ChainConfig,
    ServerConfig,
)


class TestChainConfig:
    """Test ChainConfig dataclass"""

    @pytest.mark.unit
    def test_chain_config_creation(self):
        """Test creating a chain configuration"""
        chain = ChainConfig(
            name="test-chain",
            display_name="Test Chain",
            path_name="test-chain",
            ini_name="chain1",
            rpc_port=8570,
            rpc_user="test",
            rpc_password="secret",
        )

        assert chain.name == "test-chain"
        assert chain.display_name == "Test Chain"
        assert chain.rpc_port == 8570

    @pytest.mark.unit
    def test_chain_config_generates_url(self):
        """Test that chain config generates RPC URL"""
        chain = ChainConfig(
            name="test",
            display_name="Test",
            path_name="test",
            ini_name="test",
            rpc_host="192.168.1.100",
            rpc_port=8570,
            rpc_user="user",
            rpc_password="pass",
        )

        assert chain.multichain_url == "http://192.168.1.100:8570"

    @pytest.mark.unit
    def test_chain_config_generates_headers(self):
        """Test that chain config generates auth headers"""
        chain = ChainConfig(
            name="test",
            display_name="Test",
            path_name="test",
            ini_name="test",
            rpc_user="testuser",
            rpc_password="testpass",
        )

        assert "Authorization" in chain.multichain_headers
        assert "Basic" in chain.multichain_headers["Authorization"]

    @pytest.mark.unit
    def test_chain_config_backward_compatibility(self):
        """Test that chain config creates legacy config dict"""
        chain = ChainConfig(
            name="test",
            display_name="Test Chain",
            path_name="test-chain",
            ini_name="chain1",
        )

        assert "name" in chain.config
        assert "display-name" in chain.config
        assert "path-name" in chain.config
        assert chain.config["name"] == "test"


class TestServerConfig:
    """Test ServerConfig dataclass"""

    @pytest.mark.unit
    def test_server_config_defaults(self):
        """Test server config default values"""
        server = ServerConfig()

        assert server.host == "127.0.0.1"
        assert server.port == 4444
        assert server.base_url == "/"

    @pytest.mark.unit
    def test_server_config_from_dict(self):
        """Test server config from dictionary"""
        config_dict = {"host": "0.0.0.0", "port": 8080, "base": "/explorer/"}

        server = ServerConfig.from_env(config_dict)

        assert server.host == "0.0.0.0"
        assert server.port == 8080
        assert server.base_url == "/explorer/"

    @pytest.mark.unit
    def test_server_config_env_override(self):
        """Test server config environment variable override"""
        # Set environment variables
        os.environ["MCE_HOST"] = "192.168.1.1"
        os.environ["MCE_PORT"] = "9999"
        os.environ["MCE_BASE_URL"] = "/test/"

        try:
            server = ServerConfig.from_env()

            assert server.host == "192.168.1.1"
            assert server.port == 9999
            assert server.base_url == "/test/"
        finally:
            # Clean up
            del os.environ["MCE_HOST"]
            del os.environ["MCE_PORT"]
            del os.environ["MCE_BASE_URL"]


@pytest.mark.smoke
class TestConfigSmoke:
    """Quick smoke tests for configuration"""

    def test_all_config_classes_instantiate(self):
        """Test that all config classes can be instantiated"""
        chain = ChainConfig(
            name="test", display_name="Test", path_name="test", ini_name="test"
        )
        server = ServerConfig()

        assert all([chain, server])
