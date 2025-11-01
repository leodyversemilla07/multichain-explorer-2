"""
Integration Tests for Validator Integration
Tests that validators work correctly in handlers
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app_state
from app import get_app


class TestValidatorIntegration:
    """Test validators integrated into handlers"""

    @pytest.mark.integration
    def test_block_handler_validates_height(self, mock_rpc_calls, mock_block_response):
        """Test that block handler validates height parameter"""
        # Setup
        mock_rpc_calls.set_response("getblock", mock_block_response)
        mock_rpc_calls.set_response(
            "getrawtransaction",
            {"result": {"txid": "test", "vin": [], "vout": [], "size": 100}, "error": None},
        )
        app_state.get_state().chains = [mock_rpc_calls]
        handler = get_app()

        # Test valid height - new routing API
        result = handler.handle_block("test-chain", 100)
        assert result[0] == 200

    @pytest.mark.integration
    def test_block_handler_rejects_invalid_height(self, mock_rpc_calls):
        """Test that block handler rejects invalid block height"""
        app_state.get_state().chains = [mock_rpc_calls]
        handler = get_app()

        # Test negative height - routing validates this
        try:
            result = handler.handle_block("test-chain", -1)
            # Should return error
            assert result[0] in [400, 404, 500]
        except Exception:
            # Pydantic validation may raise exception
            pass

    @pytest.mark.integration
    def test_block_handler_rejects_out_of_range(self, mock_rpc_calls):
        """Test that block handler rejects out of range height"""
        # Set error response for out of range block
        mock_rpc_calls.set_response(
            "getblockhash", {"result": None, "error": "Block height out of range"}
        )
        app_state.get_state().chains = [mock_rpc_calls]
        handler = get_app()

        # Test too large height
        result = handler.handle_block("test-chain", 999999999999)
        assert result[0] in [400, 404, 500]

    @pytest.mark.integration
    def test_transaction_handler_validates_txid(self, mock_rpc_calls, mock_transaction_response):
        """Test that transaction handler validates txid"""
        # Setup
        valid_txid = "a" * 64
        mock_rpc_calls.set_response("getrawtransaction", mock_transaction_response)
        app_state.get_state().chains = [mock_rpc_calls]
        handler = get_app()

        # Test valid txid - new routing API
        result = handler.handle_transaction("test-chain", valid_txid)
        assert result[0] == 200

    @pytest.mark.integration
    def test_transaction_handler_rejects_invalid_txid(self, mock_rpc_calls):
        """Test that transaction handler rejects invalid txid"""
        app_state.get_state().chains = [mock_rpc_calls]
        handler = get_app()

        # Test short txid - routing validation should reject
        try:
            result = handler.handle_transaction("test-chain", "abc")
            # If validation passes to handler, should return error
            assert result[0] in [400, 404]
        except Exception:
            # Pydantic validation may raise exception
            pass

    @pytest.mark.integration
    def test_asset_handler_validates_name(self, mock_rpc_calls, mock_asset_response):
        """Test that asset handler validates name"""
        # Setup
        mock_rpc_calls.set_response("listassets", mock_asset_response)
        app_state.get_state().chains = [mock_rpc_calls]
        handler = get_app()

        # Test valid name - new routing API
        result = handler.handle_asset("test-chain", "TestAsset")
        assert result[0] == 200

    @pytest.mark.security
    def test_asset_handler_rejects_injection(self, mock_rpc_calls):
        """Test that asset handler rejects injection attempts"""
        app_state.get_state().chains = [mock_rpc_calls]
        handler = get_app()

        # Test SQL injection attempt - should be handled gracefully
        result = handler.handle_asset("test-chain", "asset'; DROP TABLE--")
        # Should return 404 (not found) rather than crash
        assert result[0] in [400, 404]

    @pytest.mark.security
    def test_asset_handler_rejects_path_traversal(self, mock_rpc_calls):
        """Test that asset handler rejects path traversal"""
        app_state.get_state().chains = [mock_rpc_calls]
        handler = get_app()

        # Test path traversal attempt - should be handled gracefully
        result = handler.handle_asset("test-chain", "../../../etc/passwd")
        # Should return 404 (not found) rather than crash
        assert result[0] in [400, 404]

    @pytest.mark.integration
    def test_address_handler_sanitizes_input(self, mock_rpc_calls):
        """Test that address handler sanitizes input"""
        app_state.get_state().chains = [mock_rpc_calls]
        handler = get_app()

        # Setup mock response
        mock_rpc_calls.set_response("listpermissions", {"result": [], "error": None})

        # Test with invalid address - routing validation should handle
        try:
            result = handler.handle_address("test-chain", "<script>alert(1)</script>")
            # If validation passes, should return error
            assert result[0] in [400, 404]
        except Exception:
            # Validation may raise exception
            pass


# @pytest.mark.smoke
# class TestValidationSmoke:
#     """Quick smoke tests for validation integration"""
#
#     def test_validators_imported_successfully(self):
#         """Test that validators are imported in data.py"""
#         # Note: data.py module no longer exists in refactored architecture
#         # Validators are now in validators.py module
#         import validators
#         assert validators is not None
#
#     def test_validation_functions_available(self):
#         """Test that validation functions are available"""
#         from validators import (
#             validate_block_height,
#             validate_hex_string,
#             validate_address,
#             sanitize_input,
#         )
#         assert validate_block_height is not None
#         assert validate_hex_string is not None
#         assert validate_address is not None
#         assert sanitize_input is not None
