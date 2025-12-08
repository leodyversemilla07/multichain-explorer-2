"""
MultiChain Explorer 2 - Integration Tests
Tests for critical user paths through the FastAPI application
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app_state
import multichain
from handlers.chain_handler import ChainHandler
from handlers.block_handler import BlockHandler
from handlers.transaction_handler import TransactionHandler
from handlers.asset_handler import AssetHandler
from handlers.stream_handler import StreamHandler


class TestChainListing:
    """Test chain listing functionality"""

    @pytest.mark.integration
    def test_chains_handler_with_connected_chain(self, mock_chain, mock_chain_totals_response):
        """Test chains handler with a connected chain"""
        # Setup
        mock_chain.set_response("getchaintotals", mock_chain_totals_response)
        app_state.get_state().chains = [mock_chain]

        handler = ChainHandler()

        # Execute
        status, headers, body = handler.handle_chains(chain=None, query_params={})

        # Verify
        assert status == 200
        assert b"test-chain" in body or b"Test Chain" in body

    @pytest.mark.integration
    def test_chains_handler_with_connection_error(
        self, mock_chain, mock_connection_error_response
    ):
        """Test chains handler with connection error"""
        # Setup
        mock_chain.set_response("getchaintotals", mock_connection_error_response)
        app_state.get_state().chains = [mock_chain]

        handler = ChainHandler()

        # Execute
        status, headers, body = handler.handle_chains(chain=None, query_params={})

        # Verify - should still return 200 but show connection error
        assert status == 200
        assert b"No Connection" in body


class TestBlockBrowsing:
    """Test block browsing functionality"""

    @pytest.mark.integration
    def test_block_handler(self, mock_rpc_calls, mock_block_response):
        """Test block detail handler"""
        # Setup
        mock_rpc_calls.set_response("getblock", mock_block_response)
        mock_rpc_calls.set_response(
            "getrawtransaction",
            {
                "result": {
                    "txid": "1111111111111111111111111111111111111111111111111111111111111111",
                    "version": 1,
                    "locktime": 0,
                    "vin": [],
                    "vout": [],
                    "size": 100,
                },
                "error": None,
            },
        )
        app_state.get_state().chains = [mock_rpc_calls]

        handler = BlockHandler()

        # Execute
        status, headers, body = handler.handle_block_detail(mock_rpc_calls, 100, {})

        # Verify
        assert status == 200
        assert b"deadbeef" in body or b"100" in body

    @pytest.mark.integration
    def test_block_not_found(self, mock_rpc_calls, mock_rpc_error_response):
        """Test block handler with invalid block"""
        # Setup
        mock_rpc_calls.set_response("getblock", mock_rpc_error_response)
        mock_rpc_calls.set_response("getblockhash", mock_rpc_error_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = BlockHandler()

        # Execute
        status, headers, body = handler.handle_block_detail(mock_rpc_calls, 999999, {})

        # Verify - should return error status
        assert status in [400, 404, 500]


class TestTransactionViewing:
    """Test transaction viewing functionality"""

    @pytest.mark.integration
    def test_transaction_handler(self, mock_rpc_calls, mock_transaction_response):
        """Test transaction detail handler"""
        # Setup
        mock_rpc_calls.set_response("getrawtransaction", mock_transaction_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = TransactionHandler()

        # Execute
        txid = "1111111111111111111111111111111111111111111111111111111111111111"
        status, headers, body = handler.handle_transaction_detail(mock_rpc_calls, txid, {})

        # Verify
        assert status == 200
        assert txid.encode() in body


class TestAssetExploration:
    """Test asset exploration functionality"""

    @pytest.mark.integration
    def test_asset_handler(self, mock_rpc_calls, mock_asset_response):
        """Test asset detail handler"""
        # Setup
        mock_rpc_calls.set_response("listassets", mock_asset_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = AssetHandler()

        # Execute
        status, headers, body = handler.handle_asset_detail(mock_rpc_calls, "TestAsset", {})

        # Verify
        assert status == 200
        assert b"TestAsset" in body


class TestStreamItems:
    """Test stream item retrieval"""

    @pytest.mark.integration
    def test_stream_handler(self, mock_rpc_calls, mock_stream_response):
        """Test stream detail handler"""
        # Setup
        mock_rpc_calls.set_response("liststreams", mock_stream_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = StreamHandler()

        # Execute
        status, headers, body = handler.handle_stream_detail(mock_rpc_calls, "TestStream", {})

        # Verify
        assert status == 200
        assert b"TestStream" in body


class TestServices:
    """Test service layer"""

    @pytest.mark.unit
    def test_pagination_service_exists(self):
        """Test that pagination service exists"""
        from services.pagination_service import PaginationService

        service = PaginationService()
        assert service is not None

    @pytest.mark.unit
    def test_formatting_service_exists(self):
        """Test that formatting service exists"""
        from services.formatting_service import FormattingService

        service = FormattingService()
        assert service is not None

    @pytest.mark.unit
    def test_blockchain_service_exists(self):
        """Test that blockchain service can be imported"""
        from services.blockchain_service import BlockchainService

        assert BlockchainService is not None


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.integration
    def test_chain_home_connection_error(self, mock_rpc_calls, mock_connection_error_response):
        """Test chain home with connection error"""
        # Setup
        mock_rpc_calls.set_response("getchaintotals", mock_connection_error_response)
        mock_rpc_calls.set_response("getinfo", mock_connection_error_response)
        mock_rpc_calls.set_response("getblockchaininfo", mock_connection_error_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = ChainHandler()

        # Execute
        status, headers, body = handler.handle_chain_home(mock_rpc_calls, {})

        # Verify - Should handle error gracefully
        assert status in [200, 500]


class TestFastAPIApp:
    """Test FastAPI application"""

    @pytest.mark.unit
    def test_fastapi_app_creates(self):
        """Test that FastAPI app can be created"""
        from main import create_app

        app = create_app()
        assert app is not None
        assert app.title == "MultiChain Explorer 2"

    @pytest.mark.unit
    def test_fastapi_app_has_routes(self):
        """Test that FastAPI app has routes registered"""
        from main import create_app

        app = create_app()
        routes = [getattr(route, 'path', None) for route in app.routes if hasattr(route, 'path')]
        
        # Check some expected routes exist
        assert len(routes) > 0  # Should have some routes
        # Either has root or chain routes
        has_routes = any(r is not None for r in routes)
        assert has_routes


@pytest.mark.smoke
class TestSmokeTests:
    """Quick smoke tests for critical paths"""

    def test_handlers_can_be_instantiated(self):
        """Test that all handlers can be instantiated"""
        from handlers.block_handler import BlockHandler
        from handlers.transaction_handler import TransactionHandler
        from handlers.address_handler import AddressHandler
        from handlers.asset_handler import AssetHandler
        from handlers.stream_handler import StreamHandler
        from handlers.chain_handler import ChainHandler
        from handlers.permission_handler import PermissionHandler

        assert BlockHandler() is not None
        assert TransactionHandler() is not None
        assert AddressHandler() is not None
        assert AssetHandler() is not None
        assert StreamHandler() is not None
        assert ChainHandler() is not None
        assert PermissionHandler() is not None

    def test_chain_object_creation(self, mock_chain_config):
        """Test that chain object can be created"""
        # Initialize app_state.settings with test chain config
        app_state.get_state().settings = {"test-chain": mock_chain_config}
        chain = multichain.MCEChain("test-chain")
        assert chain is not None
        assert chain.name == "test-chain"
        # Clean up
        app_state.get_state().settings = {}
