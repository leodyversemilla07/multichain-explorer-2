"""
Tests for exception handling and error responses
"""
from unittest.mock import MagicMock, patch

import pytest

from exceptions import (
    ERROR_HTTP_CODES,
    AddressNotFoundError,
    AssetNotFoundError,
    BlockNotFoundError,
    ChainConnectionError,
    ChainNotFoundError,
    ConfigurationError,
    InvalidParameterError,
    MCEException,
    ResourceNotFoundError,
    RPCError,
    StreamNotFoundError,
    TransactionNotFoundError,
    ValidationError,
    format_error_html,
    get_http_status,
    handle_exception,
    log_exception,
)


class TestMCEException:
    """Test base exception class"""

    def test_basic_exception(self):
        """Test basic exception creation"""
        exc = MCEException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.details == {}

    def test_exception_with_details(self):
        """Test exception with details"""
        details = {"key": "value", "code": 123}
        exc = MCEException("Test error", details)
        assert exc.details == details

    def test_to_dict(self):
        """Test exception serialization to dict"""
        exc = MCEException("Test error", {"key": "value"})
        result = exc.to_dict()

        assert result["error"] == "MCEException"
        assert result["message"] == "Test error"
        assert result["details"] == {"key": "value"}


class TestChainErrors:
    """Test chain-related exceptions"""

    def test_chain_connection_error(self):
        """Test chain connection error"""
        exc = ChainConnectionError("testchain")
        assert "testchain" in str(exc)
        assert exc.chain_name == "testchain"

    def test_chain_connection_error_with_details(self):
        """Test chain connection error with details"""
        exc = ChainConnectionError("testchain", {"reason": "timeout"})
        assert exc.details["reason"] == "timeout"
        assert exc.chain_name == "testchain"

    def test_chain_not_found_error(self):
        """Test chain not found error"""
        exc = ChainNotFoundError("missingchain")
        assert "missingchain" in str(exc)
        assert exc.chain_name == "missingchain"
        assert exc.details["chain_name"] == "missingchain"


class TestParameterErrors:
    """Test parameter validation exceptions"""

    def test_invalid_parameter_error(self):
        """Test invalid parameter error"""
        exc = InvalidParameterError("height", "abc", "must be numeric")
        assert "height" in str(exc)
        assert exc.parameter == "height"
        assert exc.value == "abc"
        assert exc.details["reason"] == "must be numeric"

    def test_validation_error(self):
        """Test validation error"""
        exc = ValidationError("email", "invalid@", "must be valid email")
        assert "email" in str(exc)
        assert exc.field == "email"
        assert exc.details["value"] == "invalid@"


class TestResourceErrors:
    """Test resource not found exceptions"""

    def test_resource_not_found_error(self):
        """Test generic resource not found error"""
        exc = ResourceNotFoundError("Widget", "widget-123")
        assert "Widget" in str(exc)
        assert "widget-123" in str(exc)
        assert exc.resource_type == "Widget"
        assert exc.identifier == "widget-123"

    def test_block_not_found_error(self):
        """Test block not found error"""
        exc = BlockNotFoundError("12345")
        assert "Block" in str(exc)
        assert "12345" in str(exc)
        assert exc.block_id == "12345"
        # Should inherit from ResourceNotFoundError
        assert isinstance(exc, ResourceNotFoundError)

    def test_transaction_not_found_error(self):
        """Test transaction not found error"""
        txid = "abc123def456"
        exc = TransactionNotFoundError(txid)
        assert "Transaction" in str(exc)
        assert txid in str(exc)
        assert exc.txid == txid

    def test_address_not_found_error(self):
        """Test address not found error"""
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        exc = AddressNotFoundError(address)
        assert "Address" in str(exc)
        assert address in str(exc)
        assert exc.address == address

    def test_asset_not_found_error(self):
        """Test asset not found error"""
        exc = AssetNotFoundError("myasset")
        assert "Asset" in str(exc)
        assert "myasset" in str(exc)
        assert exc.asset_name == "myasset"

    def test_stream_not_found_error(self):
        """Test stream not found error"""
        exc = StreamNotFoundError("mystream")
        assert "Stream" in str(exc)
        assert "mystream" in str(exc)
        assert exc.stream_name == "mystream"


