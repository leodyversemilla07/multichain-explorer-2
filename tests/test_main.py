"""
Tests for main.py - FastAPI application.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

import app_state


class TestCreateApp:
    """Test create_app factory function."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        from main import create_app
        from fastapi import FastAPI

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_create_app_sets_title(self):
        """Test that app has correct title."""
        from main import create_app

        app = create_app()
        assert app.title == "MultiChain Explorer 2"

    def test_create_app_sets_version(self):
        """Test that app has correct version."""
        from main import create_app

        app = create_app()
        assert app.version == app_state.VERSION

    def test_create_app_has_docs_urls(self):
        """Test that app has documentation URLs configured."""
        from main import create_app

        app = create_app()
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"


class TestHealthEndpoint:
    """Test /health endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def test_health_check_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_healthy_status(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_check_returns_correct_version(self, client):
        """Test health endpoint returns correct version."""
        response = client.get("/health")
        data = response.json()

        assert data["version"] == app_state.VERSION


class TestApiInfoEndpoint:
    """Test /api/info endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def test_api_info_returns_200(self, client):
        """Test API info endpoint returns 200."""
        response = client.get("/api/info")
        assert response.status_code == 200

    def test_api_info_returns_correct_data(self, client):
        """Test API info endpoint returns correct data."""
        response = client.get("/api/info")
        data = response.json()

        assert data["name"] == "MultiChain Explorer 2 API"
        assert data["version"] == app_state.VERSION
        assert data["docs"] == "/docs"
        assert data["redoc"] == "/redoc"


class TestOpenAPIEndpoints:
    """Test OpenAPI documentation endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def test_openapi_json_available(self, client):
        """Test OpenAPI JSON is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_docs_endpoint_available(self, client):
        """Test Swagger UI docs are available."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_endpoint_available(self, client):
        """Test ReDoc is available."""
        response = client.get("/redoc")
        assert response.status_code == 200


class TestTemplateFilters:
    """Test custom Jinja2 template filters."""

    def test_format_hash_truncates_long_hash(self):
        """Test format_hash truncates long hashes."""
        from main import _register_template_filters
        from fastapi.templating import Jinja2Templates
        import tempfile
        import os

        # Create temp directory for templates
        with tempfile.TemporaryDirectory() as temp_dir:
            templates = Jinja2Templates(directory=temp_dir)
            _register_template_filters(templates)

            format_hash = templates.env.filters["format_hash"]

            long_hash = "abcdef1234567890abcdef1234567890"
            result = format_hash(long_hash, 16)

            assert len(result) < len(long_hash)
            assert "..." in result

    def test_format_hash_short_value(self):
        """Test format_hash doesn't truncate short values."""
        from main import _register_template_filters
        from fastapi.templating import Jinja2Templates
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            templates = Jinja2Templates(directory=temp_dir)
            _register_template_filters(templates)

            format_hash = templates.env.filters["format_hash"]

            short_hash = "abc123"
            result = format_hash(short_hash, 16)

            assert result == short_hash

    def test_format_hash_empty_value(self):
        """Test format_hash handles empty values."""
        from main import _register_template_filters
        from fastapi.templating import Jinja2Templates
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            templates = Jinja2Templates(directory=temp_dir)
            _register_template_filters(templates)

            format_hash = templates.env.filters["format_hash"]

            assert format_hash("", 16) == ""
            assert format_hash(None, 16) is None

    def test_format_amount_removes_trailing_zeros(self):
        """Test format_amount removes trailing zeros."""
        from main import _register_template_filters
        from fastapi.templating import Jinja2Templates
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            templates = Jinja2Templates(directory=temp_dir)
            _register_template_filters(templates)

            format_amount = templates.env.filters["format_amount"]

            assert format_amount(1.50000000) == "1.5"
            assert format_amount(100.0) == "100"
            assert format_amount(0) == "0"

    def test_format_timestamp_formats_correctly(self):
        """Test format_timestamp formats Unix timestamp."""
        from main import _register_template_filters
        from fastapi.templating import Jinja2Templates
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            templates = Jinja2Templates(directory=temp_dir)
            _register_template_filters(templates)

            format_timestamp = templates.env.filters["format_timestamp"]

            # Unix timestamp for 2023-01-01 00:00:00 UTC
            timestamp = 1672531200
            result = format_timestamp(timestamp)

            assert "-" in result  # Date separator
            assert ":" in result  # Time separator

    def test_format_timestamp_handles_none(self):
        """Test format_timestamp handles None/0 values."""
        from main import _register_template_filters
        from fastapi.templating import Jinja2Templates
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            templates = Jinja2Templates(directory=temp_dir)
            _register_template_filters(templates)

            format_timestamp = templates.env.filters["format_timestamp"]

            assert format_timestamp(0) == "N/A"
            assert format_timestamp(None) == "N/A"


class TestRouterRegistration:
    """Test that all routers are properly registered."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def test_chains_router_registered(self, client):
        """Test chains router is registered."""
        # The root route is handled by chains router
        response = client.get("/")
        # Should return 200 (chains list page)
        assert response.status_code == 200

    def test_openapi_includes_all_tags(self, client):
        """Test OpenAPI schema includes all expected tags."""
        response = client.get("/openapi.json")
        data = response.json()

        # Get all tags from paths
        tags_in_paths = set()
        for path_data in data.get("paths", {}).values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "tags" in method_data:
                    tags_in_paths.update(method_data["tags"])

        # Should have System tag at minimum
        assert "System" in tags_in_paths


class TestStaticFiles:
    """Test static file serving."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def test_static_mount_exists(self):
        """Test static files are mounted if directory exists."""
        from main import create_app, STATIC_DIR

        app = create_app()

        # Check if static route is mounted
        route_names = [route.name for route in app.routes if hasattr(route, "name")]

        if STATIC_DIR.exists():
            assert "static" in route_names


class TestAppState:
    """Test application state management."""

    def test_templates_in_app_state(self):
        """Test templates are stored in app state."""
        from main import create_app

        app = create_app()
        assert hasattr(app.state, "templates")
        assert app.state.templates is not None
