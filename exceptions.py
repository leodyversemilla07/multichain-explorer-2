"""
MultiChain Explorer 2 - Custom Exceptions
Structured error handling for better debugging and user experience
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MCEException(Exception):
    """Base exception for all MultiChain Explorer errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON responses"""
        return {"error": self.__class__.__name__, "message": self.message, "details": self.details}


class ChainConnectionError(MCEException):
    """Raised when unable to connect to MultiChain node"""

    def __init__(self, chain_name: str, details: Optional[Dict[str, Any]] = None):
        message = f"Cannot connect to chain: {chain_name}"
        super().__init__(message, details)
        self.chain_name = chain_name


class ChainNotFoundError(MCEException):
    """Raised when requested chain doesn't exist in configuration"""

    def __init__(self, chain_name: str):
        message = f"Chain not found: {chain_name}"
        super().__init__(message, {"chain_name": chain_name})
        self.chain_name = chain_name


class InvalidParameterError(MCEException):
    """Raised when request parameter is invalid"""

    def __init__(self, parameter: str, value: str, reason: str):
        message = f"Invalid parameter '{parameter}': {reason}"
        details = {"parameter": parameter, "value": value, "reason": reason}
        super().__init__(message, details)
        self.parameter = parameter
        self.value = value


class ResourceNotFoundError(MCEException):
    """Raised when requested resource doesn't exist"""

    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} not found: {identifier}"
        details = {"resource_type": resource_type, "identifier": identifier}
        super().__init__(message, details)
        self.resource_type = resource_type
        self.identifier = identifier


class BlockNotFoundError(ResourceNotFoundError):
    """Raised when block doesn't exist"""

    def __init__(self, block_id: str):
        super().__init__("Block", block_id)
        self.block_id = block_id


class TransactionNotFoundError(ResourceNotFoundError):
    """Raised when transaction doesn't exist"""

    def __init__(self, txid: str):
        super().__init__("Transaction", txid)
        self.txid = txid


class AddressNotFoundError(ResourceNotFoundError):
    """Raised when address doesn't exist or has no activity"""

    def __init__(self, address: str):
        super().__init__("Address", address)
        self.address = address


class AssetNotFoundError(ResourceNotFoundError):
    """Raised when asset doesn't exist"""

    def __init__(self, asset_name: str):
        super().__init__("Asset", asset_name)
        self.asset_name = asset_name


class StreamNotFoundError(ResourceNotFoundError):
    """Raised when stream doesn't exist"""

    def __init__(self, stream_name: str):
        super().__init__("Stream", stream_name)
        self.stream_name = stream_name


class RPCError(MCEException):
    """Raised when MultiChain RPC call fails"""

    def __init__(self, method: str, error_message: str, error_code: Optional[int] = None):
        message = f"RPC error calling {method}: {error_message}"
        details = {"method": method, "error_message": error_message, "error_code": error_code}
        super().__init__(message, details)
        self.method = method
        self.error_code = error_code


class ConfigurationError(MCEException):
    """Raised when configuration is invalid or missing"""

    def __init__(self, config_key: str, reason: str):
        message = f"Configuration error for '{config_key}': {reason}"
        details = {"config_key": config_key, "reason": reason}
        super().__init__(message, details)
        self.config_key = config_key


class ValidationError(MCEException):
    """Raised when input validation fails"""

    def __init__(self, field: str, value: str, constraints: str):
        message = f"Validation failed for '{field}': {constraints}"
        details = {"field": field, "value": value, "constraints": constraints}
        super().__init__(message, details)
        self.field = field


# Error code mapping for HTTP status codes
ERROR_HTTP_CODES = {
    MCEException: 500,
    ChainConnectionError: 503,
    ChainNotFoundError: 404,
    InvalidParameterError: 400,
    ResourceNotFoundError: 404,
    BlockNotFoundError: 404,
    TransactionNotFoundError: 404,
    AddressNotFoundError: 404,
    AssetNotFoundError: 404,
    StreamNotFoundError: 404,
    RPCError: 502,
    ConfigurationError: 500,
    ValidationError: 400,
}