class TestRPCError:
    """Test RPC error handling"""

    def test_rpc_error_basic(self):
        """Test basic RPC error"""
        exc = RPCError("getblock", "Block not found")
        assert "getblock" in str(exc)
        assert "Block not found" in str(exc)
        assert exc.method == "getblock"
        assert exc.details["error_message"] == "Block not found"

    def test_rpc_error_with_code(self):
        """Test RPC error with error code"""
        exc = RPCError("getblock", "Block not found", -5)
        assert exc.error_code == -5
        assert exc.details["error_code"] == -5


class TestConfigurationError:
    """Test configuration error handling"""

    def test_configuration_error(self):
        """Test configuration error"""
        exc = ConfigurationError("database.host", "missing required value")
        assert "database.host" in str(exc)
        assert "missing required value" in str(exc)
        assert exc.config_key == "database.host"
        assert exc.details["reason"] == "missing required value"


class TestHTTPStatusCodes:
    """Test HTTP status code mapping"""

    def test_base_exception_500(self):
        """Test base exception returns 500"""
        exc = MCEException("Generic error")
        assert get_http_status(exc) == 500

    def test_chain_connection_error_503(self):
        """Test chain connection error returns 503"""
        exc = ChainConnectionError("chain1")
        assert get_http_status(exc) == 503

    def test_chain_not_found_404(self):
        """Test chain not found returns 404"""
        exc = ChainNotFoundError("missing")
        assert get_http_status(exc) == 404

    def test_invalid_parameter_400(self):
        """Test invalid parameter returns 400"""
        exc = InvalidParameterError("height", "abc", "must be numeric")
        assert get_http_status(exc) == 400

    def test_resource_not_found_404(self):
        """Test resource not found returns 404"""
        exc = ResourceNotFoundError("Block", "999999")
        assert get_http_status(exc) == 404

    def test_block_not_found_404(self):
        """Test block not found returns 404"""
        exc = BlockNotFoundError("12345")
        assert get_http_status(exc) == 404

    def test_rpc_error_502(self):
        """Test RPC error returns 502"""
        exc = RPCError("getinfo", "Connection refused")
        assert get_http_status(exc) == 502

    def test_validation_error_400(self):
        """Test validation error returns 400"""
        exc = ValidationError("email", "bad", "invalid format")
        assert get_http_status(exc) == 400

    def test_unknown_exception_500(self):
        """Test unknown exception returns 500"""
        exc = ValueError("Some random error")
        assert get_http_status(exc) == 500

    def test_all_exceptions_in_mapping(self):
        """Test all exception classes have HTTP status codes"""
        exception_classes = [
            MCEException,
            ChainConnectionError,
            ChainNotFoundError,
            InvalidParameterError,
            ResourceNotFoundError,
            BlockNotFoundError,
            TransactionNotFoundError,
            AddressNotFoundError,
            AssetNotFoundError,
            StreamNotFoundError,
            RPCError,
            ConfigurationError,
            ValidationError,
        ]

        for exc_class in exception_classes:
            assert exc_class in ERROR_HTTP_CODES


