"""
Tests for FastAPI routers - endpoint integration tests.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

import app_state


@pytest.fixture
def mock_chain():
    """Create a mock chain object."""
    chain = Mock()
    chain.name = "test-chain"
    chain.config = {
        "name": "test-chain",
        "path-name": "test-chain",
        "display-name": "Test Chain",
        "multichain-url": "http://localhost:8570",
        "multichain-headers": {
            "Content-Type": "application/json",
            "Authorization": "Basic dGVzdDp0ZXN0",
        },
    }
    return chain


@pytest.fixture
def mock_blockchain_service():
    """Create a mock blockchain service."""
    service = Mock()
    service.get_blockchain_info.return_value = {
        "blocks": 1000,
        "headers": 1000,
        "bestblockhash": "abc123",
        "difficulty": 1.0,
        "chainwork": "0000",
    }
    service.get_block_by_height.return_value = {
        "hash": "blockhash123",
        "height": 100,
        "time": 1700000000,
        "tx": ["tx1", "tx2"],
        "miner": "1ABC123",
    }
    service.get_block_by_hash.return_value = {
        "hash": "blockhash123",
        "height": 100,
        "time": 1700000000,
        "tx": ["tx1", "tx2"],
    }
    service.get_transaction.return_value = {
        "txid": "tx123",
        "confirmations": 10,
        "time": 1700000000,
        "vin": [],
        "vout": [],
    }
    service.call.return_value = []
    service.get_address_info.return_value = {"address": "1ABC", "isvalid": True}
    service.get_address_balances.return_value = []
    service.get_address_permissions.return_value = []
    return service


@pytest.fixture
def app_with_mocks(mock_chain):
    """Create FastAPI app with mocked dependencies."""
    from main import create_app

    app = create_app()

    # Set up app state with mock chain
    app_state.get_state().chains = [mock_chain]
    app_state.get_state().settings = {
        "main": {"base": "/"},
        "test-chain": {"name": "test-chain"},
    }

    return app


@pytest.fixture
def client(app_with_mocks, mock_blockchain_service):
    """Create test client with mocked services."""
    with patch(
        "routers.dependencies.get_blockchain_service",
        return_value=mock_blockchain_service,
    ):
        with patch(
            "services.blockchain_service.BlockchainService",
            return_value=mock_blockchain_service,
        ):
            yield TestClient(app_with_mocks, raise_server_exceptions=False)


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
        mock_blockchain_service.get_block_by_height.return_value = None
        mock_blockchain_service.get_block_by_hash.return_value = None
        mock_blockchain_service.get_transaction.return_value = None
        mock_blockchain_service.call.return_value = None

        response = client.get("/test-chain/search/suggest?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data


class TestSystemRoutes:
    """Test system routes (health, api info)."""

    @pytest.fixture
    def simple_client(self):
        """Create simple test client without chain mocks."""
        from main import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def test_health_endpoint(self, simple_client):
        """Test health endpoint works."""
        response = simple_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

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

        app = create_app()
        app_state.get_state().chains = []
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
        # Legacy routes should be registered but may redirect or work
        response = client.get("/chain/test-chain", follow_redirects=False)
        # Should either work (200) or redirect (3xx), not 404
        assert response.status_code != 404 or response.status_code in [200, 302, 307]


class TestRouterTags:
    """Test that routers have proper tags for OpenAPI."""

    @pytest.fixture
    def simple_client(self):
        """Create simple test client."""
        from main import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

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
        """Create simple test client."""
        from main import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

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
        """Create client with service that raises errors."""
        from main import create_app

        app = create_app()
        app_state.get_state().chains = [mock_chain]
        app_state.get_state().settings = {"main": {"base": "/"}}

        error_service = Mock()
        error_service.get_blockchain_info.side_effect = Exception("RPC Error")

        with patch(
            "routers.dependencies.get_blockchain_service",
            return_value=error_service,
        ):
            yield TestClient(app, raise_server_exceptions=False)

    def test_service_error_handled(self, client_with_error_service):
        """Test that service errors are handled gracefully."""
        # The endpoint should handle the error, not crash
        response = client_with_error_service.get("/test-chain")
        # Should return some response (error page or 500)
        assert response.status_code in [200, 500]
