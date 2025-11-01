"""
Tests for the routing system.
"""

import pytest

from exceptions import InvalidParameterError
from routing import Route, Router, get, post, route, router


class TestRoute:
    """Test Route class."""

    def test_simple_route_pattern(self):
        """Test simple route without parameters."""
        r = Route(pattern="/chains", handler=lambda: None, methods=["GET"])

        assert r.match("/chains") == {}
        assert r.match("/chain") is None
        assert r.match("/chains/") is None

    def test_route_with_string_param(self):
        """Test route with string parameter."""
        r = Route(pattern="/chain/<name>", handler=lambda name: None, methods=["GET"])

        params = r.match("/chain/testchain")
        assert params == {"name": "testchain"}

        assert r.match("/chain") is None
        assert r.match("/chain/test/extra") is None

    def test_route_with_int_param(self):
        """Test route with integer parameter."""
        r = Route(
            pattern="/block/<height:int>",
            handler=lambda height: None,
            methods=["GET"],
            param_types={"height": int},
        )

        params = r.match("/block/12345")
        assert params == {"height": "12345"}

        # Conversion happens in convert_params
        converted = r.convert_params(params)
        assert converted == {"height": 12345}
        assert isinstance(converted["height"], int)

    def test_route_with_hash_param(self):
        """Test route with hash parameter."""
        r = Route(pattern="/tx/<txid:hash>", handler=lambda txid: None, methods=["GET"])

        params = r.match("/tx/abc123def456")
        assert params == {"txid": "abc123def456"}

        params = r.match("/tx/ABCDEF123456")
        assert params == {"txid": "ABCDEF123456"}

    def test_route_with_multiple_params(self):
        """Test route with multiple parameters."""
        r = Route(
            pattern="/chain/<chain>/block/<height:int>",
            handler=lambda chain, height: None,
            methods=["GET"],
            param_types={"height": int},
        )

        params = r.match("/chain/mychain/block/100")
        assert params == {"chain": "mychain", "height": "100"}

        converted = r.convert_params(params)
        assert converted == {"chain": "mychain", "height": 100}

    def test_route_param_conversion_error(self):
        """Test parameter conversion error handling."""
        r = Route(
            pattern="/block/<height>",  # Use generic param, not typed in pattern
            handler=lambda height: None,
            methods=["GET"],
            param_types={"height": int},
        )

        # Match will succeed with string pattern
        params = r.match("/block/invalid")
        assert params == {"height": "invalid"}

        # But conversion should fail
        with pytest.raises(InvalidParameterError) as exc_info:
            r.convert_params(params)

        assert "height" in str(exc_info.value)

    def test_route_with_name_param(self):
        """Test route with name parameter (alphanumeric + dash/underscore)."""
        r = Route(pattern="/asset/<name:name>", handler=lambda name: None, methods=["GET"])

        assert r.match("/asset/my-asset") is not None
        assert r.match("/asset/my_asset") is not None
        assert r.match("/asset/asset123") is not None


