"""
MultiChain Explorer 2 - Test Suite
Pytest configuration and fixtures
"""

import asyncio
import inspect
import json
from typing import Any, Dict, Optional
from unittest.mock import Mock, patch, AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Match

from exceptions import ChainNotFoundError


@pytest.fixture
def mock_chain_config():
    """Returns mock chain configuration."""
    return {
        "name": "test-chain",  # Required by MCEChain.__init__
        "host": "localhost",
        "port": "8000",
        "path-name": "test-chain",
        "display-name": "Test Chain",
        "rpc": "default-rpc-port",
        "rpcuser": "test_user",
        "rpcpassword": "test_password",
    }


@pytest.fixture
def setup_app_state():
    """Initialize app_state settings before each test."""
    import app_state

    # Set up the minimal settings needed
    app_state.get_state().settings = {
        "main": {
            "host": "0.0.0.0",
            "port": 2750,
            "base": "/",
            "template": "default",
        }
    }
    yield
    # Clean up after test
    app_state.get_state().settings = {}
    app_state.get_state().chains = []


@pytest.fixture
def mock_block_response():
    """Mock getblock RPC response"""
    return {
        "result": {
            "hash": "00000000000000000000000000000000000000000000000000000000deadbeef",
            "confirmations": 10,
            "size": 285,
            "height": 100,
            "version": 20000002,
            "merkleroot": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "miner": "1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "time": 1698764800,
            "nonce": 0,
            "bits": "207fffff",
            "difficulty": 5.96046447753906e-8,
            "previousblockhash": "00000000000000000000000000000000000000000000000000000000deadbeee",
            "nextblockhash": "00000000000000000000000000000000000000000000000000000000deadbef0",
            "tx": [
                "1111111111111111111111111111111111111111111111111111111111111111",
                "2222222222222222222222222222222222222222222222222222222222222222",
            ],
        },
        "error": None,
        "id": 1,
    }


@pytest.fixture
def mock_transaction_response():
    """Mock getrawtransaction RPC response"""
    return {
        "result": {
            "txid": "1111111111111111111111111111111111111111111111111111111111111111",
            "version": 1,
            "locktime": 0,
            "vin": [
                {
                    "txid": "0000000000000000000000000000000000000000000000000000000000000000",
                    "vout": 0,
                    "scriptSig": {"asm": "COINBASE", "hex": ""},
                    "sequence": 4294967295,
                    "addresses": [],
                    "tags": ["coinbase"],
                }
            ],
            "vout": [
                {
                    "value": 0.0,
                    "n": 0,
                    "scriptPubKey": {
                        "asm": "OP_RETURN 1234",
                        "hex": "6a021234",
                        "type": "nulldata",
                        "addresses": [],
                    },
                    "assets": [],
                    "permissions": [],
                    "items": [],
                    "data": [],
                    "tags": [],
                    "redeem": None,  # Add missing field
                }
            ],
            "confirmations": 10,
            "blocktime": 1698764800,
            "blockheight": 100,
            "assets": [],
            "tags": ["coinbase"],
        },
        "error": None,
        "id": 2,
    }


@pytest.fixture
def mock_chain_totals_response():
    """Mock getchaintotals RPC response"""
    return {
        "result": {
            "blocks": 1000,
            "transactions": 5000,
            "assets": 10,
            "streams": 5,
            "addresses": 50,
            "peers": 3,
            "rewards": 1000000.0,
        },
        "error": None,
        "id": 3,
    }


@pytest.fixture
def mock_asset_response():
    """Mock listassets RPC response"""
    return {
        "result": [
            {
                "name": "TestAsset",
                "issuetxid": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "assetref": "10-265-12345",
                "multiple": 1,
                "units": 1.0,
                "open": True,
                "restrict": {},
                "issueqty": 1000.0,
                "issuecount": 1,
                "subscribed": True,
                "synchronized": True,
                "transactions": 10,
                "confirmed": 10,
                "details": {},  # Add missing field
                "issues": [
                    {
                        "txid": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        "qty": 1000.0,
                        "raw": 100000,
                        "details": {},
                        "issuers": ["1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"],
                    }
                ],
            }
        ],
        "error": None,
        "id": 4,
    }


@pytest.fixture
def mock_stream_response():
    """Mock liststreams RPC response"""
    return {
        "result": [
            {
                "name": "TestStream",
                "createtxid": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "streamref": "20-265-54321",
                "open": True,
                "restrict": {"write": False},
                "details": {},
                "subscribed": True,
                "synchronized": True,
                "items": 100,
                "confirmed": 100,
                "keys": 50,
                "publishers": 10,
                "creators": ["1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"],
            }
        ],
        "error": None,
        "id": 5,
    }