class TestErrorHTMLFormatting:
    """Test HTML error formatting"""

    def test_format_mce_exception_basic(self):
        """Test formatting MCEException as HTML"""
        exc = MCEException("Test error message")
        html = format_error_html(exc)

        assert "alert-danger" in html
        assert "MCEException" in html
        assert "Test error message" in html

    def test_format_with_details_debug_off(self):
        """Test formatting with details but debug off"""
        exc = MCEException("Error", {"key": "value"})
        html = format_error_html(exc, debug=False)

        assert "Error" in html
        # Details should not be shown when debug=False
        assert "key" not in html
        assert "value" not in html

    def test_format_with_details_debug_on(self):
        """Test formatting with details and debug on"""
        exc = MCEException("Error", {"key": "value", "code": 123})
        html = format_error_html(exc, debug=True)

        assert "Error" in html
        assert "Debug Details" in html
        assert "key" in html
        assert "value" in html

    def test_format_chain_connection_error(self):
        """Test formatting chain connection error"""
        exc = ChainConnectionError("testchain")
        html = format_error_html(exc)

        assert "ChainConnectionError" in html
        assert "testchain" in html

    def test_format_block_not_found(self):
        """Test formatting block not found error"""
        exc = BlockNotFoundError("12345")
        html = format_error_html(exc)

        assert "BlockNotFoundError" in html
        assert "12345" in html

    def test_format_rpc_error(self):
        """Test formatting RPC error"""
        exc = RPCError("getblock", "Not found", -5)
        html = format_error_html(exc)

        assert "RPCError" in html
        assert "getblock" in html

    def test_format_generic_exception(self):
        """Test formatting generic (non-MCE) exception"""
        exc = ValueError("Generic Python error")
        html = format_error_html(exc)

        assert "alert-danger" in html
        assert "Error" in html
        assert "Generic Python error" in html

    def test_html_contains_bootstrap_classes(self):
        """Test that HTML output contains Bootstrap classes"""
        exc = MCEException("Test")
        html = format_error_html(exc)

        assert 'class="alert alert-danger"' in html
        assert 'role="alert"' in html


class TestExceptionHierarchy:
    """Test exception inheritance"""

    def test_all_inherit_from_base(self):
        """Test all custom exceptions inherit from MCEException"""
        exceptions = [
            ChainConnectionError("test"),
            ChainNotFoundError("test"),
            InvalidParameterError("p", "v", "r"),
            ResourceNotFoundError("T", "id"),
            BlockNotFoundError("123"),
            TransactionNotFoundError("abc"),
            AddressNotFoundError("addr"),
            AssetNotFoundError("asset"),
            StreamNotFoundError("stream"),
            RPCError("method", "msg"),
            ConfigurationError("key", "reason"),
            ValidationError("field", "val", "constraints"),
        ]

        for exc in exceptions:
            assert isinstance(exc, MCEException)
            assert isinstance(exc, Exception)

    def test_resource_not_found_hierarchy(self):
        """Test resource exceptions inherit correctly"""
        block_exc = BlockNotFoundError("123")
        tx_exc = TransactionNotFoundError("abc")
        addr_exc = AddressNotFoundError("addr")
        asset_exc = AssetNotFoundError("asset")
        stream_exc = StreamNotFoundError("stream")

        # All should be ResourceNotFoundError
        assert isinstance(block_exc, ResourceNotFoundError)
        assert isinstance(tx_exc, ResourceNotFoundError)
        assert isinstance(addr_exc, ResourceNotFoundError)
        assert isinstance(asset_exc, ResourceNotFoundError)
        assert isinstance(stream_exc, ResourceNotFoundError)

        # And MCEException
        assert isinstance(block_exc, MCEException)
        assert isinstance(tx_exc, MCEException)


class TestErrorDetails:
    """Test error detail preservation"""

    def test_details_preserved_in_hierarchy(self):
        """Test details are preserved through inheritance"""
        exc = BlockNotFoundError("12345")
        details = exc.to_dict()

        assert "details" in details
        assert details["details"]["resource_type"] == "Block"
        assert details["details"]["identifier"] == "12345"

    def test_custom_details_preserved(self):
        """Test custom details are preserved"""
        exc = ChainConnectionError("chain1", {"timeout": 30, "attempts": 3})

        assert exc.details["timeout"] == 30
        assert exc.details["attempts"] == 3