class TestRouter:
    """Test Router class."""

    def test_add_route(self):
        """Test adding routes to router."""
        r = Router()

        def handler():
            pass

        r.add_route("/test", handler, methods=["GET"])

        assert len(r.routes) == 1
        assert r.routes[0].pattern == "/test"

    def test_route_decorator(self):
        """Test route decorator."""
        r = Router()

        @r.route("/chains")
        def handle_chains():
            pass

        assert len(r.routes) == 1
        assert r.routes[0].handler == handle_chains

    def test_match_route(self):
        """Test matching routes."""
        r = Router()

        @r.route("/chains")
        def handle_chains():
            return "chains"

        @r.route("/block/<height:int>", param_types={"height": int})
        def handle_block(height):
            return f"block {height}"

        # Match chains
        route, params = r.match("/chains")
        assert route.handler == handle_chains
        assert params == {}

        # Match block
        route, params = r.match("/block/123")
        assert route.handler == handle_block
        assert params == {"height": 123}

        # No match
        assert r.match("/invalid") is None

    def test_named_routes(self):
        """Test named route registration."""
        r = Router()

        @r.route("/block/<height:int>", name="block_detail")
        def handle_block(height):
            pass

        assert "block_detail" in r.named_routes
        assert r.named_routes["block_detail"].handler == handle_block

    def test_url_for(self):
        """Test URL generation from named routes."""
        r = Router()

        @r.route("/block/<height:int>", name="block_detail")
        def handle_block(height):
            pass

        url = r.url_for("block_detail", height=123)
        assert url == "/block/123"

    def test_url_for_missing_param(self):
        """Test URL generation with missing parameter."""
        r = Router()

        @r.route("/block/<height:int>", name="block_detail")
        def handle_block(height):
            pass

        with pytest.raises(ValueError) as exc_info:
            r.url_for("block_detail")

        assert "Missing parameter 'height'" in str(exc_info.value)

    def test_url_for_unknown_route(self):
        """Test URL generation for unknown route."""
        r = Router()

        with pytest.raises(ValueError) as exc_info:
            r.url_for("unknown_route")

        assert "Route 'unknown_route' not found" in str(exc_info.value)

    def test_method_filtering(self):
        """Test HTTP method filtering."""
        r = Router()

        @r.route("/data", methods=["POST"])
        def handle_post():
            pass

        # Should match POST
        assert r.match("/data", method="POST") is not None

        # Should not match GET
        assert r.match("/data", method="GET") is None

    def test_get_sitemap(self):
        """Test sitemap generation."""
        r = Router()

        @r.route("/chains", name="chains_list")
        def handle_chains():
            pass

        @r.route("/block/<height:int>", name="block_detail")
        def handle_block(height):
            pass

        sitemap = r.get_sitemap()
        assert len(sitemap) == 2
        assert sitemap[0]["name"] == "chains_list"
        assert sitemap[1]["name"] == "block_detail"


class TestConvenienceDecorators:
    """Test convenience decorator functions."""

    def test_get_decorator(self):
        """Test @get decorator."""

        @get("/test")
        def handler():
            pass

        # Should be registered in global router
        route, _ = router.match("/test", method="GET")
        assert route is not None
        assert route.handler == handler

    def test_post_decorator(self):
        """Test @post decorator."""

        @post("/submit")
        def handler():
            pass

        # Should be registered in global router
        route, _ = router.match("/submit", method="POST")
        assert route is not None


class TestParameterTypes:
    """Test different parameter type conversions."""

    def test_int_conversion(self):
        """Test integer parameter conversion."""
        r = Route(
            pattern="/item/<id:int>", handler=lambda: None, methods=["GET"], param_types={"id": int}
        )

        params = r.match("/item/42")
        converted = r.convert_params(params)
        assert converted["id"] == 42
        assert isinstance(converted["id"], int)

    def test_float_conversion(self):
        """Test float parameter conversion."""
        r = Route(
            pattern="/price/<amount>",
            handler=lambda: None,
            methods=["GET"],
            param_types={"amount": float},
        )

        params = {"amount": "123.45"}
        converted = r.convert_params(params)
        assert converted["amount"] == 123.45
        assert isinstance(converted["amount"], float)

    def test_bool_conversion(self):
        """Test boolean parameter conversion."""
        r = Route(
            pattern="/config/<enabled>",
            handler=lambda: None,
            methods=["GET"],
            param_types={"enabled": bool},
        )

        # Test true values
        for val in ["true", "1", "yes", "True", "YES"]:
            converted = r.convert_params({"enabled": val})
            assert converted["enabled"] is True

        # Test false values
        for val in ["false", "0", "no", "False", "NO"]:
            converted = r.convert_params({"enabled": val})
            assert converted["enabled"] is False


class TestRouteRequirements:
    """Test route requirements and metadata."""

    def test_requires_chain_flag(self):
        """Test requires_chain flag."""
        r = Route(pattern="/chains", handler=lambda: None, methods=["GET"], requires_chain=False)

        assert r.requires_chain is False

        r2 = Route(pattern="/block/<height>", handler=lambda: None, methods=["GET"])

        assert r2.requires_chain is True  # Default

    def test_route_metadata(self):
        """Test route stores all metadata correctly."""
        handler = lambda: None
        r = Route(
            pattern="/test/<param>",
            handler=handler,
            methods=["GET", "POST"],
            name="test_route",
            param_types={"param": int},
            requires_chain=False,
        )

        assert r.pattern == "/test/<param>"
        assert r.handler == handler
        assert r.methods == ["GET", "POST"]
        assert r.name == "test_route"
        assert r.param_types == {"param": int}
        assert r.requires_chain is False
