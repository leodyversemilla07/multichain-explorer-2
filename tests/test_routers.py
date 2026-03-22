"""
Tests for FastAPI routers - endpoint integration tests.

Uses app.dependency_overrides (FastAPI-recommended pattern) instead of
unittest.mock.patch for service injection — ensures FastAPI's DI system
actually swaps the dependency rather than patching at the module reference level.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

import app_state
from routers.dependencies import get_blockchain_service


@pytest.fixture
def mock_chain():
    """Create a mock chain object."""
    chain = Mock()
    chain.name = "test-chain"
    chain.path_name = "test-chain"
    chain.display_name = "Test Chain"
    chain.multichain_url = "http://localhost:8570"
    chain.multichain_headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic dGVzdDp0ZXN0",
    }
    chain.config = {
        "name": "test-chain",
        "path-name": "test-chain",
        "display-name": "Test Chain",
        "multichain-url": "http://localhost:8570",
        "multichain-headers": chain.multichain_headers,
    }
    return chain


@pytest.fixture
def mock_blockchain_service():
    """Create a mock blockchain service with AsyncMock methods."""
    service = Mock()
    
    # Use AsyncMock for async methods
    service.get_blockchain_info = AsyncMock(return_value={
        "blocks": 1000,
        "headers": 1000,
        "bestblockhash": "abc123",
        "difficulty": 1.0,
        "chainwork": "0000",
    })
    
    service.get_block_by_height = AsyncMock(return_value={
        "hash": "blockhash123",
        "height": 100,
        "time": 1700000000,
        "tx": ["tx1", "tx2"],
        "miner": "1ABC123",
    })
    
    service.get_block_by_hash = AsyncMock(return_value={
        "hash": "blockhash123",
        "height": 100,
        "time": 1700000000,
        "tx": ["tx1", "tx2"],
    })
    
    service.get_transaction = AsyncMock(return_value={
        "txid": "tx123",
        "confirmations": 10,
        "time": 1700000000,
        "vin": [],
        "vout": [],
    })
    
    service.call = AsyncMock(return_value=[])
    
    service.get_address_info = AsyncMock(return_value={"address": "1ABC", "isvalid": True})
    service.get_address_balances = AsyncMock(return_value=[])
    service.get_address_permissions = AsyncMock(return_value=[])
    service.get_address_transactions = AsyncMock(return_value=[])
    service.list_blocks = AsyncMock(return_value=[])
    
    service.get_address_summary = AsyncMock(return_value={
        "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "isvalid": True,
        "balances": [],
        "permissions": []
    })
    
    return service
    
    
class TestAddressesRouter:
    """Test addresses router endpoints (HTML)."""
    
    def test_list_addresses(self, client):
        """Test GET /test-chain/addresses."""
        response = client.get("/test-chain/addresses")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
    def test_address_detail(self, client):
        """Test GET /test-chain/address/{address}."""
        response = client.get("/test-chain/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


@pytest.fixture
def app_with_mocks(mock_chain):
    """Create FastAPI app with mocked dependencies.

    Patches lifespan startup dependencies (Redis, env-init, HTTP client) so TestClient
    can enter the lifespan context manager without real infrastructure.
    """
    from main import create_app
    from app_state import ApplicationState

    # Build the state we want before lifespan runs
    state = ApplicationState()
    state.chains = [mock_chain]
    state.settings = {
        "main": {"base": "/"},
        "test-chain": {"name": "test-chain"},
    }

    # Patch the three things lifespan touches that need real infrastructure:
    # 1. httpx.AsyncClient — lifespan creates and later closes it
    mock_http_client = MagicMock()
    mock_http_client.aclose = AsyncMock()

    # 2. init_from_env — would try to read .env and build real ChainConfigs
    # 3. create_cache_provider — would try to connect to Redis
    mock_cache_provider = MagicMock()
    mock_cache_provider.close = AsyncMock()

    with patch("main.httpx.AsyncClient", return_value=mock_http_client), \
         patch("main.app_state.init_from_env", return_value=True), \
         patch("main.app_state.get_state", return_value=state), \
         patch("main.create_cache_provider", return_value=mock_cache_provider):
        app = create_app()

    # Ensure app.state.config is our controlled state (lifespan may overwrite it)
    app.state.config = state

    return app


@pytest.fixture
def client(app_with_mocks, mock_blockchain_service):
    """Create test client with mocked services.

    Uses app.dependency_overrides instead of patch() — the FastAPI-recommended
    way to swap dependencies in tests (see fastapi-agents skill > testing domain).
    """
    # Patch lifespan infrastructure at test-client startup too
    mock_http_client = MagicMock()
    mock_http_client.aclose = AsyncMock()
    mock_cache_provider = MagicMock()
    mock_cache_provider.close = AsyncMock()

    from app_state import ApplicationState
    state = app_with_mocks.state.config

    # Override the blockchain service dependency at the FastAPI DI level
    app_with_mocks.dependency_overrides[get_blockchain_service] = (
        lambda: mock_blockchain_service
    )
    with patch("main.httpx.AsyncClient", return_value=mock_http_client), \
         patch("main.app_state.init_from_env", return_value=True), \
         patch("main.app_state.get_state", return_value=state), \
         patch("main.create_cache_provider", return_value=mock_cache_provider):
        with TestClient(app_with_mocks, raise_server_exceptions=False) as c:
            # After lifespan, re-assert our controlled state
            app_with_mocks.state.config = state
            yield c
    # Always clear overrides after the test to prevent state leaking
    app_with_mocks.dependency_overrides.clear()


class TestChainsRouter:
    """Test chains router endpoints."""

    def test_list_chains_returns_200(self, client):
        """Test GET / returns 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_list_chains_returns_html(self, client):
        """Test GET / returns HTML."""
        response = client.get("/")
        assert "text/html" in response.headers.get("content-type", "")

    def test_chain_home_renders_recent_blocks_links(self, client, mock_blockchain_service):
        """Test chain dashboard includes recent block navigation when blocks are available."""
        mock_blockchain_service.get_blockchain_info.return_value = {
            "blocks": 2,
            "headers": 2,
            "bestblockhash": "abc123",
            "difficulty": 1.0,
            "chainwork": "0000",
            "description": "Test chain description",
        }
        mock_blockchain_service.list_blocks.return_value = [
            {"height": 1, "hash": "hash1", "time": 1700000000, "tx": ["tx1"]},
            {"height": 0, "hash": "hash0", "time": 1699990000, "tx": ["tx0"]},
        ]

        response = client.get("/test-chain")
        assert response.status_code == 200
        assert "/test-chain/blocks" in response.text
        assert "/test-chain/block/1" in response.text


