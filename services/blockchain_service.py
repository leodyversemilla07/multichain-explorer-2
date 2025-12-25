"""
Blockchain service - RPC abstraction layer.

Provides a clean interface to MultiChain RPC calls with error handling,
retry logic, and connection management.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from config import ChainConfig
from exceptions import ChainConnectionError, RPCError
from services.cache_service import cached

logger = logging.getLogger(__name__)


class BlockchainService:
    """Service for interacting with MultiChain blockchain via RPC."""

    def __init__(self, chain_config):
        """
        Initialize blockchain service.

        Args:
            chain_config: Chain configuration with RPC credentials (ChainConfig or MCEChain)
        """
        self.config = chain_config

        # Handle both new ChainConfig and old MCEChain objects
        if hasattr(chain_config, "multichain_url"):
            # New ChainConfig object
            self.rpc_url = chain_config.multichain_url
            self.headers = chain_config.multichain_headers
            self.chain_name = chain_config.name
        elif hasattr(chain_config, "config") and isinstance(chain_config.config, dict):
            # Old MCEChain object - get from config dict
            self.rpc_url = chain_config.config.get("multichain-url", "")
            self.headers = chain_config.config.get("multichain-headers", {})
            self.chain_name = chain_config.config.get("name", chain_config.name)
        else:
            raise ValueError("Invalid chain configuration object")

        self._request_id = 0
        # Initialize persistent client for connection pooling
        self.client = httpx.Client(timeout=30.0)

    def close(self):
        """Close the HTTP client."""
        try:
            self.client.close()
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")

    def __del__(self):
        """Destructor to ensure client is closed."""
        self.close()

    def call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """
        Make an RPC call to the blockchain.

        Args:
            method: RPC method name (e.g., 'getinfo', 'getblock')
            params: List of parameters for the RPC method

        Returns:
            The 'result' field from the RPC response

        Raises:
            ChainConnectionError: If connection fails
            RPCError: If RPC returns an error
        """
        if params is None:
            params = []

        self._request_id += 1

        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        # Prepare headers
        headers = {"Content-Type": "application/json"}
        # Use pre-configured headers (works with both old and new config)
        for header_name, header_value in self.headers.items():
            headers[header_name] = header_value

        try:
            response = self.client.post(
                self.rpc_url,
                content=json.dumps(payload).encode("utf-8"),
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()

            if "error" in data and data["error"] is not None:
                # Handle both dict and string error formats
                if isinstance(data["error"], dict):
                    error_msg = data["error"].get("message", "Unknown error")
                    error_code = data["error"].get("code", -1)
                else:
                    # String error (from test mocks or legacy systems)
                    error_msg = str(data["error"])
                    error_code = -1
                logger.error(f"RPC error on {self.chain_name}: {error_code} - {error_msg}")
                raise RPCError(
                    method=method,
                    error_message=error_msg,
                    error_code=error_code,
                )

            return data.get("result")

        except httpx.RequestError as e:
            logger.error(f"Connection error to {self.chain_name}: {e}")
            raise ChainConnectionError(
                chain_name=self.chain_name, details={"error": str(e), "rpc_url": self.rpc_url}
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {self.chain_name}: {e}")
            raise ChainConnectionError(
                chain_name=self.chain_name, details={"error": str(e), "status_code": e.response.status_code}
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from {self.config.name}: {e}")
            raise RPCError(
                method=method,
                error_message=f"Invalid JSON response: {e}",
            )

    @cached(ttl=30, key_prefix="info")
    def get_info(self) -> Dict[str, Any]:
        """Get blockchain info. Cached for 30 seconds."""
        return self.call("getinfo")

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Alias for get_info() for backward compatibility."""
        return self.get_info()

    @cached(ttl=3600, key_prefix="block")
    def get_block(self, block_hash_or_height: Any) -> Dict[str, Any]:
        """Get block by hash or height. Cached for 1 hour (blocks are immutable)."""
        return self.call("getblock", [block_hash_or_height])

    @cached(ttl=3600, key_prefix="blockhash")
    def get_block_hash(self, height: int) -> str:
        """Get block hash by height. Cached for 1 hour (immutable)."""
        return self.call("getblockhash", [height])

    @cached(ttl=3600, key_prefix="tx")
    def get_transaction(self, txid: str, verbose: bool = True) -> Dict[str, Any]:
        """Get transaction by ID. Cached for 1 hour (immutable)."""
        return self.call("getrawtransaction", [txid, 1 if verbose else 0])

    def list_blocks(self, start_height: int, count: int = 10) -> List[Dict[str, Any]]:
        """List blocks starting from height."""
        return self.call("listblocks", [f"{start_height}-{start_height + count - 1}"])

    def list_addresses(self, addresses: Optional[List[str]] = None) -> List[Any]:
        """List address information."""
        params = [addresses] if addresses else []
        return self.call("listaddresses", params)

    def get_address_balances(self, address: str) -> List[Dict[str, Any]]:
        """Get address asset balances."""
        return self.call("getaddressbalances", [address, 0, True])

    def list_assets(self, asset_name: Optional[str] = None, verbose: bool = True) -> List[Any]:
        """List assets."""
        params = [] if asset_name is None else [asset_name, verbose]
        return self.call("listassets", params)

    def list_streams(self, stream_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List streams."""
        params = [] if stream_name is None else [stream_name]
        return self.call("liststreams", params)

    def list_stream_items(
        self,
        stream_identifier: str,
        verbose: bool = True,
        count: int = 10,
        start: int = -10,
    ) -> List[Dict[str, Any]]:
        """List items in a stream."""
        return self.call("liststreamitems", [stream_identifier, verbose, count, start])

    def list_stream_keys(self, stream_identifier: str) -> List[Any]:
        """List keys in a stream."""
        return self.call("liststreamkeys", [stream_identifier])

    def list_stream_publishers(self, stream_identifier: str) -> List[Any]:
        """List publishers in a stream."""
        return self.call("liststreampublishers", [stream_identifier])

    def list_permissions(
        self, permission_type: str, addresses: Optional[List[str]] = None
    ) -> List[Any]:
        """List permissions."""
        params = [permission_type]
        if addresses:
            params.append(",".join(addresses))
        return self.call("listpermissions", params)

    def get_address_transactions(
        self, address: str, count: int = 10, skip: int = 0, verbose: bool = True
    ) -> List[Any]:
        """Get transactions for an address."""
        return self.call("listaddresstransactions", [address, count, skip, verbose])

    def is_healthy(self) -> bool:
        """
        Check if the blockchain connection is healthy.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            self.get_info()
            return True
        except (ChainConnectionError, RPCError):
            return False

    # Alias for backward compatibility
    def rpc(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """Alias for call() method for backward compatibility."""
        return self.call(method, params)

    def get_block_by_height(self, height: int) -> Optional[Dict[str, Any]]:
        """Get block by height number."""
        try:
            block_hash = self.get_block_hash(height)
            return self.get_block(block_hash)
        except (RPCError, ChainConnectionError):
            return None

    def get_block_by_hash(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Get block by hash."""
        try:
            return self.get_block(block_hash)
        except (RPCError, ChainConnectionError):
            return None

    def get_address_info(self, address: str) -> Dict[str, Any]:
        """Get address information including balance and transactions."""
        try:
            balances = self.get_address_balances(address)
            return {"address": address, "balances": balances}
        except (RPCError, ChainConnectionError):
            return {"address": address, "balances": []}

    def get_address_permissions(self, address: str) -> List[Any]:
        """Get permissions for an address."""
        try:
            return self.call("listpermissions", ["*", address])
        except (RPCError, ChainConnectionError):
            return []