def get_http_status(exception: Exception) -> int:
    """Get appropriate HTTP status code for exception"""
    # Check most specific exceptions first
    exc_type = type(exception)
    if exc_type in ERROR_HTTP_CODES:
        return ERROR_HTTP_CODES[exc_type]

    # Fall back to checking inheritance hierarchy
    for exc_class, status_code in ERROR_HTTP_CODES.items():
        if isinstance(exception, exc_class):
            return status_code

    return 500  # Internal Server Error for unknown exceptions


def format_error_html(exception: Exception, debug: bool = False) -> str:
    """Format exception as HTML error message"""
    if isinstance(exception, MCEException):
        error_class = exception.__class__.__name__
        message = exception.message

        html = f'<div class="alert alert-danger" role="alert">'
        html += f"<h4>{error_class}</h4>"
        html += f"<p>{message}</p>"

        if debug and exception.details:
            html += "<details><summary>Debug Details</summary>"
            html += "<pre>"
            for key, value in exception.details.items():
                html += f"{key}: {value}\n"
            html += "</pre></details>"

        html += "</div>"
        return html
    else:
        # Generic exception
        html = '<div class="alert alert-danger" role="alert">'
        html += f"<h4>Error</h4>"
        html += f"<p>{str(exception)}</p>"
        html += "</div>"
        return html


def log_exception(exception: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Log exception with context information"""
    context = context or {}

    if isinstance(exception, MCEException):
        # Log custom exceptions at appropriate level
        if isinstance(exception, (ChainConnectionError, RPCError)):
            # Service errors - warning level
            logger.warning(
                f"{exception.__class__.__name__}: {exception.message}",
                extra={"details": exception.details, **context},
            )
        elif isinstance(exception, (ResourceNotFoundError, ChainNotFoundError)):
            # Not found errors - info level (not really errors)
            logger.info(
                f"{exception.__class__.__name__}: {exception.message}",
                extra={"details": exception.details, **context},
            )
        elif isinstance(exception, (InvalidParameterError, ValidationError)):
            # Client errors - info level
            logger.info(
                f"{exception.__class__.__name__}: {exception.message}",
                extra={"details": exception.details, **context},
            )
        else:
            # Other MCE exceptions - error level
            logger.error(
                f"{exception.__class__.__name__}: {exception.message}",
                extra={"details": exception.details, **context},
            )
    else:
        # Unexpected exceptions - always log at error level with traceback
        logger.error(f"Unexpected exception: {str(exception)}", exc_info=True, extra=context)


def handle_exception(
    exception: Exception,
    chain: Optional[Any] = None,
    params: Optional[List[Any]] = None,
    nparams: Optional[Dict[str, Any]] = None,
    debug: bool = False,
) -> Tuple[int, List[Tuple[str, str]], bytes]:
    """
    Global exception handler that converts exceptions to HTTP responses

    Args:
        exception: The exception to handle
        chain: Current chain context (optional)
        params: URL parameters (optional)
        nparams: Query parameters (optional)
        debug: Whether to include debug information

    Returns:
        Tuple of (status_code, headers, body)
    """
    # Log the exception with context
    context = {
        "chain": chain.config["name"] if chain else None,
        "params": params,
        "nparams": nparams,
    }
    log_exception(exception, context)

    # Get appropriate HTTP status code
    status_code = get_http_status(exception)

    # Format error as HTML (this will be improved when we add templating)
    error_html = format_error_html(exception, debug=debug)

    # Build simple error page
    title = exception.__class__.__name__ if isinstance(exception, MCEException) else "Error"

    body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{title}</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50">
        <div class="container mx-auto px-4 py-8 max-w-4xl">
            <div class="bg-white rounded-lg shadow-lg p-8">
                <h1 class="text-3xl font-bold text-gray-900 mb-6">MultiChain Explorer</h1>
                {error_html}
                <div class="mt-6">
                    <a href="/" class="text-blue-600 hover:text-blue-800 underline">← Back to Home</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    headers = [("Content-type", "text/html; charset=utf-8")]

    return (status_code, headers, body.encode("utf-8"))