@pytest.fixture
def mock_rpc_error_response():
    """Mock RPC error response"""
    return {
        "result": None,
        "error": "Error -5: Block not found",
        "id": 99,
    }


@pytest.fixture
def mock_connection_error_response():
    """Mock connection error response"""
    return {
        "result": None,
        "error": "MultiChain is not running: Connection refused",
        "connection-error": True,
    }


class MockChain:
    """Mock MCEChain object for testing"""

    def __init__(self, config=None):
        if config is None:
            config = {
                "name": "test-chain",
                "path-name": "test-chain",
                "display-name": "Test Chain",
                "multichain-url": "http://127.0.0.1:8570",  # Add RPC URL
                "multichain-headers": {  # Add RPC headers
                    "Content-Type": "application/json",
                    "Connection": "close",
                    "Authorization": "Basic dGVzdDp0ZXN0",
                },
            }
        self.config = config
        self.name = config.get(
            "name", "test-chain"
        )  # Add name attribute for compatibility
        self.responses = {}

    def request(self, method: str, params: Optional[list] = None) -> Dict[str, Any]:
        """Mock RPC request"""
        if method in self.responses:
            return self.responses[method]

        # Default responses for common methods
        defaults = {
            "getblockcount": {"result": 1000, "error": None},
            "getblockhash": {
                "result": "00000000000000000000000000000000000000000000000000000000deadbeef",
                "error": None,
            },
            "getinfo": {
                "result": {
                    "version": "2.2.0",
                    "nodeaddress": "test-chain@127.0.0.1:8571",
                    "burnaddress": "1XXXXXXXXXXXXXXXXXXXXXXXXXXXXburnXXX",
                    "balance": 0.0,
                    "walletdbversion": 3,
                    "reindex": False,
                    "blocks": 1000,
                    "timeoffset": 0,
                    "connections": 3,
                    "proxy": "",
                    "difficulty": 5.96046447753906e-8,
                    "testnet": False,
                    "keypoololdest": 1698764800,
                    "paytxfee": 0.0,
                    "relayfee": 0.0,
                    "errors": "",
                },
                "error": None,
            },
        }

        return defaults.get(
            method, {"result": None, "error": f"Unknown method: {method}"}
        )

    def set_response(self, method: str, response: Dict[str, Any]):
        """Set a custom response for a method"""
        self.responses[method] = response


@pytest.fixture
def mock_chain():
    """Provide a mock chain instance"""
    return MockChain()


@pytest.fixture
def mock_rpc_calls(mock_chain):
    """
    Patch httpx.AsyncClient to use MockChain.

    Since BlockchainService creates the client in __init__, we patch the
    AsyncClient constructor to return a mock that routes requests through MockChain.
    """
    with patch("services.blockchain_service.httpx.AsyncClient") as MockClientClass:
        # Create an AsyncMock for the client
        mock_client = AsyncMock()

        # The constructor now returns the client directly (no context manager)
        MockClientClass.return_value = mock_client

        # Define mock post behavior
        async def mock_post(url, json=None, **kwargs):
            method = json.get("method")
            val_params = json.get("params", []) if json else []

            # Get response from mock chain logic (which is sync, but that's fine)
            result_data = mock_chain.request(method, val_params)

            # Mock HTTP response
            resp = Mock()
            resp.status_code = 200
            resp.json.return_value = result_data
            resp.raise_for_status = Mock()
            return resp

        mock_client.post.side_effect = mock_post

        yield mock_chain


@pytest.fixture
def app_mock_chain():
    """Mock chain config used by FastAPI router and API tests."""
    chain = Mock()
    chain.name = "test-chain"
    chain.path_name = "test-chain"
    chain.display_name = "Test Chain"
    chain.multichain_url = "http://localhost:8570"
    chain.multichain_headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic dGVzdDp0ZXN0",
    }
    chain.config = {
        "name": "test-chain",
        "path-name": "test-chain",
        "display-name": "Test Chain",
        "multichain-url": chain.multichain_url,
        "multichain-headers": chain.multichain_headers,
    }
    return chain


