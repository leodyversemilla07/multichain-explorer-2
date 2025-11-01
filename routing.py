"""
Modern routing system for MultiChain Explorer.

Provides a decorator-based routing system with:
- Type-safe parameter conversion
- Middleware support
- Automatic route registration
- URL generation helpers
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from urllib.parse import urlencode

from exceptions import InvalidParameterError


@dataclass
class Route:
    """Represents a single route in the application."""

    pattern: str
    handler: Callable
    methods: List[str]
    name: Optional[str] = None
    param_types: Optional[Dict[str, Type]] = None
    requires_chain: bool = True

    def __post_init__(self):
        """Compile the pattern into a regex."""
        # Convert route pattern to regex
        # e.g., "/block/<height>" -> r"/block/(?P<height>[^/]+)"
        pattern = self.pattern
        self.param_names = []

        # Find all parameter placeholders <param_name>
        param_regex = r"<(\w+)(?::([^>]+))?>"

        def replace_param(match):
            param_name = match.group(1)
            param_type = match.group(2) or "str"
            self.param_names.append(param_name)

            # Convert type to regex pattern
            if param_type in ("int", "height", "number"):
                return r"(?P<" + param_name + r">\d+)"
            elif param_type == "hash":
                return r"(?P<" + param_name + r">[a-fA-F0-9]+)"
            elif param_type == "address":
                return r"(?P<" + param_name + r">[a-zA-Z0-9]+)"
            elif param_type == "name":
                # Allow alphanumeric, underscore, dash, and dot (for stream names like "procurement.documents")
                return r"(?P<" + param_name + r">[a-zA-Z0-9_.\-]+)"
            else:  # str or any other
                return r"(?P<" + param_name + r">[^/]+)"

        pattern = re.sub(param_regex, replace_param, pattern)

        # Ensure pattern matches from start to end
        if not pattern.startswith("^"):
            pattern = "^" + pattern
        if not pattern.endswith("$"):
            pattern = pattern + "$"

        self.regex = re.compile(pattern)

    def match(self, path: str) -> Optional[Dict[str, str]]:
        """
        Check if path matches this route.

        Args:
            path: URL path to match

        Returns:
            Dictionary of matched parameters or None if no match
        """
        match = self.regex.match(path)
        if match:
            return match.groupdict()
        return None

    def convert_params(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert string parameters to their typed values.

        Args:
            params: Raw string parameters from URL

        Returns:
            Dictionary with typed parameter values

        Raises:
            InvalidParameterError: If parameter conversion fails
        """
        if not self.param_types:
            return params

        converted = {}
        for name, value in params.items():
            target_type = self.param_types.get(name, str)

            try:
                if target_type == int:
                    converted[name] = int(value)
                elif target_type == float:
                    converted[name] = float(value)
                elif target_type == bool:
                    converted[name] = value.lower() in ("true", "1", "yes")
                else:
                    converted[name] = value
            except (ValueError, AttributeError) as e:
                raise InvalidParameterError(
                    parameter=name,
                    value=value,
                    reason=f"Cannot convert to {target_type.__name__}: {e}",
                )

        return converted


class Router:
    """Central router that manages all application routes."""

    def __init__(self):
        self.routes: List[Route] = []
        self.named_routes: Dict[str, Route] = {}

    def add_route(
        self,
        pattern: str,
        handler: Callable,
        methods: Optional[List[str]] = None,
        name: Optional[str] = None,
        param_types: Optional[Dict[str, Type]] = None,
        requires_chain: bool = True,
    ):
        """
        Add a route to the router.

        Args:
            pattern: URL pattern (e.g., "/block/<height:int>")
            handler: Handler function
            methods: HTTP methods (default: ["GET"])
            name: Optional route name for URL generation
            param_types: Parameter type conversion map
            requires_chain: Whether route requires chain context
        """
        if methods is None:
            methods = ["GET"]

        route = Route(
            pattern=pattern,
            handler=handler,
            methods=methods,
            name=name,
            param_types=param_types,
            requires_chain=requires_chain,
        )

        self.routes.append(route)

        if name:
            self.named_routes[name] = route

    def route(
        self,
        pattern: str,
        methods: Optional[List[str]] = None,
        name: Optional[str] = None,
        param_types: Optional[Dict[str, Type]] = None,
        requires_chain: bool = True,
    ):
        """
        Decorator for registering routes.

        Usage:
            @router.route("/block/<height:int>", name="block_detail")
            def handle_block(chain, height):
                pass
        """

        def decorator(handler: Callable) -> Callable:
            self.add_route(
                pattern=pattern,
                handler=handler,
                methods=methods,
                name=name,
                param_types=param_types,
                requires_chain=requires_chain,
            )
            return handler

        return decorator

    def match(self, path: str, method: str = "GET") -> Optional[Tuple[Route, Dict[str, Any]]]:
        """
        Find matching route for a path.

        Args:
            path: URL path
            method: HTTP method

        Returns:
            Tuple of (route, converted_params) or None if no match
        """
        for route in self.routes:
            if method not in route.methods:
                continue

            params = route.match(path)
            if params is not None:
                converted_params = route.convert_params(params)
                return route, converted_params

        return None

    def url_for(self, name: str, **params) -> str:
        """
        Generate URL for a named route.

        Args:
            name: Route name
            **params: URL parameters

        Returns:
            Generated URL string

        Raises:
            ValueError: If route name not found
        """
        if name not in self.named_routes:
            raise ValueError(f"Route '{name}' not found")

        route = self.named_routes[name]
        url = route.pattern

        # Replace parameter placeholders
        for param_name in route.param_names:
            if param_name not in params:
                raise ValueError(f"Missing parameter '{param_name}' for route '{name}'")

            value = params[param_name]
            # Replace <param_name> or <param_name:type> with value
            url = re.sub(r"<" + param_name + r"(?::[^>]+)?>", str(value), url)

        # Remove regex anchors if present
        url = url.replace("^", "").replace("$", "")

        return url

    def get_routes(self) -> List[Route]:
        """Get all registered routes."""
        return self.routes.copy()

    def get_sitemap(self) -> List[Dict[str, str]]:
        """
        Generate sitemap data.

        Returns:
            List of route information dictionaries
        """
        sitemap = []
        for route in self.routes:
            sitemap.append(
                {
                    "pattern": route.pattern,
                    "name": route.name or "",
                    "methods": ", ".join(route.methods),
                    "requires_chain": route.requires_chain,
                    "handler": route.handler.__name__
                    if hasattr(route.handler, "__name__")
                    else str(route.handler),
                }
            )
        return sitemap


# Global router instance
router = Router()


# Convenience decorators for common HTTP methods
def get(pattern: str, **kwargs):
    """Decorator for GET routes."""
    return router.route(pattern, methods=["GET"], **kwargs)


def post(pattern: str, **kwargs):
    """Decorator for POST routes."""
    return router.route(pattern, methods=["POST"], **kwargs)


def route(pattern: str, **kwargs):
    """Decorator for routes (defaults to GET)."""
    return router.route(pattern, **kwargs)
