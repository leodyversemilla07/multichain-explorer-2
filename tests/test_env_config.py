"""
Tests for env_config.py - Environment configuration loading.
"""

import os
from unittest.mock import patch

import pytest


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
