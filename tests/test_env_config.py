"""
Tests for env_config.py - Environment configuration loading.
"""

import os
from unittest.mock import patch



class TestSettings:
    """Test Settings class."""

    def test_default_settings(self):
        """Test default settings values."""
        from env_config import Settings

        # Create settings with defaults (no env file)
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)

        assert settings.multichain_chain_name == "chain1"
        assert settings.multichain_rpc_host == "127.0.0.1"
        assert settings.multichain_rpc_port == 8000
        assert settings.multichain_rpc_username == "multichainrpc"
        assert settings.multichain_rpc_password == ""
        assert settings.explorer_host == "127.0.0.1"
        assert settings.explorer_port == 8080
        assert settings.debug is False
        assert settings.base_url == "/"

    def test_settings_from_env_vars(self):
        """Test settings loaded from environment variables."""
        from env_config import Settings

        env_vars = {
            "MULTICHAIN_CHAIN_NAME": "mychain",
            "MULTICHAIN_RPC_HOST": "192.168.1.100",
            "MULTICHAIN_RPC_PORT": "9000",
            "MULTICHAIN_RPC_USERNAME": "admin",
            "MULTICHAIN_RPC_PASSWORD": "secret123",
            "EXPLORER_HOST": "0.0.0.0",
            "EXPLORER_PORT": "3000",
            "DEBUG": "true",
            "BASE_URL": "/explorer/",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

        assert settings.multichain_chain_name == "mychain"
        assert settings.multichain_rpc_host == "192.168.1.100"
        assert settings.multichain_rpc_port == 9000
        assert settings.multichain_rpc_username == "admin"
        assert settings.multichain_rpc_password == "secret123"
        assert settings.explorer_host == "0.0.0.0"
        assert settings.explorer_port == 3000
        assert settings.debug is True
        assert settings.base_url == "/explorer/"

    def test_rpc_host_validator_strips_http(self):
        """Test that RPC host validator strips http:// prefix."""
        from env_config import Settings

        env_vars = {
            "MULTICHAIN_RPC_HOST": "http://192.168.1.100",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

        assert settings.multichain_rpc_host == "192.168.1.100"

    def test_rpc_host_validator_strips_https(self):
        """Test that RPC host validator strips https:// prefix."""
        from env_config import Settings

        env_vars = {
            "MULTICHAIN_RPC_HOST": "https://secure.example.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

        assert settings.multichain_rpc_host == "secure.example.com"

    def test_multichain_url_property(self):
        """Test multichain_url computed property."""
        from env_config import Settings

        env_vars = {
            "MULTICHAIN_RPC_HOST": "192.168.1.100",
            "MULTICHAIN_RPC_PORT": "9000",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

        assert settings.multichain_url == "http://192.168.1.100:9000"

    def test_rpc_auth_property(self):
        """Test rpc_auth computed property."""
        from env_config import Settings

        env_vars = {
            "MULTICHAIN_RPC_USERNAME": "admin",
            "MULTICHAIN_RPC_PASSWORD": "secret",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

        assert settings.rpc_auth == ("admin", "secret")

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        from env_config import Settings

        env_vars = {
            "multichain_chain_name": "lowercase_chain",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

        assert settings.multichain_chain_name == "lowercase_chain"


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        from env_config import Settings, get_settings, reload_settings

        # Clear cache first
        reload_settings()

        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self):
        """Test that get_settings returns cached instance."""
        from env_config import get_settings, reload_settings

        # Clear cache first
        reload_settings()

        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same object (cached)
        assert settings1 is settings2

    def test_reload_settings_clears_cache(self):
        """Test that reload_settings clears the cache."""
        from env_config import get_settings, reload_settings

        settings1 = get_settings()
        settings2 = reload_settings()

        # After reload, should be a new instance
        assert settings1 is not settings2


class TestSettingsEdgeCases:
    """Test edge cases for Settings."""

    def test_empty_password_allowed(self):
        """Test that empty password is allowed."""
        from env_config import Settings

        env_vars = {
            "MULTICHAIN_RPC_PASSWORD": "",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)

        assert settings.multichain_rpc_password == ""

    def test_extra_env_vars_ignored(self):
        """Test that extra environment variables are ignored."""
        from env_config import Settings

        env_vars = {
            "SOME_RANDOM_VAR": "value",
            "ANOTHER_UNKNOWN": "123",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Should not raise an error
            settings = Settings(_env_file=None)

        assert settings.multichain_chain_name == "chain1"  # Default value

    def test_debug_false_variations(self):
        """Test various false values for debug."""
        from env_config import Settings

        for false_val in ["false", "False", "FALSE", "0", "no", "No"]:
            env_vars = {"DEBUG": false_val}

            with patch.dict(os.environ, env_vars, clear=True):
                settings = Settings(_env_file=None)

            assert settings.debug is False, f"Failed for value: {false_val}"

    def test_debug_true_variations(self):
        """Test various true values for debug."""
        from env_config import Settings

        for true_val in ["true", "True", "TRUE", "1", "yes", "Yes"]:
            env_vars = {"DEBUG": true_val}

            with patch.dict(os.environ, env_vars, clear=True):
                settings = Settings(_env_file=None)

            assert settings.debug is True, f"Failed for value: {true_val}"


class TestGetAllChainSettings:
    """Test get_all_chain_settings() multi-chain env parsing."""

    def test_single_chain_fallback(self):
        """Falls back to MULTICHAIN_* when no CHAIN_N_* vars present."""
        from env_config import get_all_chain_settings, reload_settings

        env_vars = {
            "MULTICHAIN_CHAIN_NAME": "solo",
            "MULTICHAIN_RPC_HOST": "10.0.0.1",
            "MULTICHAIN_RPC_PORT": "7000",
            "MULTICHAIN_RPC_USERNAME": "admin",
            "MULTICHAIN_RPC_PASSWORD": "pass",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            reload_settings()
            chains = get_all_chain_settings()

        assert len(chains) == 1
        assert chains[0]["name"] == "solo"
        assert chains[0]["host"] == "10.0.0.1"
        assert chains[0]["port"] == "7000"

    def test_multi_chain_discovery(self):
        """Discovers multiple chains from CHAIN_N_* vars."""
        from env_config import get_all_chain_settings

        env_vars = {
            "CHAIN_1_NAME": "alpha",
            "CHAIN_1_HOST": "10.0.0.1",
            "CHAIN_1_PORT": "7001",
            "CHAIN_1_USER": "user1",
            "CHAIN_1_PASSWORD": "pw1",
            "CHAIN_2_NAME": "beta",
            "CHAIN_2_HOST": "10.0.0.2",
            "CHAIN_2_PORT": "7002",
            "CHAIN_2_USER": "user2",
            "CHAIN_2_PASSWORD": "pw2",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            chains = get_all_chain_settings()

        assert len(chains) == 2
        assert chains[0]["name"] == "alpha"
        assert chains[0]["port"] == "7001"
        assert chains[1]["name"] == "beta"
        assert chains[1]["port"] == "7002"

    def test_multi_chain_ordered_by_index(self):
        """Chains are returned in ascending numeric index order."""
        from env_config import get_all_chain_settings

        # Define out of order to verify sorting
        env_vars = {
            "CHAIN_3_NAME": "third",
            "CHAIN_3_HOST": "10.0.0.3",
            "CHAIN_3_PORT": "7003",
            "CHAIN_1_NAME": "first",
            "CHAIN_1_HOST": "10.0.0.1",
            "CHAIN_1_PORT": "7001",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            chains = get_all_chain_settings()

        assert chains[0]["name"] == "first"
        assert chains[1]["name"] == "third"

    def test_multi_chain_defaults_for_missing_fields(self):
        """Missing HOST/PORT/USER/PASSWORD fall back to sensible defaults."""
        from env_config import get_all_chain_settings

        env_vars = {
            "CHAIN_1_NAME": "minimal",
            # HOST, PORT, USER, PASSWORD omitted
        }
        with patch.dict(os.environ, env_vars, clear=True):
            chains = get_all_chain_settings()

        assert chains[0]["name"] == "minimal"
        assert chains[0]["host"] == "127.0.0.1"
        assert chains[0]["port"] == "8000"
        assert chains[0]["user"] == "multichainrpc"
        assert chains[0]["password"] == ""

    def test_numbered_chains_take_priority_over_multichain_vars(self):
        """When CHAIN_N_* exists, MULTICHAIN_* fallback is NOT used."""
        from env_config import get_all_chain_settings, reload_settings

        env_vars = {
            "CHAIN_1_NAME": "primary",
            "CHAIN_1_HOST": "10.0.0.1",
            # Also set MULTICHAIN_* to ensure they are ignored
            "MULTICHAIN_CHAIN_NAME": "ignored",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            reload_settings()
            chains = get_all_chain_settings()

        names = [c["name"] for c in chains]
        assert "primary" in names
        assert "ignored" not in names
