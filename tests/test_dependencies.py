"""
Tests for routers/dependencies.py - FastAPI dependency injection.
"""

from unittest.mock import Mock, patch, MagicMock

import pytest

import app_state
from exceptions import ChainNotFoundError


class TestGetBaseUrl:
    """Test get_base_url dependency."""

    def test_get_base_url_default(self):
        """Test get_base_url returns default when not set."""
        from routers.dependencies import get_base_url

        # Save original settings
        original = app_state.get_state().settings.copy()
        app_state.get_state().settings = {}
        try:
            result = get_base_url()
            assert result == "/"
        finally:
            app_state.get_state().settings = original

    def test_get_base_url_custom(self):
        """Test get_base_url returns custom value."""
        from routers.dependencies import get_base_url

        original = app_state.get_state().settings.copy()
        app_state.get_state().settings = {"main": {"base": "/explorer/"}}
        try:
            result = get_base_url()
            assert result == "/explorer/"
        finally:
            app_state.get_state().settings = original


class TestGetChain:
    """Test get_chain dependency."""

    @pytest.fixture
    def mock_chains(self):
        """Set up mock chains in app_state."""
        chain1 = Mock()
        chain1.config = {
            "name": "chain1",
            "path-name": "chain1",
            "display-name": "Chain One",
        }

        chain2 = Mock()
        chain2.config = {
            "name": "chain2",
            "path-name": "chain2",
            "display-name": "Chain Two",
        }

        app_state.get_state().chains = [chain1, chain2]
        return [chain1, chain2]

    def test_get_chain_found(self, mock_chains):
        """Test get_chain finds existing chain."""
        from routers.dependencies import get_chain

        result = get_chain("chain1")
        assert result.config["name"] == "chain1"

    def test_get_chain_not_found(self, mock_chains):
        """Test get_chain raises error for nonexistent chain."""
        from routers.dependencies import get_chain

        with pytest.raises(ChainNotFoundError) as exc_info:
            get_chain("nonexistent")

        assert exc_info.value.chain_name == "nonexistent"

    def test_get_chain_empty_chains(self):
        """Test get_chain with no chains configured."""
        from routers.dependencies import get_chain

        app_state.get_state().chains = []

        with pytest.raises(ChainNotFoundError):
            get_chain("anychain")

    def test_get_chain_none_chains(self):
        """Test get_chain with chains set to None."""
        from routers.dependencies import get_chain

        app_state.get_state().chains = None

        with pytest.raises(ChainNotFoundError):
            get_chain("anychain")


class TestGetBlockchainService:
    """Test get_blockchain_service dependency."""

    def test_get_blockchain_service_returns_service(self):
        """Test get_blockchain_service returns BlockchainService instance."""
        from routers.dependencies import get_blockchain_service
        from services.blockchain_service import BlockchainService

        mock_chain = Mock()
        mock_chain.config = {
            "name": "test",
            "multichain-url": "http://localhost:8570",
            "multichain-headers": {"Content-Type": "application/json"},
        }

        service = get_blockchain_service(mock_chain)
        assert isinstance(service, BlockchainService)


class TestGetPaginationService:
    """Test get_pagination_service dependency."""

    def test_get_pagination_service_returns_service(self):
        """Test get_pagination_service returns PaginationService instance."""
        from routers.dependencies import get_pagination_service
        from services.pagination_service import PaginationService

        service = get_pagination_service()
        assert isinstance(service, PaginationService)


class TestPaginationParams:
    """Test PaginationParams dependency class."""

    def test_pagination_params_defaults(self):
        """Test PaginationParams with explicit default values."""
        from routers.dependencies import PaginationParams

        # When instantiated directly (not through DI), we need to pass values
        params = PaginationParams(start=0, count=20)
        assert params.start == 0
        assert params.count == 20

    def test_pagination_params_custom(self):
        """Test PaginationParams with custom values."""
        from routers.dependencies import PaginationParams

        params = PaginationParams(start=50, count=100)
        assert params.start == 50
        assert params.count == 100

    def test_pagination_params_to_dict(self):
        """Test PaginationParams.to_dict method."""
        from routers.dependencies import PaginationParams

        params = PaginationParams(start=10, count=25)
        result = params.to_dict()

        assert result == {"start": 10, "count": 25}


