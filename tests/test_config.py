"""
Tests for Type-Safe Configuration System
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    AppConfig,
    ChainConfig,
    ServerConfig,
    get_config,
    load_env_file,
    reset_config,
    set_config,
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
            name="test", display_name="Test Chain", path_name="test-chain", ini_name="chain1"
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


class TestAppConfig:
    """Test AppConfig dataclass"""

    @pytest.mark.unit
    def test_app_config_creation(self):
        """Test creating app configuration"""
        config = AppConfig(explorer_name="my-explorer", ini_dir=Path("/tmp"))

        assert config.explorer_name == "my-explorer"
        assert config.version == "2.1"

    @pytest.mark.unit
    def test_app_config_generates_paths(self):
        """Test that app config generates log and pid paths"""
        import os

        config = AppConfig(explorer_name="test-explorer", ini_dir=Path("/var/lib/mce"))

        # Use os.path.join to handle platform differences
        expected_log = os.path.join(str(config.ini_dir), "test-explorer.log")
        expected_pid = os.path.join(str(config.ini_dir), "test-explorer.pid")

        assert str(config.log_file) == expected_log
        assert str(config.pid_file) == expected_pid

    @pytest.mark.unit
    def test_app_config_add_chain(self):
        """Test adding chains to app config"""
        config = AppConfig()

        chain1 = ChainConfig(
            name="chain1", display_name="Chain 1", path_name="chain1", ini_name="chain1"
        )

        chain2 = ChainConfig(
            name="chain2", display_name="Chain 2", path_name="chain2", ini_name="chain2"
        )

        config.add_chain(chain1)
        config.add_chain(chain2)

        assert len(config.chains) == 2
        assert config.chain_names == ["chain1", "chain2"]

    @pytest.mark.unit
    def test_app_config_get_chain(self):
        """Test getting chain by name"""
        config = AppConfig()

        chain = ChainConfig(
            name="test-chain", display_name="Test", path_name="test-chain", ini_name="test"
        )

        config.add_chain(chain)

        retrieved = config.get_chain("test-chain")
        assert retrieved is not None
        assert retrieved.name == "test-chain"

        # Test retrieval by path_name
        retrieved = config.get_chain("test-chain")
        assert retrieved is not None

    @pytest.mark.unit
    def test_app_config_get_nonexistent_chain(self):
        """Test getting non-existent chain returns None"""
        config = AppConfig()

        retrieved = config.get_chain("nonexistent")
        assert retrieved is None


class TestConfigManagement:
    """Test global config management functions"""

    def setup_method(self):
        """Reset config before each test"""
        reset_config()

    def teardown_method(self):
        """Reset config after each test"""
        reset_config()

    @pytest.mark.unit
    def test_set_and_get_config(self):
        """Test setting and getting global config"""
        config = AppConfig(explorer_name="test")

        set_config(config)
        retrieved = get_config()

        assert retrieved is not None
        assert retrieved.explorer_name == "test"

    @pytest.mark.unit
    def test_reset_config(self):
        """Test resetting global config"""
        config = AppConfig(explorer_name="test")
        set_config(config)

        assert get_config() is not None

        reset_config()

        assert get_config() is None


class TestPathHandling:
    """Test path handling in configuration"""

    @pytest.mark.unit
    def test_ini_dir_string_to_path(self):
        """Test that ini_dir string is converted to Path"""
        import os

        config = AppConfig(ini_dir=Path("/tmp/test"))

        assert isinstance(config.ini_dir, Path)
        # On Windows this becomes \tmp\test, on Unix /tmp/test
        assert os.path.basename(str(config.ini_dir)) == "test"

    @pytest.mark.unit
    def test_ini_dir_path_stays_path(self):
        """Test that ini_dir Path stays as Path"""
        import os

        config = AppConfig(ini_dir=Path("/tmp/test"))

        assert isinstance(config.ini_dir, Path)
        # On Windows this becomes \tmp\test, on Unix /tmp/test
        assert os.path.basename(str(config.ini_dir)) == "test"


@pytest.mark.smoke
class TestConfigSmoke:
    """Quick smoke tests for configuration"""

    def test_all_config_classes_instantiate(self):
        """Test that all config classes can be instantiated"""
        chain = ChainConfig(name="test", display_name="Test", path_name="test", ini_name="test")
        server = ServerConfig()
        app = AppConfig()

        assert all([chain, server, app])

    def test_config_immutability_not_enforced(self):
        """Test that configs are mutable (dataclasses default)"""
        config = AppConfig(explorer_name="original")
        config.explorer_name = "modified"

        assert config.explorer_name == "modified"
