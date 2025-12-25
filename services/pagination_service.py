"""
Pagination service - Pagination logic for lists.

Provides utilities for paginating results with proper URL generation.
"""

from dataclasses import dataclass, asdict
from typing import Any, List, Literal, Optional, Union, overload
from urllib.parse import urlencode


@dataclass
class PaginationInfo:
    """Pagination information for templates."""

    current_page: int
    total_items: int
    items_per_page: int
    total_pages: int
    has_previous: bool
    has_next: bool
    previous_page: Optional[int]
    next_page: Optional[int]
    start_item: int
    end_item: int
    base_url: str

    @property
    def start(self) -> int:
        """Get 0-based start index for slicing (legacy compatibility)."""
        return (self.current_page - 1) * self.items_per_page

    @property
    def count(self) -> int:
        """Get items per page (legacy compatibility)."""
        return self.items_per_page

    def __getitem__(self, key: str) -> Any:
        """
        Dict-like access for backward compatibility and template ease.
        """
        # Legacy keys
        if key == "start":
            return self.start
        elif key == "count":
            return self.count
        elif key == "total":
            return self.total_items

        # New keys mapped to attributes
        # We try to match the keys expected by the routers
        if key == "page":
            return self.current_page
        if key == "page_count":
            return self.total_pages
        if key == "has_next":
            return self.has_next
        if key == "has_prev":
            return self.has_previous
        if key == "next_page":
            return self.next_page
        if key == "prev_page":
            return self.previous_page
        if key == "url_base":
            return self.base_url

        # Fallback to attribute access if it exists
        if hasattr(self, key):
            return getattr(self, key)

        raise KeyError(f"Unknown key: {key}")

    def get_page_url(self, page: int, **extra_params: Any) -> str:
        """
        Generate URL for a specific page.

        Args:
            page: Page number (1-based)
            **extra_params: Additional query parameters

        Returns:
            URL string with query parameters
        """
        params = {"page": page, **extra_params}
        query_string = urlencode({k: v for k, v in params.items() if v is not None})
        return f"{self.base_url}?{query_string}" if query_string else self.base_url


class PaginationService:
    """Service for handling pagination logic."""

    @staticmethod
    def paginate(
        items: List[Any],
        page: int = 1,
        items_per_page: int = 20,
        base_url: str = "",
    ) -> tuple[List[Any], PaginationInfo]:
        """
        Paginate a list of items.

        Args:
            items: List of items to paginate
            page: Current page number (1-based)
            items_per_page: Number of items per page
            base_url: Base URL for pagination links

        Returns:
            Tuple of (paginated_items, pagination_info)
        """
        total_items = len(items)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        total_pages = max(1, total_pages)  # At least 1 page

        # Clamp page to valid range
        page = max(1, min(page, total_pages))

        # Calculate slice indices
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        # Slice items
        paginated_items = items[start_idx:end_idx]

        # Calculate navigation
        has_previous = page > 1
        has_next = page < total_pages
        previous_page = page - 1 if has_previous else None
        next_page = page + 1 if has_next else None

        # Calculate display info
        start_item = start_idx + 1 if total_items > 0 else 0
        end_item = min(end_idx, total_items)

        pagination_info = PaginationInfo(
            current_page=page,
            total_items=total_items,
            items_per_page=items_per_page,
            total_pages=total_pages,
            has_previous=has_previous,
            has_next=has_next,
            previous_page=previous_page,
            next_page=next_page,
            start_item=start_item,
            end_item=end_item,
            base_url=base_url,
        )

        return paginated_items, pagination_info

    @staticmethod
    def get_page_range(current_page: int, total_pages: int, max_pages: int = 5) -> List[int]:
        """
        Get a range of page numbers to display.

        Args:
            current_page: Current page number
            total_pages: Total number of pages
            max_pages: Maximum number of page links to show

        Returns:
            List of page numbers to display
        """
        if total_pages <= max_pages:
            return list(range(1, total_pages + 1))

        # Calculate range centered on current page
        half_max = max_pages // 2
        start = max(1, current_page - half_max)
        end = min(total_pages, start + max_pages - 1)

        # Adjust if at the end
        if end == total_pages:
            start = max(1, end - max_pages + 1)

        return list(range(start, end + 1))

    def get_pagination_info(
        self,
        total_count: Optional[int] = None,
        page: int = 1,
        items_per_page: int = 20,
        base_url: str = "",
        # Legacy parameter names for backward compatibility
        total: Optional[int] = None,
        start: Optional[int] = None,
        count: Optional[int] = None,
    ) -> PaginationInfo:
        """
        Get pagination information without actual items.

        Supports both new and legacy parameter names for compatibility.

        Args:
            total_count: Total number of items (new style)
            page: Current page number (1-based)
            items_per_page: Number of items per page
            base_url: Base URL for pagination links
            total: Legacy alias for total_count
            start: Legacy start offset (converted to page)
            count: Legacy alias for items_per_page

        Returns:
            PaginationInfo object
        """
        # Handle legacy parameters
        if total is not None:
            total_count = total
        if count is not None:
            items_per_page = count
        if start is not None and items_per_page > 0:
            page = (start // items_per_page) + 1

        if total_count is None:
            total_count = 0

        total_pages = (total_count + items_per_page - 1) // items_per_page
        total_pages = max(1, total_pages)  # At least 1 page

        # Clamp page to valid range
        page = max(1, min(page, total_pages))

        # Calculate navigation
        has_previous = page > 1
        has_next = page < total_pages
        previous_page = page - 1 if has_previous else None
        next_page = page + 1 if has_next else None

        # Calculate display info
        start_idx = (page - 1) * items_per_page
        start_item = start_idx + 1 if total_count > 0 else 0
        end_item = min(start_idx + items_per_page, total_count)

        return PaginationInfo(
            current_page=page,
            total_items=total_count,
            items_per_page=items_per_page,
            total_pages=total_pages,
            has_previous=has_previous,
            has_next=has_next,
            previous_page=previous_page,
            next_page=next_page,
            start_item=start_item,
            end_item=end_item,
            base_url=base_url,
        )
