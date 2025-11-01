"""
Tests for service layer.

Tests for BlockchainService, PaginationService, and FormattingService.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from config import ChainConfig
from exceptions import ChainConnectionError, RPCError
from services import BlockchainService, FormattingService, PaginationService


class TestBlockchainService:
    """Tests for BlockchainService."""

    @pytest.fixture
    def chain_config(self):
        """Create test chain configuration."""
        return ChainConfig(
            name="test-chain",
            display_name="Test Chain",
            path_name="test-chain",
            ini_name="test-chain.ini",
            rpc_host="localhost",
            rpc_port=8000,
            rpc_user="testuser",
            rpc_password="testpass",
        )

    @pytest.fixture
    def service(self, chain_config):
        """Create blockchain service instance."""
        return BlockchainService(chain_config)

    def test_service_initialization(self, service, chain_config):
        """Test service initializes correctly."""
        assert service.config == chain_config
        assert service.rpc_url == "http://localhost:8000"
        assert service._request_id == 0

    @patch("services.blockchain_service.urlopen")
    def test_successful_rpc_call(self, mock_urlopen, service):
        """Test successful RPC call."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"blocks": 100}}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = service.call("getinfo")

        assert result == {"blocks": 100}
        assert service._request_id == 1

    @patch("services.blockchain_service.urlopen")
    def test_rpc_call_with_params(self, mock_urlopen, service):
        """Test RPC call with parameters."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"hash": "abc123"}}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = service.call("getblock", ["abc123"])

        assert result == {"hash": "abc123"}

    @patch("services.blockchain_service.urlopen")
    def test_rpc_error_handling(self, mock_urlopen, service):
        """Test RPC error is properly raised."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -5, "message": "Block not found"},
            }
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with pytest.raises(RPCError) as exc_info:
            service.call("getblock", ["invalid"])

        assert "Block not found" in str(exc_info.value)
        assert exc_info.value.method == "getblock"
        assert exc_info.value.error_code == -5

    @patch("services.blockchain_service.urlopen")
    def test_connection_error_handling(self, mock_urlopen, service):
        """Test connection error is properly handled."""
        mock_urlopen.side_effect = URLError("Connection refused")

        with pytest.raises(ChainConnectionError) as exc_info:
            service.call("getinfo")

        assert "Cannot connect to chain" in str(exc_info.value)
        assert exc_info.value.chain_name == "test-chain"

    @patch("services.blockchain_service.urlopen")
    def test_json_decode_error(self, mock_urlopen, service):
        """Test invalid JSON response handling."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"invalid json"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with pytest.raises(RPCError) as exc_info:
            service.call("getinfo")

        assert "Invalid JSON" in str(exc_info.value)

    @patch("services.blockchain_service.urlopen")
    def test_get_info(self, mock_urlopen, service):
        """Test get_info method."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"version": "2.0"}}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = service.get_info()
        assert result == {"version": "2.0"}

    @patch("services.blockchain_service.urlopen")
    def test_get_block(self, mock_urlopen, service):
        """Test get_block method."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"height": 100}}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = service.get_block(100)
        assert result == {"height": 100}

    @patch("services.blockchain_service.urlopen")
    def test_is_healthy_success(self, mock_urlopen, service):
        """Test is_healthy returns True when connection works."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {}}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        assert service.is_healthy() is True

    @patch("services.blockchain_service.urlopen")
    def test_is_healthy_failure(self, mock_urlopen, service):
        """Test is_healthy returns False when connection fails."""
        mock_urlopen.side_effect = URLError("Connection refused")

        assert service.is_healthy() is False


class TestPaginationService:
    """Tests for PaginationService."""

    def test_paginate_basic(self):
        """Test basic pagination."""
        items = list(range(100))
        service = PaginationService()

        paginated, info = service.paginate(items, page=1, items_per_page=10)

        assert len(paginated) == 10
        assert paginated == list(range(10))
        assert info.current_page == 1
        assert info.total_items == 100
        assert info.total_pages == 10
        assert info.has_next is True
        assert info.has_previous is False

    def test_paginate_last_page(self):
        """Test pagination on last page."""
        items = list(range(25))
        service = PaginationService()

        paginated, info = service.paginate(items, page=3, items_per_page=10)

        assert len(paginated) == 5
        assert paginated == list(range(20, 25))
        assert info.current_page == 3
        assert info.has_next is False
        assert info.has_previous is True

    def test_paginate_empty_list(self):
        """Test pagination with empty list."""
        service = PaginationService()

        paginated, info = service.paginate([], page=1, items_per_page=10)

        assert len(paginated) == 0
        assert info.total_items == 0
        assert info.total_pages == 1
        assert info.start_item == 0
        assert info.end_item == 0

    def test_paginate_invalid_page(self):
        """Test pagination clamps invalid page numbers."""
        items = list(range(50))
        service = PaginationService()

        # Page too high
        paginated, info = service.paginate(items, page=100, items_per_page=10)
        assert info.current_page == 5  # Last valid page

        # Page too low
        paginated, info = service.paginate(items, page=0, items_per_page=10)
        assert info.current_page == 1  # First page

    def test_pagination_info_urls(self):
        """Test pagination URL generation."""
        items = list(range(50))
        service = PaginationService()

        _, info = service.paginate(items, page=2, items_per_page=10, base_url="/test")

        assert info.get_page_url(1) == "/test?page=1"
        assert info.get_page_url(3) == "/test?page=3"
        assert info.get_page_url(2, filter="active") == "/test?page=2&filter=active"

    def test_get_page_range_small(self):
        """Test page range with few pages."""
        service = PaginationService()
        pages = service.get_page_range(current_page=1, total_pages=3, max_pages=5)

        assert pages == [1, 2, 3]

    def test_get_page_range_large(self):
        """Test page range with many pages."""
        service = PaginationService()

        # Beginning
        pages = service.get_page_range(current_page=3, total_pages=20, max_pages=5)
        assert len(pages) == 5
        assert 3 in pages

        # Middle
        pages = service.get_page_range(current_page=10, total_pages=20, max_pages=5)
        assert len(pages) == 5
        assert 10 in pages

        # End
        pages = service.get_page_range(current_page=18, total_pages=20, max_pages=5)
        assert len(pages) == 5
        assert pages == [16, 17, 18, 19, 20]


