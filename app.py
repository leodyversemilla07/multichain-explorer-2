#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MultiChain Explorer 2 - Modern Application
Uses new architecture: handlers, services, models, routing
"""

import logging
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import app_state
from handlers.address_handler import AddressHandler
from handlers.asset_handler import AssetHandler
from handlers.block_handler import BlockHandler
from handlers.chain_handler import ChainHandler
from handlers.permission_handler import PermissionHandler
from handlers.stream_handler import StreamHandler
from handlers.transaction_handler import TransactionHandler
from routing import Router, get, route
from services.blockchain_service import BlockchainService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MCEApplication:
    """
    Modern MultiChain Explorer application using new architecture.

    This replaces the old MCEDataHandler with a clean, modular design.
    """

    def __init__(self):
        """Initialize the application with new architecture."""
        self.router = Router()
        self.handlers = {}
        self.services = {}

        # Initialize services
        self._init_services()

        # Initialize handlers
        self._init_handlers()

        # Register routes
        self._register_routes()

        logger.info("MCEApplication initialized with new architecture")

    def _init_services(self):
        """Initialize shared services."""
        # Services will be initialized per-chain as needed
        pass

    def _init_handlers(self):
        """Initialize all handlers."""
        self.handlers = {
            "chain": ChainHandler(),
            "block": BlockHandler(),
            "transaction": TransactionHandler(),
            "address": AddressHandler(),
            "asset": AssetHandler(),
            "stream": StreamHandler(),
            "permission": PermissionHandler(),
        }

    def _register_routes(self):
        """Register all application routes."""

        # Homepage - list all chains
        self.router.add_route("/", self.handle_chains, name="chains")

        # Chain routes
        self.router.add_route("/<chain_name:name>", self.handle_chain_home, name="chain_home")
        self.router.add_route(
            "/<chain_name:name>/chain", self.handle_chain_home, name="chain_dashboard"
        )
        self.router.add_route(
            "/<chain_name:name>/parameters", self.handle_chain_parameters, name="chain_parameters"
        )

        # Block routes
        self.router.add_route("/<chain_name:name>/blocks", self.handle_blocks, name="blocks")
        # Redirect /block to /blocks (common typo/bookmark)
        self.router.add_route(
            "/<chain_name:name>/block", self.handle_block_redirect, name="block_redirect"
        )
        self.router.add_route(
            "/<chain_name:name>/block/<height:int>", self.handle_block, name="block"
        )
        self.router.add_route(
            "/<chain_name:name>/block/<hash:hash>", self.handle_block_by_hash, name="block_by_hash"
        )
        self.router.add_route(
            "/<chain_name:name>/block/<height:int>/transactions",
            self.handle_block_transactions,
            name="block_transactions",
        )

        # Transaction routes
        self.router.add_route(
            "/<chain_name:name>/transactions", self.handle_transactions, name="transactions"
        )
        self.router.add_route(
            "/<chain_name:name>/tx/<txid:hash>", self.handle_transaction, name="transaction"
        )
        self.router.add_route(
            "/<chain_name:name>/tx/<txid:hash>/raw",
            self.handle_raw_transaction,
            name="raw_transaction",
        )
        self.router.add_route(
            "/<chain_name:name>/tx/<txid:hash>/hex",
            self.handle_raw_transaction_hex,
            name="raw_transaction_hex",
        )
        self.router.add_route(
            "/<chain_name:name>/tx/<txid:hash>/output/<n:int>",
            self.handle_tx_output_data,
            name="tx_output_data",
        )

        # Address routes
        self.router.add_route(
            "/<chain_name:name>/addresses", self.handle_addresses, name="addresses"
        )
        self.router.add_route(
            "/<chain_name:name>/address/<address:name>", self.handle_address, name="address"
        )
        self.router.add_route(
            "/<chain_name:name>/address/<address:name>/transactions",
            self.handle_address_transactions,
            name="address_transactions",
        )
        self.router.add_route(
            "/<chain_name:name>/address/<address:name>/assets",
            self.handle_address_assets,
            name="address_assets",
        )
        self.router.add_route(
            "/<chain_name:name>/address/<address:name>/streams",
            self.handle_address_streams,
            name="address_streams",
        )
        self.router.add_route(
            "/<chain_name:name>/address/<address:name>/permissions",
            self.handle_address_permissions,
            name="address_permissions",
        )

        # Asset routes
        self.router.add_route("/<chain_name:name>/assets", self.handle_assets, name="assets")
        self.router.add_route(
            "/<chain_name:name>/asset/<asset_name:name>", self.handle_asset, name="asset"
        )
        self.router.add_route(
            "/<chain_name:name>/asset/<asset_name:name>/holders",
            self.handle_asset_holders,
            name="asset_holders",
        )
        self.router.add_route(
            "/<chain_name:name>/asset/<asset_name:name>/transactions",
            self.handle_asset_transactions,
            name="asset_transactions",
        )
        self.router.add_route(
            "/<chain_name:name>/asset/<asset_name:name>/issues",
            self.handle_asset_issues,
            name="asset_issues",
        )
        self.router.add_route(
            "/<chain_name:name>/asset/<asset_name:name>/permissions",
            self.handle_asset_permissions,
            name="asset_permissions",
        )
        self.router.add_route(
            "/<chain_name:name>/asset/<asset_name:name>/holder/<address:name>/transactions",
            self.handle_holder_transactions,
            name="holder_transactions",
        )

        # Stream routes
        self.router.add_route("/<chain_name:name>/streams", self.handle_streams, name="streams")
        self.router.add_route(
            "/<chain_name:name>/stream/<stream_name:name>", self.handle_stream, name="stream"
        )
        self.router.add_route(
            "/<chain_name:name>/stream/<stream_name:name>/items",
            self.handle_stream_items,
            name="stream_items",
        )
        self.router.add_route(
            "/<chain_name:name>/stream/<stream_name:name>/keys",
            self.handle_stream_keys,
            name="stream_keys",
        )
        self.router.add_route(
            "/<chain_name:name>/stream/<stream_name:name>/publishers",
            self.handle_stream_publishers,
            name="stream_publishers",
        )
        self.router.add_route(
            "/<chain_name:name>/stream/<stream_name:name>/permissions",
            self.handle_stream_permissions,
            name="stream_permissions",
        )
        self.router.add_route(
            "/<chain_name:name>/stream/<stream_name:name>/key/<key:name>",
            self.handle_key_items,
            name="key_items",
        )
        self.router.add_route(
            "/<chain_name:name>/stream/<stream_name:name>/publisher/<publisher:name>",
            self.handle_publisher_items,
            name="publisher_items",
        )

        # Legacy /chain/ prefix routes (for backward compatibility with old templates)
        self.router.add_route(
            "/chain/<chain_name:name>", self.handle_chain_home, name="legacy_chain_home"
        )
        self.router.add_route(
            "/chain/<chain_name:name>/blocks", self.handle_blocks, name="legacy_blocks"
        )
        self.router.add_route(
            "/chain/<chain_name:name>/block/<height:int>", self.handle_block, name="legacy_block"
        )
        self.router.add_route(
            "/chain/<chain_name:name>/block/<hash:hash>",
            self.handle_block_by_hash,
            name="legacy_block_by_hash",
        )
        self.router.add_route(
            "/chain/<chain_name:name>/transactions",
            self.handle_transactions,
            name="legacy_transactions",
        )
        self.router.add_route(
            "/chain/<chain_name:name>/tx/<txid:hash>",
            self.handle_transaction,
            name="legacy_transaction",
        )
        self.router.add_route(
            "/chain/<chain_name:name>/addresses", self.handle_addresses, name="legacy_addresses"
        )
        self.router.add_route(
            "/chain/<chain_name:name>/address/<address:name>",
            self.handle_address,
            name="legacy_address",
        )
        self.router.add_route(
            "/chain/<chain_name:name>/assets", self.handle_assets, name="legacy_assets"
        )
        self.router.add_route(
            "/chain/<chain_name:name>/asset/<asset_name:name>",
            self.handle_asset,
            name="legacy_asset",
        )
        self.router.add_route(
            "/chain/<chain_name:name>/streams", self.handle_streams, name="legacy_streams"
        )
        self.router.add_route(
            "/chain/<chain_name:name>/stream/<stream_name:name>",
            self.handle_stream,
            name="legacy_stream",
        )
        self.router.add_route(
            "/chain/<chain_name:name>/permissions",
            self.handle_permissions,
            name="legacy_permissions",
        )

        # Permission routes
        self.router.add_route(
            "/<chain_name:name>/permissions", self.handle_permissions, name="permissions"
        )
        self.router.add_route(
            "/<chain_name:name>/permissions/global",
            self.handle_global_permissions,
            name="global_permissions",
        )

        # Network/Peers routes
        self.router.add_route("/<chain_name:name>/peers", self.handle_peers, name="peers")
        self.router.add_route("/<chain_name:name>/miners", self.handle_miners, name="miners")

        # Search route
        self.router.add_route(
            "/<chain_name:name>/search", self.handle_search, name="search", methods=["POST"]
        )

        logger.info(f"Registered {len(self.router.routes)} routes")

    def handle_request(
        self, path: str, method: str = "GET", query_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, list, bytes]:
        """
        Handle HTTP request using new routing system.

        Args:
            path: Request path (e.g., '/Procuchain/block/169')
            method: HTTP method (GET, POST, etc.)
            query_params: Query parameters dictionary

        Returns:
            Tuple of (status_code, headers, body_bytes)
        """
        query_params = query_params or {}

        # Match route
        match = self.router.match(path, method)

        if not match:
            return self._handle_404(path)

        route, params = match
        handler_func = route.handler

        try:
            # Call handler with matched parameters
            result = handler_func(**params, query_params=query_params)

            # Handler returns (status, headers, body)
            if isinstance(result, tuple) and len(result) == 3:
                return result
            else:
                logger.error(f"Handler returned invalid format: {type(result)}")
                return self._handle_500("Invalid handler response")

        except Exception as e:
            logger.exception(f"Error handling request {path}: {e}")
            return self._handle_500(str(e))

    def _handle_404(self, path: str = "/") -> Tuple[int, list, bytes]:
        """Handle 404 Not Found."""
        from template_engine import render_template

        try:
            state = app_state.get_state()
            base_url = state.get_setting("main", "base", "/")

            html = render_template(
                "pages/error.html",
                {
                    "title": "Page Not Found",
                    "status_code": 404,
                    "error_title": "Page Not Found",
                    "error_message": "The page you requested could not be found.",
                    "path": path,
                    "base_url": base_url,
                    "debug_mode": False,
                },
            )
            return (404, [("Content-Type", "text/html")], html.encode("utf-8"))
        except Exception as e:
            logger.error(f"Error rendering 404 page: {e}")
            body = b"404 - Page Not Found"
            return (404, [("Content-Type", "text/plain")], body)

    def _handle_500(self, error: str) -> Tuple[int, list, bytes]:
        """Handle 500 Internal Server Error."""
        body = f"500 - Internal Server Error: {error}".encode("utf-8")
        return (500, [("Content-Type", "text/plain")], body)

    # Handler methods that delegate to specialized handlers

    def handle_chains(
        self, chain=None, params=None, nparams=None, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List all chains - supports both old and new calling conventions."""
        # Delegate to ChainHandler
        from handlers.chain_handler import ChainHandler

        handler = ChainHandler()
        return handler.handle_chains(chain, query_params or {})

    def handle_chain_home(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Chain homepage/dashboard."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}")

        return self.handlers["chain"].handle_chain_home(chain, query_params)

    def handle_chain_parameters(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Chain parameters page."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/parameters")

        return self.handlers["chain"].handle_chain_parameters(chain, query_params)

    def handle_blocks(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List blocks."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/blocks")

        return self.handlers["block"].handle_blocks_list(chain, query_params)

    def handle_block_redirect(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Redirect /block to /blocks."""
        # Return a redirect response
        redirect_url = f"/{chain_name}/blocks"
        html = f'<html><head><meta http-equiv="refresh" content="0;url={redirect_url}"></head><body>Redirecting to <a href="{redirect_url}">blocks list</a>...</body></html>'
        return (
            302,
            [("Location", redirect_url), ("Content-Type", "text/html; charset=utf-8")],
            html.encode("utf-8"),
        )

    def handle_block(
        self, chain_name: str, height: int, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show block by height."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/block/{height}")

        return self.handlers["block"].handle_block_detail(chain, height, query_params)

    def handle_block_by_hash(
        self, chain_name: str, hash: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show block by hash."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/block/{hash}")

        return self.handlers["block"].handle_block_by_hash(chain, hash, query_params)

    def handle_block_transactions(
        self, chain_name: str, height: int, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List transactions in a block."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/block/{height}/transactions")

        return self.handlers["block"].handle_block_transactions(chain, height, query_params)

    def handle_transactions(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List transactions."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/transactions")

        return self.handlers["transaction"].handle_transactions_list(chain, query_params)

    def handle_transaction(
        self, chain_name: str, txid: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show transaction detail."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/tx/{txid}")

        return self.handlers["transaction"].handle_transaction_detail(chain, txid, query_params)

    def handle_raw_transaction(
        self, chain_name: str, txid: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show raw transaction data."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/tx/{txid}/raw")

        return self.handlers["transaction"].handle_raw_transaction(chain, txid, query_params)

    def handle_raw_transaction_hex(
        self, chain_name: str, txid: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show raw transaction hex."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/tx/{txid}/hex")

        return self.handlers["transaction"].handle_raw_transaction_hex(chain, txid, query_params)

    def handle_tx_output_data(
        self, chain_name: str, txid: str, n: int, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show transaction output data."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/tx/{txid}/output/{n}")

        return self.handlers["transaction"].handle_tx_output_data(chain, txid, n, query_params)

    def handle_addresses(
        self, chain_name: Optional[str] = None, query_params: Optional[Dict] = None, **kwargs
    ) -> Tuple[int, list, bytes]:
        """List addresses - supports both new routing and legacy calls."""
        query_params = query_params or {}

        # Handle legacy calls with different parameter names
        if not chain_name and "chain" in kwargs:
            chain_name = kwargs["chain"]
        if not query_params and "nparams" in kwargs:
            query_params = kwargs["nparams"] or {}

        if not chain_name:
            return self._handle_404("/addresses")

        # Get chain object
        chain_obj = self._get_chain(chain_name)
        if not chain_obj:
            return self._handle_404(f"/{chain_name}/addresses")

        return self.handlers["address"].handle_addresses_list(chain_obj, query_params)

    def handle_address(
        self, chain_name: str, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show address detail."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/address/{address}")

        return self.handlers["address"].handle_address_detail(chain, address, query_params)

    def handle_address_transactions(
        self, chain_name: str, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show address transactions."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/address/{address}/transactions")

        return self.handlers["address"].handle_address_transactions(chain, address, query_params)

    def handle_address_assets(
        self, chain_name: str, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show address assets."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/address/{address}/assets")

        return self.handlers["address"].handle_address_assets(chain, address, query_params)

    def handle_address_streams(
        self, chain_name: str, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show address streams."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/address/{address}/streams")

        return self.handlers["address"].handle_address_streams(chain, address, query_params)

    def handle_address_permissions(
        self, chain_name: str, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show address permissions."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/address/{address}/permissions")

        return self.handlers["address"].handle_address_permissions(chain, address, query_params)

    def handle_assets(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List assets."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/assets")

        return self.handlers["asset"].handle_assets_list(chain, query_params)

    def handle_asset(
        self, chain_name: str, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show asset detail."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/asset/{asset_name}")

        return self.handlers["asset"].handle_asset_detail(chain, asset_name, query_params)

    def handle_asset_holders(
        self, chain_name: str, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show asset holders."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/asset/{asset_name}/holders")

        return self.handlers["asset"].handle_asset_holders(chain, asset_name, query_params)

    def handle_asset_transactions(
        self, chain_name: str, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show asset transactions."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/asset/{asset_name}/transactions")

        return self.handlers["asset"].handle_asset_transactions(chain, asset_name, query_params)

    def handle_asset_issues(
        self, chain_name: str, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show asset issuance history."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/asset/{asset_name}/issues")

        return self.handlers["asset"].handle_asset_issues(chain, asset_name, query_params)

    def handle_asset_permissions(
        self, chain_name: str, asset_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show asset permissions."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/asset/{asset_name}/permissions")

        return self.handlers["asset"].handle_asset_permissions(chain, asset_name, query_params)

    def handle_holder_transactions(
        self, chain_name: str, asset_name: str, address: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show transactions for a specific asset holder."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(
                f"/{chain_name}/asset/{asset_name}/holder/{address}/transactions"
            )

        return self.handlers["asset"].handle_holder_transactions(
            chain, asset_name, address, query_params
        )

    def handle_streams(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List streams."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/streams")

        return self.handlers["stream"].handle_streams_list(chain, query_params or {})

    def handle_stream(
        self, chain_name: str, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show stream detail."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/stream/{stream_name}")

        return self.handlers["stream"].handle_stream_detail(chain, stream_name, query_params)

    def handle_stream_items(
        self, chain_name: str, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show stream items."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/stream/{stream_name}/items")

        return self.handlers["stream"].handle_stream_items(chain, stream_name, query_params)

    def handle_stream_keys(
        self, chain_name: str, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show stream keys."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/stream/{stream_name}/keys")

        return self.handlers["stream"].handle_stream_keys(chain, stream_name, query_params)

    def handle_stream_publishers(
        self, chain_name: str, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show stream publishers."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/stream/{stream_name}/publishers")

        return self.handlers["stream"].handle_stream_publishers(chain, stream_name, query_params)

    def handle_stream_permissions(
        self, chain_name: str, stream_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show stream permissions."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/stream/{stream_name}/permissions")

        return self.handlers["stream"].handle_stream_permissions(chain, stream_name, query_params)

    def handle_key_items(
        self, chain_name: str, stream_name: str, key: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show items for a specific key in a stream."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/stream/{stream_name}/key/{key}")

        return self.handlers["stream"].handle_key_items(chain, stream_name, key, query_params)

    def handle_publisher_items(
        self, chain_name: str, stream_name: str, publisher: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show items from a specific publisher in a stream."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/stream/{stream_name}/publisher/{publisher}")

        return self.handlers["stream"].handle_publisher_items(
            chain, stream_name, publisher, query_params
        )

    def handle_permissions(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List permissions."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/permissions")

        return self.handlers["permission"].handle_permissions_list(chain, query_params)

    def handle_global_permissions(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List global permissions only."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/permissions/global")

        return self.handlers["permission"].handle_global_permissions(chain, query_params)

    def handle_peers(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """List network peers."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/peers")

        return self.handlers["chain"].handle_peers(chain, query_params)

    def handle_miners(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Show mining statistics."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/miners")

        return self.handlers["chain"].handle_miners(chain, query_params)

    def handle_search(
        self, chain_name: str, query_params: Optional[Dict] = None
    ) -> Tuple[int, list, bytes]:
        """Handle search - delegates to search handler."""
        chain = self._get_chain(chain_name)
        if not chain:
            return self._handle_404(f"/{chain_name}/search")

        # Import search handler
        from handlers.search_handler import SearchHandler

        handler = SearchHandler()
        return handler.handle_search(chain, query_params or {})

    def _get_chain(self, chain_name: str):
        """Get chain object by name."""
        state = app_state.get_state()
        chains = state.chains or []
        for chain in chains:
            if chain.config.get("path-name") == chain_name:
                return chain
        return None

    # Compatibility methods for old server.py routing
    def __getattr__(self, name: str):
        """
        Handle dynamic method calls from old server.py routing.

        Server.py does: getattr(cfg.page_handler, 'handle_xyz')
        This method intercepts those calls and routes to new architecture.
        """
        if name.startswith("handle_"):
            # Return a compatibility wrapper
            def compat_handler(chain=None, params=None, nparams=None, query_params=None, **kwargs):
                """
                Compatibility wrapper for old-style handler calls.

                Old style: handler(chain, params_list, nparams_dict)
                New style: handler(chain_name=str, param1=val, query_params=dict)
                """
                # Handle both calling styles
                if query_params is None:
                    query_params = nparams if nparams else {}
                if params is None:
                    params = []

                # Convert old-style call to new-style
                endpoint = name[7:]  # Remove 'handle_' prefix

                # Map old endpoint names to new handler methods
                endpoint_map = {
                    "chains": self.handle_chains,
                    "chain": self.handle_chain_home,
                    "blocks": self.handle_blocks,
                    "block": self.handle_block,
                    "transactions": self.handle_transactions,
                    "tx": self.handle_transaction,
                    "addresses": self.handle_addresses,
                    "address": self.handle_address,
                    "assets": self.handle_assets,
                    "asset": self.handle_asset,
                    "streams": self.handle_streams,
                    "stream": self.handle_stream,
                    "permissions": self.handle_permissions,
                }

                # Get the appropriate handler
                handler = endpoint_map.get(endpoint)

                if handler:
                    try:
                        # Convert params - chain might be a string (chain_name) or an MCEChain object
                        if chain and hasattr(chain, "config"):
                            # It's an MCEChain object
                            chain_name = chain.config.get("path-name")
                        elif chain and isinstance(chain, str):
                            # It's already a chain name string
                            chain_name = chain
                        else:
                            chain_name = None

                        # Ensure query_params is set
                        if query_params is None:
                            query_params = nparams if nparams else {}

                        # Call new-style handler
                        if endpoint == "chains":
                            return handler(
                                chain=chain,
                                params=params,
                                nparams=nparams,
                                query_params=query_params,
                            )
                        elif endpoint in ["block", "address", "asset", "stream"]:
                            # Detail endpoints - need a parameter (height, address, name, etc.)
                            if params and len(params) > 0:
                                if endpoint == "block":
                                    try:
                                        height = int(params[0])
                                        return handler(
                                            chain_name=chain_name or "",
                                            height=height,
                                            query_params=query_params,
                                        )
                                    except ValueError:
                                        # It's a hash
                                        return self.handle_block_by_hash(
                                            chain_name=chain_name or "",
                                            hash=params[0],
                                            query_params=query_params,
                                        )
                                else:
                                    # For address, asset, stream detail pages
                                    param_names = {
                                        "address": "address",
                                        "asset": "asset_name",
                                        "stream": "stream_name",
                                    }
                                    param_name = param_names.get(endpoint, "name")
                                    return handler(
                                        chain_name=chain_name or "",
                                        **{param_name: params[0]},
                                        query_params=query_params,
                                    )
                        elif endpoint == "tx":
                            if params and len(params) > 0:
                                return self.handle_transaction(
                                    chain_name=chain_name or "",
                                    txid=params[0],
                                    query_params=query_params,
                                )
                        else:
                            # List endpoints (addresses, blocks, transactions, assets, streams, permissions)
                            return handler(chain_name=chain_name or "", query_params=query_params)
                    except Exception as e:
                        import logging

                        logging.getLogger(__name__).error(
                            f"Error in compat handler {endpoint}: {e}"
                        )
                        return self._handle_500(str(e))

                # Endpoint not found
                return self._handle_404(f"/{endpoint}")

            return compat_handler

        # For other attributes, raise AttributeError
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# Global application instance
_app = None


def get_app() -> MCEApplication:
    """Get or create the application instance."""
    global _app
    if _app is None:
        _app = MCEApplication()
    return _app