class TestCommonContext:
    """Test CommonContext dependency class."""

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        request = Mock()
        request.app = Mock()
        request.app.state = Mock()
        request.app.state.templates = Mock()
        return request

    @pytest.fixture
    def mock_chain(self):
        """Create mock chain."""
        chain = Mock()
        chain.config = {
            "name": "test-chain",
            "path-name": "test-chain",
            "display-name": "Test Chain",
        }
        return chain

    def test_common_context_initialization(self, mock_request, mock_chain):
        """Test CommonContext initialization."""
        from routers.dependencies import CommonContext

        app_state.get_state().settings = {"main": {"base": "/api/"}}

        context = CommonContext(mock_request, mock_chain)

        assert context.request is mock_request
        assert context.chain is mock_chain
        assert context.base_url == "/api/"
        assert context.chain_name == "Test Chain"
        assert context.chain_path == "test-chain"

    def test_common_context_build_context(self, mock_request, mock_chain):
        """Test CommonContext.build_context method."""
        from routers.dependencies import CommonContext

        app_state.get_state().settings = {"main": {"base": "/"}}

        context = CommonContext(mock_request, mock_chain)
        result = context.build_context(title="Test Page", extra="value")

        assert result["request"] is mock_request
        assert result["base_url"] == "/"
        assert result["chain_name"] == "Test Chain"
        assert result["chain_path"] == "test-chain"
        assert result["title"] == "Test Page"
        assert result["extra"] == "value"

    def test_common_context_fallback_chain_name(self, mock_request):
        """Test CommonContext falls back to 'name' if 'display-name' missing."""
        from routers.dependencies import CommonContext

        chain = Mock()
        chain.config = {
            "name": "fallback-name",
            "path-name": "fallback-path",
        }

        app_state.get_state().settings = {"main": {"base": "/"}}

        context = CommonContext(mock_request, chain)
        assert context.chain_name == "fallback-name"


class TestGetQueryParams:
    """Test get_query_params dependency."""

    def test_get_query_params_with_params(self):
        """Test get_query_params extracts query parameters."""
        from routers.dependencies import get_query_params

        mock_request = Mock()
        mock_request.query_params = {"page": "2", "count": "50"}

        result = get_query_params(mock_request)
        assert result == {"page": "2", "count": "50"}

    def test_get_query_params_empty(self):
        """Test get_query_params with no parameters."""
        from routers.dependencies import get_query_params

        mock_request = Mock()
        mock_request.query_params = {}

        result = get_query_params(mock_request)
        assert result == {}


class TestGetOptionalQueryParams:
    """Test get_optional_query_params dependency."""

    def test_get_optional_query_params_with_params(self):
        """Test get_optional_query_params extracts query parameters."""
        from routers.dependencies import get_optional_query_params

        mock_request = Mock()
        mock_request.query_params = {"key": "value"}

        result = get_optional_query_params(mock_request)
        assert result == {"key": "value"}

    def test_get_optional_query_params_empty(self):
        """Test get_optional_query_params with empty params."""
        from routers.dependencies import get_optional_query_params

        mock_request = Mock()
        mock_request.query_params = {}

        result = get_optional_query_params(mock_request)
        assert result == {}

    def test_get_optional_query_params_falsy(self):
        """Test get_optional_query_params with falsy query_params."""
        from routers.dependencies import get_optional_query_params

        mock_request = Mock()
        mock_request.query_params = None

        result = get_optional_query_params(mock_request)
        assert result == {}


class TestGetTemplates:
    """Test get_templates dependency."""

    def test_get_templates_returns_templates(self):
        """Test get_templates returns templates from app state."""
        from routers.dependencies import get_templates

        mock_templates = Mock()
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state.templates = mock_templates

        result = get_templates(mock_request)
        assert result is mock_templates