@pytest.fixture
def app_mock_blockchain_service():
    """Mock blockchain service used by FastAPI router and API tests."""
    service = Mock()

    block = {
        "hash": "blockhash_new",
        "height": 999,
        "time": 1700000000,
        "tx": ["tx1"],
        "nTx": 1,
        "size": 100,
        "version": 1,
        "confirmations": 1,
        "merkleroot": "root",
        "miner": "1ABC123",
    }
    tx = {
        "txid": "tx1",
        "version": 1,
        "locktime": 0,
        "vin": [],
        "vout": [],
        "confirmations": 1,
        "time": 1700000000,
        "size": 250,
        "hex": "010000...",
        "blockhash": "blockhash_new",
        "blockheight": 999,
    }

    service.get_blockchain_info = AsyncMock(
        return_value={
            "blocks": 1000,
            "headers": 1000,
            "bestblockhash": "abc123",
            "difficulty": 1.0,
            "chainwork": "0000",
        }
    )
    service.list_blocks = AsyncMock(
        return_value=[
            block,
            {
                **block,
                "hash": "blockhash_old",
                "height": 998,
                "time": 1690000000,
                "tx": ["tx2", "tx3"],
                "nTx": 2,
                "confirmations": 2,
            },
        ]
    )
    service.get_block_by_height = AsyncMock(return_value=block)
    service.get_block_by_hash = AsyncMock(return_value=block)
    service.get_block_hash = AsyncMock(return_value="blockhash_new")
    service.get_block = AsyncMock(return_value=block)
    service.get_transaction = AsyncMock(return_value=tx)

    async def mock_call(method, params=None):
        if method == "validateaddress":
            address = params[0] if params else ""
            return {"address": address, "isvalid": True, "ismine": False}
        if method == "listaddresses":
            return []
        if method == "listpermissions":
            return []
        if method == "listaddresstransactions":
            return []
        if method == "listassets":
            if params and params[0] != "*":
                return [
                    {
                        "name": "asset1",
                        "assetref": "1-2-3",
                        "multiple": 1,
                        "units": 0.1,
                        "open": True,
                        "issues": [],
                    }
                ]
            return [
                {
                    "name": "asset1",
                    "assetref": "1-2-3",
                    "multiple": 1,
                    "units": 0.1,
                    "open": True,
                    "issues": [],
                },
                {
                    "name": "assetA",
                    "assetref": "2-3-4",
                    "multiple": 1,
                    "units": 1.0,
                    "open": False,
                    "issues": [],
                },
            ]
        if method == "listassetholders":
            return []
        if method == "listassettransactions":
            return [tx]
        if method == "liststreams":
            if params and params[0] != "*":
                stream_name = params[0]
                return [
                    {
                        "name": stream_name,
                        "streamref": "5-6-7",
                        "createtxid": "tx_str",
                        "items": 10,
                    }
                ]
            return [
                {
                    "name": "stream1",
                    "streamref": "5-6-7",
                    "createtxid": "tx_str",
                    "items": 10,
                }
            ]
        if method == "liststreamitems":
            return [
                {
                    "publishers": ["pub1"],
                    "key": "key1",
                    "data": "hexdata",
                    "confirmations": 1,
                    "blocktime": 1000,
                    "txid": "tx_item",
                }
            ]
        if method in {
            "liststreamkeys",
            "liststreampublishers",
            "liststreamkeyitems",
            "liststreampublisheritems",
            "explorerlistaddressstreams",
        }:
            return []
        return []

    async def mock_get_asset(asset_ref):
        assets = await service.call("listassets", [asset_ref, True])
        return assets[0] if assets else None

    async def mock_get_stream(stream_ref):
        streams = await service.call("liststreams", [stream_ref, True])
        return streams[0] if streams else None

    async def mock_get_all_assets():
        return await service.call("listassets", ["*", True])

    async def mock_get_asset_holders(asset_ref):
        return await service.call("listassetholders", [asset_ref])

    async def mock_get_all_streams():
        return await service.call("liststreams", ["*", True])

    async def mock_get_all_addresses():
        return await service.call("listaddresses", ["*", False])

    async def mock_get_recent_blocks(start_height, count=10):
        return await service.list_blocks(start_height, count)

    async def mock_get_mining_info():
        return await service.call("getmininginfo")

    async def mock_get_network_hashrate():
        return await service.call("getnetworkhashps")

    async def mock_get_recent_transaction_summaries(
        page=1,
        count=20,
        *,
        block_window=50,
        max_transactions=200,
    ):
        block_count = (await service.get_blockchain_info()).get("blocks", 0)
        latest_height = max(block_count - 1, -1)
        transactions = []

        for height in range(latest_height, max(latest_height - block_window, -1), -1):
            block = await service.get_block_by_height(height)
            if not block:
                continue
            block_height = block.get("height", height)
            confirmations = block_count - block_height
            for txid in block.get("tx", []):
                if len(transactions) >= max_transactions:
                    break
                transactions.append(
                    {
                        "txid": txid,
                        "blockheight": block_height,
                        "confirmations": confirmations,
                        "time": block.get("time"),
                    }
                )
            if len(transactions) >= max_transactions:
                break

        start = max((page - 1) * count, 0)
        end = start + count
        return {
            "transactions": transactions[start:end],
            "total": len(transactions),
            "latest_height": latest_height,
            "scanned_block_count": min(block_count, block_window),
            "page": page,
            "count": count,
            "is_capped": len(transactions) >= max_transactions,
            "max_transactions": max_transactions,
        }

    async def mock_count_rpc_list_results(method, *leading_params, fetch_limit=100000):
        results = await service.call(
            method,
            [*leading_params, False, fetch_limit, 0],
        )
        return len(results) if results else 0

    async def mock_count_address_transactions(address, fetch_limit=100000):
        results = await service.call(
            "listaddresstransactions",
            [address, fetch_limit, 0, False],
        )
        return len(results) if results else 0

    async def mock_count_address_streams(address, fetch_limit=100000):
        results = await service.call(
            "explorerlistaddressstreams",
            [address, True, fetch_limit, 0],
        )
        return len(results) if results else 0

    async def mock_count_asset_transactions(asset_ref, fetch_limit=100000):
        return await mock_count_rpc_list_results(
            "listassettransactions",
            asset_ref,
            fetch_limit=fetch_limit,
        )

    async def mock_count_stream_items(stream_ref, fetch_limit=100000):
        return await mock_count_rpc_list_results(
            "liststreamitems",
            stream_ref,
            fetch_limit=fetch_limit,
        )

    async def mock_count_stream_key_items(stream_ref, key, fetch_limit=100000):
        return await mock_count_rpc_list_results(
            "liststreamkeyitems",
            stream_ref,
            key,
            fetch_limit=fetch_limit,
        )

    async def mock_count_stream_publisher_items(
        stream_ref, publisher, fetch_limit=100000
    ):
        return await mock_count_rpc_list_results(
            "liststreampublisheritems",
            stream_ref,
            publisher,
            fetch_limit=fetch_limit,
        )

    async def mock_get_all_stream_keys(stream_ref, fetch_limit=1000):
        return await service.call(
            "liststreamkeys",
            [stream_ref, "*", False, fetch_limit, 0],
        )

    async def mock_get_all_stream_publishers(stream_ref, fetch_limit=1000):
        return await service.call(
            "liststreampublishers",
            [stream_ref, "*", False, fetch_limit, 0],
        )

    async def mock_get_asset_holder_transactions(asset_ref, address, fetch_limit=1000):
        transactions = await service.call(
            "listaddresstransactions",
            [address, fetch_limit, 0, True],
        )
        if not transactions:
            return []

        def output_matches_asset(output):
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

        return [
            tx
            for tx in transactions
            if any(output_matches_asset(output) for output in tx.get("vout", []))
        ]

    service.call = AsyncMock(side_effect=mock_call)
    service.get_asset = AsyncMock(side_effect=mock_get_asset)
    service.get_stream = AsyncMock(side_effect=mock_get_stream)
    service.get_all_assets = AsyncMock(side_effect=mock_get_all_assets)
    service.get_asset_holders = AsyncMock(side_effect=mock_get_asset_holders)
    service.get_all_streams = AsyncMock(side_effect=mock_get_all_streams)
    service.get_all_addresses = AsyncMock(side_effect=mock_get_all_addresses)
    service.get_recent_blocks = AsyncMock(side_effect=mock_get_recent_blocks)
    service.get_recent_transaction_summaries = AsyncMock(
        side_effect=mock_get_recent_transaction_summaries
    )
    service.get_mining_info = AsyncMock(side_effect=mock_get_mining_info)
    service.get_network_hashrate = AsyncMock(side_effect=mock_get_network_hashrate)
    service.count_rpc_list_results = AsyncMock(side_effect=mock_count_rpc_list_results)
    service.count_address_transactions = AsyncMock(
        side_effect=mock_count_address_transactions
    )
    service.count_address_streams = AsyncMock(side_effect=mock_count_address_streams)
    service.count_asset_transactions = AsyncMock(
        side_effect=mock_count_asset_transactions
    )
    service.count_stream_items = AsyncMock(side_effect=mock_count_stream_items)
    service.count_stream_key_items = AsyncMock(side_effect=mock_count_stream_key_items)
    service.count_stream_publisher_items = AsyncMock(
        side_effect=mock_count_stream_publisher_items
    )
    service.get_all_stream_keys = AsyncMock(side_effect=mock_get_all_stream_keys)
    service.get_all_stream_publishers = AsyncMock(
        side_effect=mock_get_all_stream_publishers
    )
    service.get_asset_holder_transactions = AsyncMock(
        side_effect=mock_get_asset_holder_transactions
    )
    service.get_address_info = AsyncMock(
        return_value={
            "address": "addr1",
            "ismine": False,
            "iswatchonly": False,
            "isscript": False,
            "isvalid": True,
        }
    )
    service.get_address_balances = AsyncMock(
        return_value=[
            {"asset": "asset1", "assetref": "1-2-3", "qty": 100.0, "raw": 10000000000}
        ]
    )
    service.get_address_permissions = AsyncMock(
        return_value=["connect", "send", "receive"]
    )
    service.get_address_transactions = AsyncMock(
        return_value=[{"txid": "tx1", "balance": {}, "addresses": ["addr1"]}]
    )
    service.get_address_summary = AsyncMock(
        return_value={
            "address": "addr1",
            "ismine": False,
            "iswatchonly": False,
            "isscript": False,
            "isvalid": True,
            "balances": [
                {
                    "asset": "asset1",
                    "assetref": "1-2-3",
                    "qty": 100.0,
                    "raw": 10000000000,
                }
            ],
            "permissions": ["connect", "send", "receive"],
        }
    )

    return service