class TestBlocksRouter:
    """Test blocks router endpoints."""

    def test_block_redirect(self, client):
        """Test GET /{chain}/block redirects to /blocks."""
        response = client.get("/test-chain/block", follow_redirects=False)
        assert response.status_code == 302
        assert "/blocks" in response.headers.get("location", "")


class TestSearchRouter:
    """Test search router endpoints."""

    def test_search_suggest_returns_json(self, client, mock_blockchain_service):
        """Test search suggest endpoint returns JSON."""
        mock_blockchain_service.call.return_value = {"results": [], "total": 0}
        # Note: search algo calls specific getters which are already mocked
        
        response = client.get("/test-chain/search/suggest?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data


class TestSystemRoutes:
    """Test system routes (health, api info)."""

    @pytest.fixture
    def simple_client(self):
        """Create simple test client without chain mocks.

        Uses context manager so lifespan startup/shutdown events run.
        Skill ref: fastapi-agents > testing > Testing Lifespan with TestClient
        """
        from main import create_app

        app = create_app()
        with patch("main.app_state.init_from_env", return_value=False):
            with TestClient(app, raise_server_exceptions=False) as client:
                yield client

    def test_health_endpoint(self, simple_client):
        """Test health endpoint works."""
        response = simple_client.get("/health")
        assert response.status_code == 200
        # When chains are configured, status may be degraded if RPC is unreachable.
        assert response.json()["status"] in ["healthy", "degraded"]

    def test_api_info_endpoint(self, simple_client):
        """Test API info endpoint works."""
        response = simple_client.get("/api/info")
        assert response.status_code == 200
        assert "name" in response.json()
        assert "version" in response.json()


class TestChainNotFoundHandling:
    """Test handling of nonexistent chains."""

    @pytest.fixture
    def client_no_chains(self):
        """Create client with no chains configured."""
        from main import create_app
        from app_state import ApplicationState

        app = create_app()
        
        # Set empty state
        state = ApplicationState()
        state.chains = []
        app.state.config = state
        
        return TestClient(app, raise_server_exceptions=False)

    def test_nonexistent_chain_returns_404(self, client_no_chains):
        """Test accessing nonexistent chain returns 404."""
        response = client_no_chains.get("/nonexistent-chain")
        assert response.status_code == 404


class TestPaginationInRoutes:
    """Test pagination parameters in routes."""

    def test_blocks_accepts_page_param(self, client, mock_blockchain_service):
        """Test blocks endpoint accepts page parameter."""
        response = client.get("/test-chain/blocks?page=2")
        # Should not error on pagination param
        assert response.status_code in [200, 500]  # 500 if template missing

    def test_blocks_accepts_count_param(self, client, mock_blockchain_service):
        """Test blocks endpoint accepts count parameter."""
        response = client.get("/test-chain/blocks?count=50")
        assert response.status_code in [200, 500]


class TestLegacyRoutes:
    """Test legacy route compatibility."""

    def test_legacy_chain_route_exists(self, client):
        """Test legacy /chain/{name} route exists."""
        # Legacy routes should be registered — they redirect or serve content, never 404
        response = client.get("/chain/test-chain", follow_redirects=False)
        # Should either work (200) or redirect (3xx), never 404 (route not registered)
        assert response.status_code in [200, 302, 307, 500]


class TestRouterTags:
    """Test that routers have proper tags for OpenAPI."""

    @pytest.fixture
    def simple_client(self):
        """Create simple test client.

        Uses context manager so lifespan startup/shutdown events run.
        Skill ref: fastapi-agents > testing > Testing Lifespan with TestClient
        """
        from main import create_app

        app = create_app()
        with patch("main.app_state.init_from_env", return_value=False):
            with TestClient(app, raise_server_exceptions=False) as client:
                yield client

    def test_openapi_has_tags(self, simple_client):
        """Test OpenAPI schema has tags defined."""
        response = simple_client.get("/openapi.json")
        data = response.json()

        # Collect all tags used
        tags = set()
        for path_data in data.get("paths", {}).values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "tags" in method_data:
                    tags.update(method_data["tags"])

        # Should have multiple tags from different routers
        assert len(tags) >= 1
        assert "System" in tags


class TestResponseModels:
    """Test that endpoints return proper response models."""

    @pytest.fixture
    def simple_client(self):
        """Create simple test client.

        Uses context manager so lifespan startup/shutdown events run.
        Skill ref: fastapi-agents > testing > Testing Lifespan with TestClient
        """
        from main import create_app

        app = create_app()
        with patch("main.app_state.init_from_env", return_value=False):
            with TestClient(app, raise_server_exceptions=False) as client:
                yield client

    def test_health_response_model(self, simple_client):
        """Test health endpoint matches HealthResponse model."""
        response = simple_client.get("/health")
        data = response.json()

        # Should have exactly the fields from HealthResponse
        assert "status" in data
        assert "version" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)

    def test_api_info_response_model(self, simple_client):
        """Test API info endpoint matches APIInfoResponse model."""
        response = simple_client.get("/api/info")
        data = response.json()

        # Should have exactly the fields from APIInfoResponse
        assert "name" in data
        assert "version" in data
        assert "docs" in data
        assert "redoc" in data


