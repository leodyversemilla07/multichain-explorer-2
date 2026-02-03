"""
MultiChain Explorer 2 - Test Suite
Pytest configuration and fixtures
"""

import json
from collections import OrderedDict
from typing import Any, Dict, Optional
from unittest.mock import Mock, patch, AsyncMock

import pytest


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
        self.name = config.get("name", "test-chain")  # Add name attribute for compatibility
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

        return defaults.get(method, {"result": None, "error": f"Unknown method: {method}"})

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
    """
    with patch("services.blockchain_service.httpx.AsyncClient") as MockClientClass:
        # Create an AsyncMock for the client
        mock_client = AsyncMock()
        
        # Setup context manager (async with httpx.AsyncClient() as client)
        mock_instance = MockClientClass.return_value
        mock_instance.__aenter__.return_value = mock_client
        mock_instance.__aexit__.return_value = None
        
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