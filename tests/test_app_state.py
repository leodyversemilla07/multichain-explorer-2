"""Tests for app_state.py."""

from unittest.mock import Mock, patch


class TestApplicationState:
    """Test ApplicationState helpers and singleton behavior."""

    def test_get_chain_by_name_matches_name_and_path(self):
        """Chain lookup should match either canonical name or path name."""
        from app_state import ApplicationState

        chain = Mock()
        chain.name = "chain-one"
        chain.path_name = "chain-path"

        state = ApplicationState()
        state.chains = [chain]

        assert state.get_chain_by_name("chain-one") is chain
        assert state.get_chain_by_name("chain-path") is chain
        assert state.get_chain_by_name("missing") is None

    def test_reset_state_resets_singleton_instance(self):
        """Global reset should leave a fresh ApplicationState available."""
        import app_state

        state = app_state.get_state()
        state.settings = {"main": {"base": "/"}}
        state.explorer_name = "custom"

        app_state.reset_state()
        fresh_state = app_state.get_state()

        assert fresh_state.settings == {}
        assert fresh_state.explorer_name == ""


class TestInitFromEnv:
    """Test .env-backed state initialization."""

    def test_init_from_env_builds_state(self):
        """Environment-backed settings should populate state and chains."""
        import app_state

        settings = Mock()
        settings.explorer_host = "127.0.0.1"
        settings.explorer_port = 8080
        settings.base_url = "/"

        chain_defs = [
            {
                "name": "alpha",
                "host": "127.0.0.1",
                "port": 8570,
                "user": "rpcuser",
                "password": "rpcpass",
            }
        ]

        app_state.reset_state()
        with (
            patch("env_config.get_settings", return_value=settings),
            patch("env_config.get_all_chain_settings", return_value=chain_defs),
        ):
            result = app_state.init_from_env()

        state = app_state.get_state()
        assert result is True
        assert state.settings["main"]["base"] == "/"
        assert state.settings["chains"] == {"alpha": "on"}
        assert len(state.chains) == 1
        assert state.chains[0].name == "alpha"
        assert state.chains[0].rpc_user == "rpcuser"

    def test_init_from_env_logs_and_returns_false_on_failure(self):
        """Init failures should be logged and reported as False."""
        import app_state

        with (
            patch("env_config.get_settings", side_effect=RuntimeError("boom")),
            patch("app_state.logger.warning") as mock_warning,
        ):
            result = app_state.init_from_env()

        assert result is False
        mock_warning.assert_called_once()
