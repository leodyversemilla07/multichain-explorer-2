"""
Tests for routers/dependencies.py - FastAPI dependency injection.
"""

from unittest.mock import Mock

import pytest

from exceptions import ChainNotFoundError


class TestGetState:
    """Test get_state dependency."""

    def test_get_state_returns_app_state_config(self):
        """Test get_state reads ApplicationState from request.app.state.config."""
        from app_state import ApplicationState
        from routers.dependencies import get_state

        state = ApplicationState()
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state.config = state

        assert get_state(mock_request) is state

    def test_get_state_raises_when_missing_config(self):
        """Test get_state raises explicit error when config is missing."""
        from routers.dependencies import get_state

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock(spec=[])  # no config attribute

        with pytest.raises(RuntimeError, match="ApplicationState is not initialized"):
            get_state(mock_request)


class TestGetBaseUrl:
    """Test get_base_url dependency."""

    def test_get_base_url_default(self):
        """Test get_base_url returns default when not set."""
        from routers.dependencies import get_base_url
        from app_state import ApplicationState

        # Mock state
        mock_state = Mock(spec=ApplicationState)
        mock_state.get_setting.return_value = "/"

        result = get_base_url(mock_state)
        assert result == "/"

    def test_get_base_url_custom(self):
        """Test get_base_url returns custom value."""
        from routers.dependencies import get_base_url
        from app_state import ApplicationState

        # Mock state
        mock_state = Mock(spec=ApplicationState)
        mock_state.get_setting.return_value = "/explorer/"

        result = get_base_url(mock_state)
        assert result == "/explorer/"


class TestGetChain:
    """Test get_chain dependency."""

    @pytest.fixture
    def mock_chain_config(self):
        """Create a mock ChainConfig."""
        mock = Mock()
        mock.name = "chain1"
        mock.path_name = "chain1"
        mock.display_name = "Chain One"
        return mock

    def test_get_chain_found(self, mock_chain_config):
        """Test get_chain finds existing chain."""
        from routers.dependencies import get_chain
        from app_state import ApplicationState

        mock_state = Mock(spec=ApplicationState)
        mock_state.get_chain_by_name.return_value = mock_chain_config

        result = get_chain("chain1", state=mock_state)
        assert result.name == "chain1"

    def test_get_chain_not_found(self):
        """Test get_chain raises error for nonexistent chain."""
        from routers.dependencies import get_chain
        from app_state import ApplicationState

        mock_state = Mock(spec=ApplicationState)
        mock_state.get_chain_by_name.return_value = None

        with pytest.raises(ChainNotFoundError) as exc_info:
            get_chain("nonexistent", state=mock_state)

        assert exc_info.value.chain_name == "nonexistent"

    def test_get_chain_empty_chains(self):
        """Test get_chain with no chains configured."""
        from routers.dependencies import get_chain
        from app_state import ApplicationState

        mock_state = Mock(spec=ApplicationState)
        mock_state.get_chain_by_name.return_value = None

        with pytest.raises(ChainNotFoundError):
            get_chain("anychain", state=mock_state)

    def test_get_chain_none_chains(self):
        """Test get_chain with chains set to None."""
        from routers.dependencies import get_chain
        from app_state import ApplicationState

        mock_state = Mock(spec=ApplicationState)
        mock_state.get_chain_by_name.return_value = None

        with pytest.raises(ChainNotFoundError):
            get_chain("anychain", state=mock_state)


class TestGetBlockchainService:
    """Test get_blockchain_service dependency."""

    def test_get_blockchain_service_returns_service(self):
        """Test get_blockchain_service returns BlockchainService instance."""
        from routers.dependencies import get_blockchain_service
        from services.blockchain_service import BlockchainService
        from config import ChainConfig

        mock_chain = Mock(spec=ChainConfig)
        mock_chain.multichain_url = "http://localhost:8570"
        mock_chain.multichain_headers = {"Content-Type": "application/json"}
        mock_chain.name = "test"

        # Provide a mock request with no http_client (falls back to creating its own)
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock(spec=[])  # no http_client attr → falls back

        service = get_blockchain_service(mock_request, mock_chain)
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
        chain.name = "test-chain"
        chain.path_name = "test-chain"
        chain.display_name = "Test Chain"
        return chain

    @pytest.fixture
    def mock_state(self):
        """Create mock state."""
        from app_state import ApplicationState

        state = Mock(spec=ApplicationState)
        state.get_setting.return_value = "/api/"
        return state

    def test_common_context_initialization(self, mock_request, mock_chain, mock_state):
        """Test CommonContext initialization."""
        from routers.dependencies import CommonContext

        context = CommonContext(mock_request, mock_chain, mock_state)

        assert context.request is mock_request
        assert context.chain is mock_chain
        assert context.base_url == "/api"
        assert context.chain_name == "Test Chain"
        assert context.chain_path == "/test-chain"

    def test_common_context_build_context(self, mock_request, mock_chain, mock_state):
        """Test CommonContext.build_context method."""
        from routers.dependencies import CommonContext

        mock_state.get_setting.return_value = "/"

        context = CommonContext(mock_request, mock_chain, mock_state)
        result = context.build_context(title="Test Page", extra="value")

        assert result["request"] is mock_request
        assert result["base_url"] == "/"
        assert result["chain_name"] == "Test Chain"
        assert result["chain_path"] == "/test-chain"
        assert result["title"] == "Test Page"
        assert result["extra"] == "value"

    def test_common_context_fallback_chain_name(self, mock_request, mock_state):
        """Test CommonContext falls back to 'name' if 'display-name' missing."""
        # Note: With type-safe ChainConfig, display_name is always present
        # This test ensures it uses the display_name property
        from routers.dependencies import CommonContext

        chain = Mock()
        chain.name = "fallback-name"
        chain.path_name = "fallback-path"
        chain.display_name = "Fallback Chain"  # ChainConfig always has display_name

        mock_state.get_setting.return_value = "/"

        context = CommonContext(mock_request, chain, state=mock_state)
        assert context.chain_name == "Fallback Chain"


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


class TestQueryParsingHelpers:
    """Test shared query parsing helpers."""

    def test_get_page_count_defaults(self):
        """Test page/count defaults are returned when params are missing."""
        from routers.dependencies import get_page_count

        page, count = get_page_count({})
        assert page == 1
        assert count == 20

    def test_get_page_count_custom_values(self):
        """Test page/count helper parses valid values."""
        from routers.dependencies import get_page_count

        page, count = get_page_count({"page": "3", "count": "50"})
        assert page == 3
        assert count == 50

    def test_get_page_count_legacy_start_fallback(self):
        """Test page/count helper derives the page from legacy start/count links."""
        from routers.dependencies import get_page_count

        page, count = get_page_count({"start": "40", "count": "20"})
        assert page == 3
        assert count == 20

    def test_get_start_count_invalid_values(self):
        """Test start/count helper falls back on invalid values."""
        from routers.dependencies import get_start_count

        start, count = get_start_count({"start": "bad", "count": None})
        assert start == 0
        assert count == 20


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