@pytest.fixture
def app_test_state(app_mock_chain):
    """Application state used by FastAPI router and API tests."""
    from app_state import ApplicationState

    state = ApplicationState()
    state.chains = [app_mock_chain]
    state.settings = {
        "main": {"base": "/"},
        "test-chain": {"name": "test-chain"},
    }
    return state


class DirectTestResponse:
    def __init__(self, status_code: int, headers: Dict[str, str], body: bytes):
        self.status_code = status_code
        self.headers = headers
        self._body = body

    @property
    def text(self) -> str:
        return self._body.decode("utf-8")

    def json(self):
        return json.loads(self.text)


class DirectAppClient:
    def __init__(self, app, blockchain_service=None):
        from routers.dependencies import CommonContext, PaginationService, _resolve_base_url

        self.app = app
        self._blockchain_service = blockchain_service
        self._CommonContext = CommonContext
        self._PaginationService = PaginationService
        self._resolve_base_url = _resolve_base_url

    def _build_scope(self, method: str, path: str, query_string: bytes):
        return {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query_string,
            "headers": [],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "root_path": "",
            "app": self.app,
        }

    def _match_route(self, scope):
        for route in self.app.routes:
            match, child_scope = route.matches(scope)
            if match == Match.FULL:
                return route, child_scope
        raise AssertionError(f"No route matched {scope['path']}")

    def _coerce_param(self, raw_value, annotation):
        if annotation is int:
            return int(raw_value)
        if annotation is float:
            return float(raw_value)
        if annotation is bool:
            return raw_value.lower() in {"1", "true", "yes", "on"}
        return raw_value

    async def _render_response(self, response, scope):
        if not hasattr(response, "__call__"):
            response = JSONResponse(content=jsonable_encoder(response))

        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await response(scope, receive, send)

        start = next(msg for msg in messages if msg["type"] == "http.response.start")
        body = b"".join(
            msg.get("body", b"")
            for msg in messages
            if msg["type"] == "http.response.body"
        )
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in start.get("headers", [])
        }
        return DirectTestResponse(start["status"], headers, body)

    async def _handle_exception(self, request: Request, exc: Exception):
        handler = None
        for exc_type in type(exc).__mro__:
            handler = self.app.exception_handlers.get(exc_type)
            if handler:
                break

        if handler:
            response = await handler(request, exc)
            return await self._render_response(response, request.scope)

        if isinstance(exc, HTTPException):
            if request.url.path.startswith("/api/"):
                response = JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                )
            else:
                response = self.app.state.templates.TemplateResponse(
                    name="pages/error.html",
                    context={
                        "request": request,
                        "title": "Error",
                        "status_code": exc.status_code,
                        "error_title": "Error",
                        "error_message": str(exc.detail),
                        "base_url": self._resolve_base_url(self.app.state.config),
                    },
                    status_code=exc.status_code,
                )
            return await self._render_response(response, request.scope)

        raise exc

    async def _request(self, method: str, url: str, **kwargs):
        follow_redirects = kwargs.pop("follow_redirects", True)
        params = kwargs.pop("params", None)
        if kwargs:
            raise TypeError(f"Unsupported request kwargs: {sorted(kwargs.keys())}")

        parsed = httpx.URL(url)
        if params is not None:
            parsed = parsed.copy_merge_params(params)
        scope = self._build_scope(method, parsed.path, parsed.query)
        route, child_scope = self._match_route(scope)
        path_params = child_scope.get("path_params", {})
        request = Request({**scope, **child_scope})
        state = getattr(self.app.state, "config", None)
        chain_name = path_params.get("chain_name")
        chain = state.get_chain_by_name(chain_name) if chain_name and state else None

        if chain_name and chain is None:
            return await self._handle_exception(
                request,
                ChainNotFoundError(chain_name),
            )

        if isinstance(route, APIRoute):
            signature = inspect.signature(route.endpoint)
            endpoint_kwargs = {}
            for name, parameter in signature.parameters.items():
                if name == "request":
                    endpoint_kwargs[name] = request
                elif name == "state":
                    endpoint_kwargs[name] = state
                elif name == "chain":
                    endpoint_kwargs[name] = chain
                elif name == "service":
                    endpoint_kwargs[name] = self._blockchain_service
                elif name == "pagination":
                    endpoint_kwargs[name] = self._PaginationService()
                elif name == "templates":
                    endpoint_kwargs[name] = self.app.state.templates
                elif name == "context":
                    endpoint_kwargs[name] = self._CommonContext(
                        request=request,
                        chain=chain,
                        state=state,
                    )
                elif name == "query_params":
                    endpoint_kwargs[name] = dict(request.query_params)
                elif name == "base_url":
                    endpoint_kwargs[name] = (
                        self._resolve_base_url(state) if state else "/"
                    )
                elif name in path_params:
                    endpoint_kwargs[name] = self._coerce_param(
                        path_params[name], parameter.annotation
                    )
                elif name in request.query_params:
                    endpoint_kwargs[name] = self._coerce_param(
                        request.query_params[name], parameter.annotation
                    )

            try:
                response = await route.endpoint(**endpoint_kwargs)
            except Exception as exc:
                return await self._handle_exception(request, exc)

            rendered = await self._render_response(response, request.scope)
            if follow_redirects and 300 <= rendered.status_code < 400:
                location = rendered.headers.get("location")
                if location:
                    return await self._request(method, location)
            return rendered

        if hasattr(route, "endpoint"):
            endpoint = route.endpoint
            if inspect.iscoroutinefunction(endpoint):
                response = await endpoint(request)
            else:
                response = endpoint(request)
            rendered = await self._render_response(response, request.scope)
            if follow_redirects and 300 <= rendered.status_code < 400:
                location = rendered.headers.get("location")
                if location:
                    return await self._request(method, location)
            return rendered

        raise AssertionError(f"Unsupported route type for {parsed.path}: {type(route)}")

    def request(self, method: str, url: str, **kwargs):
        return asyncio.run(self._request(method, url, **kwargs))

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)


@pytest.fixture
def direct_client_factory():
    def _factory(app, blockchain_service=None):
        return DirectAppClient(app, blockchain_service)

    return _factory


@pytest.fixture
def api_test_client(app_mock_chain, app_mock_blockchain_service, app_test_state):
    """Shared JSON API client with dependency overrides applied."""
    from main import create_app

    app = create_app()
    app.user_middleware = []
    app.middleware_stack = app.build_middleware_stack()
    app.state.config = app_test_state
    yield DirectAppClient(app, app_mock_blockchain_service)


@pytest.fixture
def html_test_app(app_mock_chain, app_test_state):
    """Shared FastAPI app for HTML router tests without lifespan startup."""
    from main import create_app

    app = create_app()
    app.user_middleware = []
    app.middleware_stack = app.build_middleware_stack()
    app.state.config = app_test_state
    app.state.http_client = Mock()
    app.state.http_client.aclose = AsyncMock()
    app.state.cache_provider = Mock()
    app.state.cache_provider.close = AsyncMock()
    return app


@pytest.fixture
def html_test_client(html_test_app, app_mock_blockchain_service):
    """Shared HTML client using direct route invocation instead of ASGI transport."""
    yield DirectAppClient(html_test_app, app_mock_blockchain_service)
