"""
Blockchain service - RPC abstraction layer.

Provides a clean interface to MultiChain RPC calls with error handling,
retry logic, and connection management.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
import httpx

from config import ChainConfig
from exceptions import ChainConnectionError, RPCError, is_rpc_not_found_error
from services.cache_service import cached

logger = logging.getLogger(__name__)

LIST_CACHE_TTL_SECONDS = 10
COUNT_CACHE_TTL_SECONDS = 5
SUMMARY_CACHE_TTL_SECONDS = 15


class BlockchainService:
    """Service for interacting with MultiChain blockchain via RPC."""

    def __init__(
        self,
        chain_config: ChainConfig,
        client: Optional[httpx.AsyncClient] = None,
        max_retries: int = 2,
        retry_base_delay: float = 0.2,
        retry_max_delay: float = 1.0,
    ):
        """
        Initialize blockchain service.

        Args:
            chain_config: Chain configuration with RPC credentials
            client: Optional shared httpx.AsyncClient. When provided, the client
                    is NOT closed by this service (caller manages its lifecycle).
                    When omitted, an internal client is created and closed on close().
            max_retries: Number of retries for transient transport errors.
            retry_base_delay: Initial retry delay (seconds), doubled per attempt.
            retry_max_delay: Maximum retry delay (seconds).
        """
        self.config = chain_config
        self.rpc_url = chain_config.multichain_url
        self.headers = chain_config.multichain_headers
        self.chain_name = chain_config.name
        self._request_id = 0
        self._owns_client = client is None
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._retry_max_delay = retry_max_delay

    async def _post_with_retry(self, payload: Dict[str, Any]) -> httpx.Response:
        """
        Post RPC payload with bounded retry for transient transport failures.
        """
        for attempt in range(self._max_retries + 1):
            try:
                return await self._client.post(
                    self.rpc_url,
                    json=payload,
                    headers=self.headers,
                )
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt >= self._max_retries:
                    raise
                delay = min(
                    self._retry_base_delay * (2**attempt), self._retry_max_delay
                )
                logger.warning(
                    "Transient RPC transport error on %s (attempt %s/%s): %s. Retrying in %.2fs",
                    self.chain_name,
                    attempt + 1,
                    self._max_retries + 1,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)

    async def close(self):
        """Close the underlying HTTP client (only if owned by this service)."""
        if self._owns_client:
            await self._client.aclose()

    async def call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """
        Make an asynchronous RPC call to the blockchain.

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
        start_time = time.perf_counter()

        try:
            response = await self._post_with_retry(payload)

            # Check for HTTP errors (like 401 Unauthorized, 500 Internal Server Error)
            # Note: MultiChain might return 500 for RPC errors, so we parse JSON first if possible
            try:
                data = response.json()
            except json.JSONDecodeError:
                response.raise_for_status()
                data = {}

            if "error" in data and data["error"] is not None:
                # Handle both dict and string error formats
                if isinstance(data["error"], dict):
                    error_msg = data["error"].get("message", "Unknown error")
                    error_code = data["error"].get("code", -1)
                else:
                    # String error (from test mocks or legacy systems)
                    error_msg = str(data["error"])
                    error_code = -1
                logger.error(
                    f"RPC error on {self.chain_name}: {error_code} - {error_msg}"
                )
                raise RPCError(
                    method=method,
                    error_message=error_msg,
                    error_code=error_code,
                )

            result = data.get("result")
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_fn = logger.warning if duration_ms > 500 else logger.debug
            log_fn(
                "rpc_call chain=%s method=%s duration_ms=%.2f status=ok",
                self.chain_name,
                method,
                duration_ms,
            )
            return result

        except httpx.HTTPError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Connection error to {self.chain_name}: {e}")
            logger.warning(
                "rpc_call chain=%s method=%s duration_ms=%.2f status=connection_error",
                self.chain_name,
                method,
                duration_ms,
            )
            raise ChainConnectionError(
                chain_name=self.chain_name,
                details={"error": str(e), "rpc_url": self.rpc_url},
            )
        except json.JSONDecodeError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Invalid JSON response from {self.chain_name}: {e}")
            logger.warning(
                "rpc_call chain=%s method=%s duration_ms=%.2f status=invalid_json",
                self.chain_name,
                method,
                duration_ms,
            )
            raise RPCError(
                method=method,
                error_message=f"Invalid JSON response: {e}",
            )
        except RPCError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "rpc_call chain=%s method=%s duration_ms=%.2f status=rpc_error",
                self.chain_name,
                method,
                duration_ms,
            )
            raise

    @cached(ttl=30, key_prefix="info")
    async def get_info(self) -> Dict[str, Any]:
        """Get blockchain info. Cached for 30 seconds."""
        return await self.call("getinfo")

    async def get_blockchain_info(self) -> Dict[str, Any]:
        """Alias for get_info() for backward compatibility."""
        return await self.get_info()

    @cached(ttl=SUMMARY_CACHE_TTL_SECONDS, key_prefix="mining-info")
    async def get_mining_info(self) -> Dict[str, Any]:
        """Return mining info with a short TTL for dashboard views."""
        info = await self.call("getmininginfo")
        return info or {}

    @cached(ttl=SUMMARY_CACHE_TTL_SECONDS, key_prefix="network-hashrate")
    async def get_network_hashrate(self) -> Any:
        """Return network hashrate with a short TTL for dashboard views."""
        return await self.call("getnetworkhashps")

    @cached(ttl=3600, key_prefix="block")
    async def get_block(self, block_hash_or_height: Any) -> Dict[str, Any]:
        """Get block by hash or height. Cached for 1 hour (blocks are immutable)."""
        return await self.call("getblock", [block_hash_or_height])

    @cached(ttl=3600, key_prefix="blockhash")
    async def get_block_hash(self, height: int) -> str:
        """Get block hash by height. Cached for 1 hour (immutable)."""
        return await self.call("getblockhash", [height])

    @cached(ttl=3600, key_prefix="tx")
    async def get_transaction(self, txid: str, verbose: bool = True) -> Dict[str, Any]:
        """Get transaction by ID. Cached for 1 hour (immutable)."""
        return await self.call("getrawtransaction", [txid, 1 if verbose else 0])

    async def list_blocks(
        self, start_height: int, count: int = 10
    ) -> List[Dict[str, Any]]:
        """List blocks starting from height."""
        return await self.call(
            "listblocks", [f"{start_height}-{start_height + count - 1}"]
        )

    @cached(ttl=LIST_CACHE_TTL_SECONDS, key_prefix="recent-blocks")
    async def get_recent_blocks(
        self,
        start_height: int,
        count: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return a short-lived cached recent block slice for dashboard views."""
        blocks = await self.list_blocks(start_height, count)
        return blocks or []

    async def list_addresses(self, addresses: Optional[List[str]] = None) -> List[Any]:
        """List address information."""
        params = [addresses] if addresses else []
        return await self.call("listaddresses", params)

    @cached(ttl=LIST_CACHE_TTL_SECONDS, key_prefix="addresses-all")
    async def get_all_addresses(self) -> List[Any]:
        """Return the full address list for short-lived summary caching."""
        addresses = await self.call("listaddresses", ["*", False])
        return addresses or []

    async def get_address_balances(self, address: str) -> List[Dict[str, Any]]:
        """Get address asset balances."""
        return await self.call("getaddressbalances", [address, 0, True])

    async def list_assets(
        self, asset_name: Optional[str] = None, verbose: bool = True
    ) -> List[Any]:
        """List assets."""
        params = [] if asset_name is None else [asset_name, verbose]
        return await self.call("listassets", params)

    @cached(ttl=LIST_CACHE_TTL_SECONDS, key_prefix="assets-all")
    async def get_all_assets(self) -> List[Dict[str, Any]]:
        """Return the full asset list for short-lived list-page caching."""
        assets = await self.call("listassets", ["*", True])
        return assets or []

    async def list_streams(
        self, stream_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List streams."""
        params = [] if stream_name is None else [stream_name]
        return await self.call("liststreams", params)

    @cached(ttl=LIST_CACHE_TTL_SECONDS, key_prefix="streams-all")
    async def get_all_streams(self) -> List[Dict[str, Any]]:
        """Return the full stream list for short-lived list-page caching."""
        streams = await self.call("liststreams", ["*", True])
        return streams or []

    async def list_stream_items(
        self,
        stream_identifier: str,
        verbose: bool = True,
        count: int = 10,
        start: int = -10,
    ) -> List[Dict[str, Any]]:
        """List items in a stream."""
        return await self.call(
            "liststreamitems", [stream_identifier, verbose, count, start]
        )

    async def list_stream_keys(self, stream_identifier: str) -> List[Any]:
        """List keys in a stream."""
        return await self.call("liststreamkeys", [stream_identifier])

    async def list_stream_publishers(self, stream_identifier: str) -> List[Any]:
        """List publishers in a stream."""
        return await self.call("liststreampublishers", [stream_identifier])

    async def list_permissions(
        self, permission_type: str, addresses: Optional[List[str]] = None
    ) -> List[Any]:
        """List permissions."""
        params = [permission_type]
        if addresses:
            params.append(",".join(addresses))
        return await self.call("listpermissions", params)

    async def get_address_transactions(
        self, address: str, count: int = 10, skip: int = 0, verbose: bool = True
    ) -> List[Any]:
        """Get transactions for an address."""
        return await self.call(
            "listaddresstransactions", [address, count, skip, verbose]
        )

    async def is_healthy(self) -> bool:
        """
        Check if the blockchain connection is healthy.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            await self.get_info()
            return True
        except (ChainConnectionError, RPCError):
            return False

    # Alias for backward compatibility
    async def rpc(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """Alias for call() method for backward compatibility."""
        return await self.call(method, params)

    async def get_block_by_height(self, height: int) -> Optional[Dict[str, Any]]:
        """Get block by height number."""
        try:
            block_hash = await self.get_block_hash(height)
            return await self.get_block(block_hash)
        except RPCError as exc:
            if is_rpc_not_found_error(exc):
                return None
            raise

    async def get_block_by_hash(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Get block by hash."""
        try:
            return await self.get_block(block_hash)
        except RPCError as exc:
            if is_rpc_not_found_error(exc):
                return None
            raise

    async def get_address_info(self, address: str) -> Dict[str, Any]:
        """Get address information including balance and transactions."""
        balances = await self.get_address_balances(address)
        return {"address": address, "balances": balances}

    async def get_address_permissions(self, address: str) -> List[Any]:
        """Get permissions for an address."""
        return await self.call("listpermissions", ["*", address])

    async def get_asset(self, asset_ref: str) -> Optional[Dict[str, Any]]:
        """Get a single asset by name/reference, returning None when not found."""
        try:
            assets = await self.call("listassets", [asset_ref, True])
        except RPCError as exc:
            if is_rpc_not_found_error(exc):
                return None
            raise
        return assets[0] if assets else None

    async def get_stream(self, stream_ref: str) -> Optional[Dict[str, Any]]:
        """Get a single stream by name/reference, returning None when not found."""
        try:
            streams = await self.call("liststreams", [stream_ref, True])
        except RPCError as exc:
            if is_rpc_not_found_error(exc):
                return None
            raise
        return streams[0] if streams else None

    @cached(ttl=LIST_CACHE_TTL_SECONDS, key_prefix="asset-holders")
    async def get_asset_holders(self, asset_ref: str) -> List[Dict[str, Any]]:
        """Return the full holder list for a given asset with a short TTL."""
        holders = await self.call("listassetholders", [asset_ref])
        return holders or []

    @cached(ttl=COUNT_CACHE_TTL_SECONDS, key_prefix="rpc-list-count")
    async def _count_rpc_list_results_cached(
        self,
        method: str,
        *leading_params: Any,
        fetch_limit: int = 100000,
    ) -> int:
        """Cached bounded-count fallback for RPC list endpoints."""
        results = await self.call(method, [*leading_params, False, fetch_limit, 0])
        return len(results) if results else 0

    async def count_rpc_list_results(
        self,
        method: str,
        *leading_params: Any,
        fetch_limit: int = 100000,
    ) -> int:
        """
        Count paginated RPC list results via a bounded full fetch.

        This is the current compatibility fallback for MultiChain list endpoints
        that do not expose a dedicated count RPC. Centralizing it makes the cost
        visible and keeps the route layer consistent.
        """
        return await self._count_rpc_list_results_cached(
            method,
            *leading_params,
            fetch_limit=fetch_limit,
        )

    @cached(ttl=COUNT_CACHE_TTL_SECONDS, key_prefix="address-tx-count")
    async def _count_address_transactions_cached(
        self,
        address: str,
        fetch_limit: int = 100000,
    ) -> int:
        """Cached count helper for address transactions."""
        results = await self.call(
            "listaddresstransactions",
            [address, fetch_limit, 0, False],
        )
        return len(results) if results else 0

    async def count_address_transactions(
        self,
        address: str,
        fetch_limit: int = 100000,
    ) -> int:
        """Count address transactions using the MultiChain parameter order."""
        return await self._count_address_transactions_cached(
            address,
            fetch_limit=fetch_limit,
        )

    @cached(ttl=COUNT_CACHE_TTL_SECONDS, key_prefix="address-stream-count")
    async def _count_address_streams_cached(
        self,
        address: str,
        fetch_limit: int = 100000,
    ) -> int:
        """Cached count helper for address-associated streams."""
        results = await self.call(
            "explorerlistaddressstreams",
            [address, True, fetch_limit, 0],
        )
        return len(results) if results else 0

    async def count_address_streams(
        self,
        address: str,
        fetch_limit: int = 100000,
    ) -> int:
        """Count address-associated streams using the explorer RPC parameter order."""
        return await self._count_address_streams_cached(
            address,
            fetch_limit=fetch_limit,
        )

    async def count_asset_transactions(
        self,
        asset_ref: str,
        fetch_limit: int = 100000,
    ) -> int:
        """Count transactions involving a specific asset."""
        return await self.count_rpc_list_results(
            "listassettransactions",
            asset_ref,
            fetch_limit=fetch_limit,
        )

    async def count_stream_items(
        self,
        stream_ref: str,
        fetch_limit: int = 100000,
    ) -> int:
        """Count items published to a stream."""
        return await self.count_rpc_list_results(
            "liststreamitems",
            stream_ref,
            fetch_limit=fetch_limit,
        )

    async def count_stream_key_items(
        self,
        stream_ref: str,
        key: str,
        fetch_limit: int = 100000,
    ) -> int:
        """Count items for a specific stream key."""
        return await self.count_rpc_list_results(
            "liststreamkeyitems",
            stream_ref,
            key,
            fetch_limit=fetch_limit,
        )

    async def count_stream_publisher_items(
        self,
        stream_ref: str,
        publisher: str,
        fetch_limit: int = 100000,
    ) -> int:
        """Count items published by a specific stream publisher."""
        return await self.count_rpc_list_results(
            "liststreampublisheritems",
            stream_ref,
            publisher,
            fetch_limit=fetch_limit,
        )

    @cached(ttl=LIST_CACHE_TTL_SECONDS, key_prefix="stream-keys")
    async def get_all_stream_keys(
        self,
        stream_ref: str,
        fetch_limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Return stream keys via the shared bounded full-list fallback."""
        keys = await self.call(
            "liststreamkeys", [stream_ref, "*", False, fetch_limit, 0]
        )
        return keys or []

    @cached(ttl=LIST_CACHE_TTL_SECONDS, key_prefix="stream-publishers")
    async def get_all_stream_publishers(
        self,
        stream_ref: str,
        fetch_limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Return stream publishers via the shared bounded full-list fallback."""
        publishers = await self.call(
            "liststreampublishers",
            [stream_ref, "*", False, fetch_limit, 0],
        )
        return publishers or []

    @staticmethod
    def _output_matches_asset(output: Dict[str, Any], asset_ref: str) -> bool:
        """Match legacy flat asset fields and nested MultiChain asset entries."""
        if output.get("assetref") == asset_ref or output.get("asset") == asset_ref:
            return True

        for asset in output.get("assets", []) or []:
            if (
                asset.get("assetref") == asset_ref
                or asset.get("name") == asset_ref
                or asset.get("asset") == asset_ref
            ):
                return True
        return False

    @cached(ttl=SUMMARY_CACHE_TTL_SECONDS, key_prefix="asset-holder-txs")
    async def get_asset_holder_transactions(
        self,
        asset_ref: str,
        address: str,
        fetch_limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Return address transactions filtered down to those that affect one asset.

        MultiChain does not expose a direct paginated holder+asset query, so this
        remains a bounded full-fetch fallback, centralized and cached here.
        """
        transactions = await self.call(
            "listaddresstransactions",
            [address, fetch_limit, 0, True],
        )
        if not transactions:
            return []

        return [
            tx
            for tx in transactions
            if any(
                self._output_matches_asset(output, asset_ref)
                for output in tx.get("vout", [])
            )
        ]

    async def get_address_summary(self, address: str) -> Dict[str, Any]:
        """
        Get comprehensive address summary in parallel.
        Fetches info, balances, and permissions.
        """
        import asyncio

        # Define tasks
        async def fetch_info():
            return await self.get_address_info(address)

        async def fetch_permissions():
            return await self.get_address_permissions(address)

        # Run in parallel
        results = await asyncio.gather(
            fetch_info(), fetch_permissions(), return_exceptions=True
        )

        info = results[0]
        permissions = results[1]

        if isinstance(info, Exception) or not info:
            # Distinguish missing/invalid addresses from backend failures.
            try:
                val = await self.call("validateaddress", [address])
            except RPCError as exc:
                if is_rpc_not_found_error(exc):
                    info = {}
                else:
                    raise
            except ChainConnectionError:
                raise
            else:
                info = val if val and val.get("isvalid") else {}

            if isinstance(info, Exception):
                raise info

        if isinstance(permissions, Exception):
            raise permissions

        # Merge results
        result = info.copy()
        result["permissions"] = permissions

        return result