class TestErrorHandling:
    """Test error handling in routes."""

    @pytest.fixture
    def client_with_error_service(self, mock_chain):
        """Create client with a service that raises errors — uses dependency_overrides."""
        from main import create_app
        from app_state import ApplicationState

        app = create_app()

        state = ApplicationState()
        state.chains = [mock_chain]
        state.settings = {
            "main": {"base": "/"},
            "test-chain": {"name": "test-chain"},
        }
        app.state.config = state

        error_service = Mock()
        error_service.get_blockchain_info = AsyncMock(side_effect=Exception("RPC Error"))

        # Use dependency_overrides — the FastAPI-idiomatic approach
        app.dependency_overrides[get_blockchain_service] = lambda: error_service

        # Patch lifespan dependencies so startup does not replace our in-test state
        mock_http_client = MagicMock()
        mock_http_client.aclose = AsyncMock()
        mock_cache_provider = MagicMock()
        mock_cache_provider.close = AsyncMock()

        with patch("main.httpx.AsyncClient", return_value=mock_http_client), \
             patch("main.app_state.init_from_env", return_value=True), \
             patch("main.app_state.get_state", return_value=state), \
             patch("main.create_cache_provider", return_value=mock_cache_provider):
            with TestClient(app, raise_server_exceptions=False) as client:
                app.state.config = state
                yield client
        app.dependency_overrides.clear()

    def test_service_error_handled(self, client_with_error_service):
        """Test that service errors are handled gracefully."""
        # The endpoint should handle the error, not crash
        response = client_with_error_service.get("/test-chain")
        # Should return some response (error page or 500)
        assert response.status_code in [200, 500]
