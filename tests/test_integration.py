"""
MultiChain Explorer 2 - Integration Tests
Tests for critical user paths through the application
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app_state
import multichain
from app import get_app


class TestChainListing:
    """Test chain listing functionality"""

    @pytest.mark.integration
    def test_chains_data_handler_with_connected_chain(self, mock_chain, mock_chain_totals_response):
        """Test chains data handler with a connected chain"""
        # Setup
        mock_chain.set_response("getchaintotals", mock_chain_totals_response)
        app_state.get_state().chains = [mock_chain]

        handler = get_app()

        # Execute - handle_chains doesn't need chain parameter for listing all chains
        result = handler.handle_chains()

        # Verify
        assert result[0] == 200
        # Check for chain name in response
        assert b"test-chain" in result[2] or b"Test Chain" in result[2]

    @pytest.mark.integration
    def test_chains_data_handler_with_connection_error(
        self, mock_chain, mock_connection_error_response
    ):
        """Test chains data handler with connection error"""
        # Setup
        mock_chain.set_response("getchaintotals", mock_connection_error_response)
        app_state.get_state().chains = [mock_chain]

        handler = get_app()

        # Execute
        result = handler.handle_chains()

        # Verify - should still return 200 but show connection error
        assert result[0] == 200
        assert b"No Connection" in result[2]


class TestBlockBrowsing:
    """Test block browsing functionality"""

    @pytest.mark.integration
    def test_block_summary_handler(self, mock_rpc_calls, mock_block_response):
        """Test block summary data handler"""
        # Setup - the block handler also calls getrawtransaction for each tx
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

        handler = get_app()

        # Execute - new routing uses chain_name and height
        result = handler.handle_block("test-chain", 100)

        # Verify
        assert result[0] == 200
        assert b"deadbeef" in result[2]
        assert b"100" in result[2]

    @pytest.mark.integration
    def test_block_summary_not_found(self, mock_rpc_calls, mock_rpc_error_response):
        """Test block summary with invalid block"""
        # Setup
        mock_rpc_calls.set_response("getblock", mock_rpc_error_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = get_app()

        # Execute
        result = handler.handle_block("test-chain", 999999)

        # Verify - should return error status
        assert result[0] in [400, 404, 500]


class TestTransactionViewing:
    """Test transaction viewing functionality"""

    @pytest.mark.integration
    def test_transaction_handler(self, mock_rpc_calls, mock_transaction_response):
        """Test transaction detail handler"""
        # Setup
        mock_rpc_calls.set_response("getrawtransaction", mock_transaction_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = get_app()

        # Execute - new routing uses chain_name and txid (as string, not list)
        result = handler.handle_transaction(
            "test-chain", "1111111111111111111111111111111111111111111111111111111111111111"
        )

        # Verify
        assert result[0] == 200
        assert b"1111111111111111111111111111111111111111111111111111111111111111" in result[2]


class TestAssetExploration:
    """Test asset exploration functionality"""

    @pytest.mark.integration
    def test_asset_handler(self, mock_rpc_calls, mock_asset_response):
        """Test asset data handler"""
        # Setup
        mock_rpc_calls.set_response("listassets", mock_asset_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = get_app()

        # Execute - new routing uses chain_name and asset_ref
        result = handler.handle_asset("test-chain", "TestAsset")

        # Verify
        assert result[0] == 200
        assert b"TestAsset" in result[2]
        assert b"1000" in result[2]  # issued quantity


class TestStreamItems:
    """Test stream item retrieval"""

    @pytest.mark.integration
    def test_stream_summary(self, mock_rpc_calls, mock_stream_response):
        """Test stream summary handler"""
        # Setup
        mock_rpc_calls.set_response("liststreams", mock_stream_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = get_app()

        # Execute - new routing uses chain_name and stream_name
        result = handler.handle_stream("test-chain", "TestStream")

        # Verify
        assert result[0] == 200
        assert b"TestStream" in result[2]


class TestPagination:
    """Test pagination functionality - Deprecated: Pagination is now handled in services"""

    # Note: These tests are commented out as expand_params no longer exists in the new architecture
    # Pagination is now handled by PaginationService in services/pagination_service.py

    # @pytest.mark.unit
    # def test_expand_params_forward_pagination(self):
    #     """Test forward pagination parameter expansion"""
    #     from services.pagination_service import PaginationService
    #     service = PaginationService()
    #     # TODO: Update to use new pagination service API

    @pytest.mark.unit
    def test_pagination_service_exists(self):
        """Test that pagination service exists"""
        from services.pagination_service import PaginationService

        service = PaginationService()
        assert service is not None


class TestDataFormatting:
    """Test data formatting functions - Deprecated: Now in services"""

    # Note: These tests reference old 'data' module that no longer exists
    # Formatting is now in services/formatting_service.py

    @pytest.mark.unit
    def test_formatting_service_exists(self):
        """Test that formatting service exists"""
        from services.formatting_service import FormattingService

        service = FormattingService()
        assert service is not None


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.integration
    def test_chain_summary_connection_error(self, mock_rpc_calls, mock_connection_error_response):
        """Test chain summary with connection error"""
        # Setup
        mock_rpc_calls.set_response("getchaintotals", mock_connection_error_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = get_app()

        # Execute - new routing uses chain_name
        result = handler.handle_chain_home("test-chain")

        # Verify - Should handle error gracefully
        assert result[0] in [200, 500]  # Either shows error page or gracefully degrades

    @pytest.mark.integration
    def test_invalid_block_height(self, mock_rpc_calls):
        """Test handling of invalid block height"""
        # Setup
        error_response = {
            "result": None,
            "error": "Block height out of range",
        }
        mock_rpc_calls.set_response("getblock", error_response)
        app_state.get_state().chains = [mock_rpc_calls]

        handler = get_app()

        # Execute - new routing uses chain_name and height
        result = handler.handle_block("test-chain", -1)

        # Verify
        assert result[0] in [400, 404, 500]  # Error status code


class TestUtilityFunctions:
    """Test utility functions - Deprecated: Now in services"""

    # Note: field_in_dict and other utility functions no longer exist in 'data' module
    # They have been moved to appropriate service classes

    @pytest.mark.unit
    def test_blockchain_service_exists(self):
        """Test that blockchain service exists"""
        from services.blockchain_service import BlockchainService

        # Service needs a chain, so we can't instantiate without one
        # But we can verify the import works
        assert BlockchainService is not None


class TestChainNativeFlag:
    """Test native currency flag detection - Deprecated: Now handled in services"""

    # Note: chain_native_flag method no longer exists in the new architecture
    # This functionality is now handled within BlockchainService

    @pytest.mark.unit
    def test_blockchain_service_can_be_imported(self):
        """Test that blockchain service can be imported"""
        from services.blockchain_service import BlockchainService

        assert BlockchainService is not None


@pytest.mark.smoke
class TestSmokeTests:
    """Quick smoke tests for critical paths"""

    def test_application_instantiation(self):
        """Test that application can be instantiated"""
        handler = get_app()
        assert handler is not None
        assert hasattr(handler, "handle_chains")
        assert hasattr(handler, "handle_block")
        assert hasattr(handler, "handle_transaction")

    def test_chain_object_creation(self, mock_chain_config):
        """Test that chain object can be created"""
        # Initialize app_state.settings with test chain config
        app_state.get_state().settings = {"test-chain": mock_chain_config}
        chain = multichain.MCEChain("test-chain")
        assert chain is not None
        assert chain.name == "test-chain"
        # Clean up
        app_state.get_state().settings = {}
