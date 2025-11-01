# -*- coding: utf-8 -*-

"""
MultiChain Explorer HTTP Server
Modern HTTP server implementation using new routing architecture.
"""

import logging
import mimetypes
import os
import urllib.parse
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Optional, Tuple

import app_state
import utils
from app import get_app
from exceptions import handle_exception

logger = logging.getLogger(__name__)


class ExplorerHTTPHandler(BaseHTTPRequestHandler):
    """
    Modern HTTP request handler for MultiChain Explorer.

    Uses the new routing system from app.py instead of legacy URL parsing.
    """

    timeout = 30  # Increased timeout for better stability

    def _parse_query_params(self, path: str) -> Tuple[str, Dict[str, str]]:
        """
        Parse query parameters from URL path.

        Args:
            path: Full URL path with optional query string

        Returns:
            Tuple of (clean_path, query_params_dict)
        """
        query_params: Dict[str, str] = {}
        parsed_path = path.split("?", 1)

        if len(parsed_path) == 2:
            parsed_qs = urllib.parse.parse_qs(parsed_path[1])
            # Convert list values to single values
            for key, value in parsed_qs.items():
                # parse_qs returns Dict[str, List[str]], we need to convert to str
                single_value = value[0] if isinstance(value, list) and len(value) > 0 else ""
                query_params[key] = single_value
            path = parsed_path[0]

        return path, query_params

    def _send_response(self, content: Tuple[int, list, bytes]) -> None:
        """
        Send HTTP response to client.

        Args:
            content: Tuple of (status_code, headers, body)
        """
        try:
            status_code, headers, body = content

            self.send_response(status_code)
            for header_name, header_value in headers:
                self.send_header(header_name, header_value)
            self.end_headers()

            if body:
                self.wfile.write(body)

        except (IOError, BrokenPipeError, ConnectionResetError) as e:
            logger.debug(f"Connection error while sending response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending response: {e}")

    def _serve_static_file(self, filepath: str) -> Optional[Tuple[int, list, bytes]]:
        """
        Serve a static file from the static directory.

        Args:
            filepath: Relative path to the file (e.g., 'logo32.png' or 'css/style.css')

        Returns:
            Tuple of (status_code, headers, body) or None if file not found
        """
        try:
            # Get the static directory path (relative to script location)
            static_dir = Path(__file__).parent / "static"
            file_path = static_dir / filepath

            # Security: Ensure the resolved path is within static directory
            if not file_path.resolve().is_relative_to(static_dir.resolve()):
                logger.warning(f"Attempted path traversal: {filepath}")
                return None

            if not file_path.exists() or not file_path.is_file():
                return None

            # Read file content
            with open(file_path, "rb") as f:
                content = f.read()

            # Determine content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if content_type is None:
                content_type = "application/octet-stream"

            headers = [
                ("Content-Type", content_type),
                ("Content-Length", str(len(content))),
                ("Cache-Control", "public, max-age=3600"),  # Cache for 1 hour
            ]

            return (200, headers, content)

        except Exception as e:
            logger.error(f"Error serving static file {filepath}: {e}")
            return None

    def do_GET(self):
        """Handle GET requests using new routing system."""
        try:
            # Parse query parameters
            path, query_params = self._parse_query_params(self.path)

            # Remove trailing slash (except for root path)
            if path != "/" and path.endswith("/"):
                path = path.rstrip("/")

            logger.debug(f"GET {path} with params: {query_params}")

            # Check if this is a static file request
            # Handle both /static/file.ext and direct /file.ext paths
            if path.startswith("/static/"):
                # Remove /static/ prefix
                static_path = path[8:]
                static_content = self._serve_static_file(static_path)
                if static_content:
                    self._send_response(static_content)
                    return
            elif not path.startswith("/"):
                # Direct file request (e.g., logo32.png)
                static_content = self._serve_static_file(path)
                if static_content:
                    self._send_response(static_content)
                    return
            else:
                # Try without leading slash for common files
                clean_path = path.lstrip("/")
                if "/" not in clean_path and "." in clean_path:
                    # Looks like a file (has extension, no path separators)
                    static_content = self._serve_static_file(clean_path)
                    if static_content:
                        self._send_response(static_content)
                        return

            # Use new routing system
            state = app_state.get_state()
            if state.page_handler is None:
                raise RuntimeError("Application not initialized")

            content = state.page_handler.handle_request(
                path, method="GET", query_params=query_params
            )

            # Send response
            self._send_response(content)

        except Exception as e:
            logger.exception(f"Error handling GET request {self.path}")
            self._handle_error(e)

    def do_POST(self):
        """Handle POST requests using new routing system."""
        try:
            # Parse query parameters from path
            path, query_params = self._parse_query_params(self.path)

            # Get POST data
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                post_fields = urllib.parse.parse_qs(post_data.decode("UTF-8"))

                # Merge POST fields into query params
                for key, value in post_fields.items():
                    # Convert list to single value
                    single_value = value[0] if isinstance(value, list) and len(value) > 0 else ""
                    query_params[key] = single_value

            logger.debug(f"POST {path} with params: {query_params}")

            # Use new routing system for POST requests
            state = app_state.get_state()
            if state.page_handler is None:
                raise RuntimeError("Application not initialized")

            content = state.page_handler.handle_request(
                path, method="POST", query_params=query_params
            )

            # Check if it's a redirect (search typically redirects)
            if isinstance(content, str):
                # It's a redirect URL
                self.send_response(302)
                self.send_header("Location", content)
                self.end_headers()
            else:
                # Normal response
                self._send_response(content)

        except Exception as e:
            logger.exception(f"Error handling POST request {self.path}")
            self._handle_error(e)

    def _handle_error(self, error: Exception) -> None:
        """
        Handle errors by sending appropriate error response.

        Args:
            error: The exception that occurred
        """
        try:
            state = app_state.get_state()
            debug = state.get_setting("main", "debug", "false").lower() == "true"
            content = handle_exception(error, None, [], {}, debug=debug)
            self._send_response(content)
        except Exception as send_error:
            logger.error(f"Failed to send error response: {send_error}")
            # Last resort: send basic error
            try:
                self.send_error(500, "Internal Server Error")
            except:
                pass

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger instead of stderr."""
        logger.info(f"{self.address_string()} - {format % args}")


def start_server() -> bool:
    """
    Start the MultiChain Explorer web server.

    Returns:
        True if server started and stopped gracefully, False on error
    """
    # Configure logging
    state = app_state.get_state()
    log_level = logging.INFO
    if state.get_setting("main", "debug", "false").lower() == "true":
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("explorer.log"), logging.StreamHandler()],
    )

    logger.info("Starting MultiChain Explorer with modern architecture...")

    # Initialize application (single instance, modern approach)
    app = get_app()
    state.page_handler = app

    # Setup display names for chains
    _setup_chain_display_names()

    # Get server configuration
    host_name = state.get_setting("main", "host", "localhost")
    server_port = int(state.get_setting("main", "port", 8000))

    # Start HTTP server
    try:
        web_server = HTTPServer((host_name, server_port), ExplorerHTTPHandler)
        logger.info(f"Server started at http://{host_name}:{server_port}")
        logger.info(f"Serving {app_state.get_chain_count()} blockchain(s)")
        logger.info("Press Ctrl+C to stop the server")
    except Exception as e:
        message = f"Failed to start web server: {e}"
        utils.log_error(message)
        logger.error(message)
        print(message)
        return False

    try:
        web_server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")

    web_server.server_close()
    utils.log_write("Web server stopped")
    logger.info("Web server stopped gracefully")

    return True


def _setup_chain_display_names() -> None:
    """
    Setup display names for chains to handle duplicates and reserved names.

    This function ensures that each chain has a unique path-name and
    appropriate display-name, handling edge cases like:
    - Reserved path names (chains, search, notfound, chain)
    - Duplicate path names from different chains
    """
    state = app_state.get_state()

    if not state.chains:
        logger.warning("No chains configured")
        return

    reserved_names = ["chains", "search", "notfound", "chain"]

    for i, chain in enumerate(state.chains):
        # Set default display name (escaped for HTML safety)
        chain.config["display-name"] = escape(chain.config["name"])

        # Handle reserved path names
        if chain.config["path-name"] in reserved_names:
            original_name = chain.config["path-name"]
            chain.config[
                "path-name"
            ] = f"{chain.config['path-name']}-{chain.config['path-ini-name']}"
            chain.config[
                "display-name"
            ] = f"{escape(chain.config['name'])} ({escape(chain.config['ini-name'])})"
            logger.info(
                f"Chain '{original_name}' renamed to '{chain.config['path-name']}' "
                f"(reserved name)"
            )
            continue

        # Handle duplicate path names
        for j in range(i):
            if chain.config["path-name"] == state.chains[j].config["path-name"]:
                original_name = chain.config["path-name"]
                chain.config[
                    "path-name"
                ] = f"{chain.config['path-name']}-{chain.config['path-ini-name']}"
                chain.config[
                    "display-name"
                ] = f"{escape(chain.config['name'])} ({escape(chain.config['ini-name'])})"
                logger.info(
                    f"Chain '{original_name}' renamed to '{chain.config['path-name']}' "
                    f"(duplicate name)"
                )
                break

    # Log all configured chains
    logger.info("Configured chains:")
    for chain in state.chains:
        logger.info(f"  - {chain.config['display-name']} -> /{chain.config['path-name']}")
