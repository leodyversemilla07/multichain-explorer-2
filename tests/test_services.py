"""
Tests for service layer.

Tests for BlockchainService, PaginationService, and FormattingService.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock, Mock
from urllib.error import HTTPError, URLError

import httpx
import pytest

from config import ChainConfig
from exceptions import ChainConnectionError, RPCError
from services import BlockchainService, FormattingService, PaginationService
from services.search_service import search_all_entities


@pytest.mark.asyncio
class TestBlockchainService:
    """Tests for BlockchainService (Async)."""

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

    async def test_successful_rpc_call(self, service):
        """Test successful RPC call."""
        mock_response = Mock()
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"blocks": 100}}
        mock_response.status_code = 200
        
        service._client = AsyncMock()
        service._client.post.return_value = mock_response

        result = await service.call("getinfo")

        assert result == {"blocks": 100}
        assert service._request_id == 1

    async def test_rpc_error_handling(self, service):
        """Test RPC error is properly raised."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0", 
            "id": 1, 
            "error": {"code": -5, "message": "Block not found"}
        }
        
        service._client = AsyncMock()
        service._client.post.return_value = mock_response

        with pytest.raises(RPCError) as exc_info:
            await service.call("getblock", ["invalid"])

        assert "Block not found" in str(exc_info.value)

    async def test_call_retries_transient_transport_error(self, service):
        """Test transient transport failures are retried before succeeding."""
        mock_response = Mock()
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
        mock_response.status_code = 200
        connect_error = httpx.ConnectError(
            "temporary network issue",
            request=httpx.Request("POST", service.rpc_url),
        )

        service._client = AsyncMock()
        service._client.post.side_effect = [connect_error, mock_response]

        with patch("services.blockchain_service.asyncio.sleep", new_callable=AsyncMock):
            result = await service.call("getinfo")

        assert result == {"ok": True}
        assert service._client.post.await_count == 2

    async def test_call_raises_after_exhausting_retries(self, service):
        """Test transport errors become ChainConnectionError after retries."""
        connect_error = httpx.ConnectError(
            "still failing",
            request=httpx.Request("POST", service.rpc_url),
        )
        service._client = AsyncMock()
        service._client.post.side_effect = connect_error

        with patch("services.blockchain_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ChainConnectionError):
                await service.call("getinfo")
        assert service._client.post.await_count == service._max_retries + 1

    async def test_get_address_summary(self, service):
        """Test get_address_summary aggregation."""
        # Mock internal methods on the service instance directly
        service.get_address_info = AsyncMock(return_value={"image": "info"})
        service.get_address_permissions = AsyncMock(return_value=["perm"])
        service.call = AsyncMock(return_value={"isvalid": True}) # for fallback

        # Test
        result = await service.get_address_summary("addr")
        
        assert result["image"] == "info"
        assert result["permissions"] == ["perm"]
        
        # Verify calls
        service.get_address_info.assert_called_with("addr")
        service.get_address_permissions.assert_called_with("addr")

    async def test_get_address_info_raises_connection_errors(self, service):
        """Test address info does not hide balance fetch connection failures."""
        service.get_address_balances = AsyncMock(side_effect=ChainConnectionError("test-chain"))

        with pytest.raises(ChainConnectionError):
            await service.get_address_info("addr")

    async def test_get_address_permissions_raises_rpc_errors(self, service):
        """Test address permissions do not hide RPC failures."""
        service.call = AsyncMock(side_effect=RPCError("listpermissions", "boom"))

        with pytest.raises(RPCError):
            await service.get_address_permissions("addr")

    async def test_get_address_summary_returns_empty_for_invalid_addresses(self, service):
        """Test invalid addresses fall back to an empty summary."""
        service.get_address_info = AsyncMock(
            side_effect=RPCError("getaddressbalances", "not found", error_code=-5)
        )
        service.get_address_permissions = AsyncMock(return_value=[])
        service.call = AsyncMock(return_value={"isvalid": False})

        result = await service.get_address_summary("addr")

        assert result == {"permissions": []}

    async def test_get_address_summary_raises_permission_failures(self, service):
        """Test address summary no longer hides permission backend failures."""
        service.get_address_info = AsyncMock(return_value={"address": "addr", "balances": []})
        service.get_address_permissions = AsyncMock(side_effect=ChainConnectionError("test-chain"))

        with pytest.raises(ChainConnectionError):
            await service.get_address_summary("addr")

    async def test_get_block_by_height_returns_none_for_not_found_rpc(self, service):
        """Test missing blocks return None without hiding other backend failures."""
        service.get_block_hash = AsyncMock(
            side_effect=RPCError("getblockhash", "Block not found", error_code=-5)
        )

        result = await service.get_block_by_height(999)

        assert result is None

    async def test_get_block_by_height_raises_connection_errors(self, service):
        """Test connection failures are not swallowed by get_block_by_height."""
        service.get_block_hash = AsyncMock(side_effect=ChainConnectionError("test-chain"))

        with pytest.raises(ChainConnectionError):
            await service.get_block_by_height(999)

    async def test_get_block_by_hash_raises_non_not_found_rpc_errors(self, service):
        """Test non-not-found RPC failures still propagate for block lookups."""
        service.get_block = AsyncMock(side_effect=RPCError("getblock", "boom", error_code=-1))

        with pytest.raises(RPCError):
            await service.get_block_by_hash("a" * 64)

    async def test_get_asset_returns_none_for_missing_assets(self, service):
        """Test missing assets resolve to None without swallowing other failures."""
        service.call = AsyncMock(
            side_effect=RPCError("listassets", "Asset not found", error_code=-5)
        )

        result = await service.get_asset("missing-asset")

        assert result is None

    async def test_get_stream_raises_connection_errors(self, service):
        """Test stream lookups preserve backend connection failures."""
        service.call = AsyncMock(side_effect=ChainConnectionError("test-chain"))

        with pytest.raises(ChainConnectionError):
            await service.get_stream("stream1")

    async def test_count_rpc_list_results_uses_shared_bounded_fetch(self, service):
        """Test shared RPC count fallback uses the expected bounded parameters."""
        service.call = AsyncMock(return_value=[{"txid": "tx1"}, {"txid": "tx2"}])

        result = await service.count_rpc_list_results("listassettransactions", "asset1")

        assert result == 2
        service.call.assert_awaited_with(
            "listassettransactions",
            ["asset1", False, 100000, 0],
        )


@pytest.mark.asyncio
class TestSearchService:
    """Tests for the shared search service."""

    @pytest.fixture
    def chain(self):
        chain = Mock()
        chain.path_name = "test-chain"
        chain.config = {"path-name": "test-chain"}
        return chain

    @pytest.fixture
    def search_service_mock(self):
        service = Mock()
        service.get_block_by_height = AsyncMock(return_value=None)
        service.get_block_by_hash = AsyncMock(return_value=None)
        service.get_transaction = AsyncMock(return_value=None)
        service.get_address_balances = AsyncMock(return_value=[])
        service.call = AsyncMock(return_value=[])
        return service

    async def test_search_all_entities_ignores_missing_transactions(self, chain, search_service_mock):
        """Test not-found transaction lookups are treated as empty search results."""
        txid = "a" * 64
        search_service_mock.get_transaction = AsyncMock(
            side_effect=RPCError("getrawtransaction", "not found", error_code=-5)
        )

        result = await search_all_entities(chain, search_service_mock, txid, include_stream_keys=False)

        assert result == {"results": [], "total": 0}

    async def test_search_all_entities_raises_backend_failures(self, chain, search_service_mock):
        """Test backend failures are no longer silently swallowed by search."""
        search_service_mock.call = AsyncMock(side_effect=ChainConnectionError("test-chain"))

        with pytest.raises(ChainConnectionError):
            await search_all_entities(chain, search_service_mock, "asset1", include_stream_keys=False)


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

    def test_build_context_includes_component_fields(self):
        """Test template pagination context builder."""
        service = PaginationService()
        page_info = service.get_pagination_info(total=42, page=2, items_per_page=10)

        context = service.build_context(
            page_info,
            "/test/path",
            include_component_fields=True,
        )

        assert context["page"] == 2
        assert context["page_count"] == 5
        assert context["url_base"] == "/test/path"
        assert context["total"] == 42
        assert context["total_pages"] == 5
        assert context["page_number"] == 2
        assert context["base_path"] == "/test/path"

    def test_pagination_info_exposes_legacy_accessors(self):
        """Test PaginationInfo still supports the legacy template fields."""
        service = PaginationService()
        page_info = service.get_pagination_info(total=42, page=2, items_per_page=10)

        assert page_info.total == 42
        assert page_info.end == 20
        assert page_info.has_prev is True
        assert page_info.prev_start == 0
        assert page_info.next_start == 20


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