class TestExceptionLogging:
    """Test exception logging"""

    @patch("exceptions.logger")
    def test_log_chain_connection_error(self, mock_logger):
        """Test logging of chain connection errors"""
        exc = ChainConnectionError("chain1")
        log_exception(exc)

        # Should log at warning level
        mock_logger.warning.assert_called_once()
        args = mock_logger.warning.call_args
        assert "ChainConnectionError" in args[0][0]

    @patch("exceptions.logger")
    def test_log_resource_not_found(self, mock_logger):
        """Test logging of resource not found errors"""
        exc = BlockNotFoundError("12345")
        log_exception(exc)

        # Should log at info level (not a real error)
        mock_logger.info.assert_called_once()

    @patch("exceptions.logger")
    def test_log_validation_error(self, mock_logger):
        """Test logging of validation errors"""
        exc = ValidationError("field", "value", "constraints")
        log_exception(exc)

        # Should log at info level
        mock_logger.info.assert_called_once()

    @patch("exceptions.logger")
    def test_log_unexpected_exception(self, mock_logger):
        """Test logging of unexpected exceptions"""
        exc = ValueError("Unexpected error")
        log_exception(exc)

        # Should log at error level with traceback
        mock_logger.error.assert_called_once()
        args = mock_logger.error.call_args
        assert args[1]["exc_info"] is True

    @patch("exceptions.logger")
    def test_log_with_context(self, mock_logger):
        """Test logging with context information"""
        exc = MCEException("Test error")
        context = {"chain": "chain1", "params": ["block", "123"]}
        log_exception(exc, context)

        # Context should be passed to logger
        mock_logger.error.assert_called_once()
        args = mock_logger.error.call_args
        extra = args[1]["extra"]
        assert extra["chain"] == "chain1"


class TestExceptionHandler:
    """Test global exception handler"""

    def test_handle_mce_exception(self):
        """Test handling MCEException"""
        exc = BlockNotFoundError("12345")
        status, headers, body = handle_exception(exc)

        assert status == 404
        assert ("Content-type", "text/html; charset=utf-8") in headers
        assert b"BlockNotFoundError" in body
        assert b"12345" in body

    def test_handle_chain_connection_error(self):
        """Test handling chain connection error"""
        exc = ChainConnectionError("chain1")
        status, headers, body = handle_exception(exc)

        assert status == 503
        assert b"ChainConnectionError" in body

    def test_handle_generic_exception(self):
        """Test handling generic exception"""
        exc = ValueError("Something went wrong")
        status, headers, body = handle_exception(exc)

        assert status == 500
        assert b"Error" in body
        assert b"Something went wrong" in body

    def test_handle_exception_with_chain_context(self):
        """Test exception handler with chain context"""
        exc = BlockNotFoundError("12345")

        # Mock chain object
        chain = MagicMock()
        chain.config = {"name": "testchain"}

        with patch("exceptions.log_exception") as mock_log:
            status, headers, body = handle_exception(exc, chain=chain)

            # Should pass chain context to logger
            mock_log.assert_called_once()
            context = mock_log.call_args[0][1]
            assert context["chain"] == "testchain"

    def test_handle_exception_debug_mode(self):
        """Test exception handler in debug mode"""
        exc = MCEException("Test error", {"detail1": "value1"})
        status, headers, body = handle_exception(exc, debug=True)

        # Debug details should be in response
        assert b"Debug Details" in body
        assert b"detail1" in body

    def test_handle_exception_no_debug(self):
        """Test exception handler without debug mode"""
        exc = MCEException("Test error", {"detail1": "value1"})
        status, headers, body = handle_exception(exc, debug=False)

        # Debug details should NOT be in response
        assert b"Debug Details" not in body
        assert b"detail1" not in body

    def test_handle_exception_with_params(self):
        """Test exception handler with parameters"""
        exc = InvalidParameterError("height", "abc", "must be numeric")
        params = ["block", "abc"]
        nparams = {"count": "10"}

        with patch("exceptions.log_exception") as mock_log:
            status, headers, body = handle_exception(exc, params=params, nparams=nparams)

            # Should pass params to logger
            context = mock_log.call_args[0][1]
            assert context["params"] == params
            assert context["nparams"] == nparams
