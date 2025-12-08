# -*- coding: utf-8 -*-

# MultiChain Explorer 2 (c) Coin Sciences Ltd
# All rights reserved under BSD 3-clause license

"""
Base handler class with common functionality for all entity handlers.
"""

import json
from html import escape
from typing import Any, Dict, Optional, Tuple, Union
from urllib import parse

try:
    from template_engine import render_template

    TEMPLATES_AVAILABLE = True
except ImportError:
    TEMPLATES_AVAILABLE = False

try:
    from validators import sanitize_html

    VALIDATORS_AVAILABLE = True
except ImportError:
    VALIDATORS_AVAILABLE = False

    def sanitize_html(text: str) -> str:
        return escape(str(text), quote=True)


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default if empty or invalid."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Navigation symbols
NAV_SYMBOL_FIRST = "&laquo;"
NAV_SYMBOL_PREV = "&lt;"
NAV_SYMBOL_NEXT = "&gt;"
NAV_SYMBOL_LAST = "&raquo;"

DEFAULT_NONAV_COUNT = 5
DEFAULT_PAGE_SHIFT = 3
DEFAULT_COUNTS = [20, 50, 100, 200, 500]


class BaseHandler:
    """
    Base handler class providing common functionality for all entity handlers.

    This class provides:
    - Template rendering with fallback to HTML generation
    - Pagination logic
    - Common HTML generation methods
    - Error handling
    - JSON response generation
    """

    def __init__(
        self,
        chain_name: Optional[str] = None,
        base_url: Optional[str] = None,
        use_new_templates: bool = True,
    ):
        """
        Initialize the base handler.

        Args:
            chain_name: Name of the blockchain (optional, can be set per-request)
            base_url: Base URL for the explorer (optional, can be set per-request)
            use_new_templates: Whether to use Jinja2 templates (default: True)
        """
        self.chain_name = chain_name or ""
        self.base_url = base_url or ""
        self.use_new_templates = use_new_templates and TEMPLATES_AVAILABLE

    def render_template_response(
        self,
        template_name: str,
        context: Dict[str, Any],
        fallback_html: Optional[str] = None,
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template file
            context: Template context dictionary
            fallback_html: HTML to return if template rendering fails

        Returns:
            Rendered HTML string
        """
        if not self.use_new_templates or not TEMPLATES_AVAILABLE:
            return fallback_html or ""

        try:
            # Add common context variables
            context.setdefault("chain_name", self.chain_name)
            context.setdefault("base_url", self.base_url)

            return render_template(template_name, **context)
        except Exception:
            # Graceful fallback on template errors
            return fallback_html or ""

    def error_response(
        self, error_code: int, title: str, message: str, details: Optional[str] = None
    ) -> str:
        """
        Generate an error response page.

        Args:
            error_code: HTTP error code (400, 404, 500, etc.)
            title: Error title
            message: Error message
            details: Optional error details

        Returns:
            Rendered error page HTML
        """
        context = {
            "error_code": error_code,
            "error_title": title,
            "error_message": message,
            "error_details": details,
            "chain_name": self.chain_name,
            "base_url": self.base_url,
        }

        # Try template rendering first
        if self.use_new_templates and TEMPLATES_AVAILABLE:
            try:
                return render_template("error.html", **context)
            except Exception:
                pass

        # Fallback to simple HTML
        details_html = f"<p>{sanitize_html(details)}</p>" if details else ""
        return f"""
        <html>
        <head><title>{error_code} - {sanitize_html(title)}</title></head>
        <body>
            <h1>{error_code} - {sanitize_html(title)}</h1>
            <p>{sanitize_html(message)}</p>
            {details_html}
        </body>
        </html>
        """

    def not_found_response(self, entity_type: str, entity_id: str) -> str:
        """
        Generate a 404 not found response.

        Args:
            entity_type: Type of entity (block, transaction, address, etc.)
            entity_id: ID of the entity that wasn't found

        Returns:
            Rendered 404 page HTML
        """
        return self.error_response(
            404,
            f"{entity_type.title()} Not Found",
            f"The {entity_type} '{entity_id}' could not be found.",
            f"Please check the {entity_type} identifier and try again.",
        )

    def json_response(self, data: Any, indent: int = 2) -> str:
        """
        Generate a JSON response.

        Args:
            data: Data to serialize to JSON
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return json.dumps(data, indent=indent, default=str)

    def create_pagination_context(
        self,
        current_page: int,
        total_items: int,
        items_per_page: int,
        base_path: str,
    ) -> Dict[str, Any]:
        """
        Create pagination context for templates.

        Args:
            current_page: Current page number (1-indexed)
            total_items: Total number of items
            items_per_page: Number of items per page
            base_path: Base URL path for pagination links

        Returns:
            Dictionary with pagination data
        """
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        current_page = max(1, min(current_page, total_pages))

        return {
            "current_page": current_page,
            "total_pages": total_pages,
            "total_items": total_items,
            "items_per_page": items_per_page,
            "has_prev": current_page > 1,
            "has_next": current_page < total_pages,
            "prev_page": current_page - 1 if current_page > 1 else None,
            "next_page": current_page + 1 if current_page < total_pages else None,
            "base_path": base_path,
        }

    @staticmethod
    def build_url(path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Build a URL with query parameters.

        Args:
            path: URL path
            params: Query parameters dictionary

        Returns:
            Complete URL with query string
        """
        if not params:
            return path

        # Filter out None values
        params = {k: v for k, v in params.items() if v is not None}

        if params:
            query_string = parse.urlencode(params)
            return f"{path}?{query_string}"
        return path

    @staticmethod
    def format_hash(hash_value: str, length: int = 16) -> str:
        """
        Format a hash for display (truncate with ellipsis).

        Args:
            hash_value: Full hash value
            length: Number of characters to show on each end

        Returns:
            Formatted hash string
        """
        if not hash_value or len(hash_value) <= length * 2:
            return hash_value
        return f"{hash_value[:length]}...{hash_value[-length:]}"

    @staticmethod
    def format_amount(amount: float, decimals: int = 8) -> str:
        """
        Format an amount with appropriate decimal places.

        Args:
            amount: Numeric amount
            decimals: Number of decimal places

        Returns:
            Formatted amount string
        """
        return f"{amount:.{decimals}f}".rstrip("0").rstrip(".")

    # Convenience aliases for common response types
    def not_found(self, message: str) -> Tuple[int, list, bytes]:
        """Return a 404 not found response (convenience method)."""
        html = self.error_response(404, "Not Found", message)
        return (
            404,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def error(self, message: str, code: int = 500) -> Tuple[int, list, bytes]:
        """Return an error response (convenience method)."""
        html = self.error_response(code, "Error", message)
        return (
            code,
            [("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    @staticmethod
    def unpack_pagination(page_info: Any, base_path: str = "") -> Dict[str, Any]:
        """
        Unpack PaginationInfo object into dict for template context.

        Templates expect flat variables like total_pages, current_page, etc.
        This helper unpacks the PaginationInfo dataclass.

        Args:
            page_info: PaginationInfo object from pagination service
            base_path: Base path for pagination links (e.g., '/chain/blocks')

        Returns:
            Dict with unpacked pagination variables for templates
        """
        return {
            "pagination": page_info,  # Keep the object for programmatic access
            "total_pages": page_info.total_pages,
            "page_number": page_info.current_page,
            "total_items": page_info.total_items,
            "items_per_page": page_info.items_per_page,
            "has_previous": page_info.has_previous,
            "has_next": page_info.has_next,
            "previous_page": page_info.previous_page,
            "next_page": page_info.next_page,
            "start_item": page_info.start_item,
            "end_item": page_info.end_item,
            "base_path": base_path or page_info.base_url,
        }