class TestFormattingService:
    """Tests for FormattingService."""

    def test_format_hash(self):
        """Test hash formatting."""
        service = FormattingService()

        full_hash = "abcdef1234567890abcdef1234567890"
        formatted = service.format_hash(full_hash, length=16)

        assert formatted == "abcdef12...34567890"
        assert len(formatted) < len(full_hash)

    def test_format_hash_short(self):
        """Test hash formatting with short hash."""
        service = FormattingService()

        short_hash = "abc123"
        formatted = service.format_hash(short_hash, length=16)

        assert formatted == short_hash

    def test_format_amount(self):
        """Test amount formatting."""
        service = FormattingService()

        assert service.format_amount(1.23456789, decimals=8) == "1.23456789"
        assert service.format_amount(1.0, decimals=8) == "1"
        assert service.format_amount(100, decimals=2) == "100"
        assert service.format_amount(1.5, decimals=2, symbol="BTC") == "1.5 BTC"

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        service = FormattingService()

        timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        formatted = service.format_timestamp(timestamp)

        assert "2021" in formatted

    def test_format_relative_time(self):
        """Test relative time formatting."""
        service = FormattingService()
        now = datetime.now().timestamp()

        assert "seconds ago" in service.format_relative_time(now - 30)
        assert "minutes ago" in service.format_relative_time(now - 300)
        assert "hours ago" in service.format_relative_time(now - 7200)

    def test_format_bytes(self):
        """Test byte size formatting."""
        service = FormattingService()

        assert service.format_bytes(500) == "500 B"
        assert "KiB" in service.format_bytes(1024)  # Binary units
        assert "MiB" in service.format_bytes(1024 * 1024)
        assert "GiB" in service.format_bytes(1024 * 1024 * 1024)

    def test_format_number(self):
        """Test number formatting with separators."""
        service = FormattingService()

        assert service.format_number(1000) == "1,000"
        assert service.format_number(1000000) == "1,000,000"
        assert service.format_number(1234.56) == "1,234.56"

    def test_format_address(self):
        """Test address formatting."""
        service = FormattingService()

        long_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        formatted = service.format_address(long_address, length=20)

        assert len(formatted) < len(long_address)
        assert "..." in formatted

    def test_format_percentage(self):
        """Test percentage formatting."""
        service = FormattingService()

        assert service.format_percentage(75.5) == "75.50%"
        assert service.format_percentage(100, decimals=0) == "100%"

    def test_truncate_string(self):
        """Test string truncation."""
        service = FormattingService()

        long_text = "This is a very long text that needs to be truncated"
        truncated = service.truncate_string(long_text, max_length=20)

        assert len(truncated) <= 20
        assert truncated.endswith("...")

    def test_sanitize_html(self):
        """Test HTML sanitization."""
        service = FormattingService()

        unsafe = '<script>alert("xss")</script>'
        safe = service.sanitize_html(unsafe)

        assert "<script>" not in safe
        assert "&lt;script&gt;" in safe

    def test_calculate_hash(self):
        """Test hash calculation."""
        service = FormattingService()

        data = "test data"
        hash_value = service.calculate_hash(data, algorithm="sha256")

        assert len(hash_value) == 64  # SHA256 produces 64 hex chars
        assert hash_value == service.calculate_hash(data)  # Deterministic

    def test_format_confirmations(self):
        """Test confirmation formatting."""
        service = FormattingService()

        assert service.format_confirmations(0) == "Unconfirmed"
        assert service.format_confirmations(1) == "1 confirmation"
        assert service.format_confirmations(6) == "6 confirmations"
        assert "," in service.format_confirmations(1000)  # Thousand separator
