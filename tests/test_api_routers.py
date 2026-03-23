"""Tests for API routers (JSON endpoints)."""

from unittest.mock import AsyncMock
from exceptions import ChainConnectionError, RPCError


class TestApiBlocksRouter:
    """Test API blocks router."""

    def test_api_list_blocks(self, api_test_client):
        """Test GET /api/v1/{chain}/blocks returns JSON list."""
        response = api_test_client.get("/api/v1/test-chain/blocks")
        assert response.status_code == 200, f"Response text: {response.text}"
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_api_list_blocks_supports_legacy_start_fallback(self, api_test_client, app_mock_blockchain_service):
        """Test blocks API accepts legacy start/count pagination inputs."""
        response = api_test_client.get("/api/v1/test-chain/blocks?start=40&count=20")
        assert response.status_code == 200
        app_mock_blockchain_service.list_blocks.assert_awaited_with(940, 20)
        
    def test_api_get_block_by_height(self, api_test_client):
        """Test GET /api/v1/{chain}/blocks/{height}."""
        response = api_test_client.get("/api/v1/test-chain/blocks/999")
        assert response.status_code == 200
        data = response.json()
        assert data["height"] == 999
        assert data["hash"] == "blockhash_new"

    def test_api_get_block_by_hash(self, api_test_client):
        """Test GET /api/v1/{chain}/blocks/{hash}."""
        response = api_test_client.get("/api/v1/test-chain/blocks/0000000000000000000000000000000000000000000000000000000000000000") 
        assert response.status_code == 200
        data = response.json()
        assert data["hash"] == "blockhash_new"

    def test_api_get_block_rejects_invalid_identifier(self, api_test_client):
        """Test block detail rejects malformed identifiers."""
        response = api_test_client.get("/api/v1/test-chain/blocks/not-a-block-id")
        assert response.status_code == 400

    def test_api_get_block_returns_503_on_connection_error(
        self, api_test_client, app_mock_blockchain_service
    ):
        """Test block detail surfaces backend connection failures."""
        app_mock_blockchain_service.get_block_by_height = AsyncMock(
            side_effect=ChainConnectionError("test-chain")
        )

        response = api_test_client.get("/api/v1/test-chain/blocks/999")
        assert response.status_code == 503


class TestApiTransactionsRouter:
    """Test API transactions router."""

    def test_api_get_transaction(self, api_test_client):
        """Test GET /api/v1/{chain}/transactions/{txid}."""
        response = api_test_client.get("/api/v1/test-chain/transactions/tx1")
        assert response.status_code == 200
        data = response.json()
        assert data["txid"] == "tx1"

    def test_api_get_transaction_returns_503_on_connection_error(self, api_test_client, app_mock_blockchain_service):
        """Test transaction endpoint surfaces backend connection failures."""
        app_mock_blockchain_service.get_transaction = AsyncMock(side_effect=ChainConnectionError("test-chain"))

        response = api_test_client.get("/api/v1/test-chain/transactions/tx1")
        assert response.status_code == 503

    def test_api_list_block_transactions(self, api_test_client):
        """Test GET /api/v1/{chain}/blocks/{height}/transactions."""
        response = api_test_client.get("/api/v1/test-chain/blocks/999/transactions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["txid"] == "tx1"

    def test_api_list_block_transactions_returns_503_when_all_tx_fetches_fail(
        self, api_test_client, app_mock_blockchain_service
    ):
        """Test block transaction listing surfaces backend failures when no tx can be loaded."""
        app_mock_blockchain_service.get_transaction = AsyncMock(
            side_effect=ChainConnectionError("test-chain")
        )

        response = api_test_client.get("/api/v1/test-chain/blocks/999/transactions")

        assert response.status_code == 503


class TestApiAddressesRouter:
    """Test API addresses router."""

    def test_api_get_address(self, api_test_client):
        """Test GET /api/v1/{chain}/addresses/{address}."""
        response = api_test_client.get("/api/v1/test-chain/addresses/addr1")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["address"] == "addr1"
        assert len(data["balances"]) == 1
        assert data["balances"][0]["asset"] == "asset1"

    def test_api_get_address_returns_503_on_summary_connection_error(
        self, api_test_client, app_mock_blockchain_service
    ):
        """Test address endpoint surfaces backend summary failures."""
        async def validate_ok(method, params=None):
            if method == "validateaddress":
                return {"isvalid": True, "address": params[0], "ismine": False}
            return None

        app_mock_blockchain_service.call = AsyncMock(side_effect=validate_ok)
        app_mock_blockchain_service.get_address_summary = AsyncMock(
            side_effect=ChainConnectionError("test-chain")
        )

        response = api_test_client.get("/api/v1/test-chain/addresses/addr1")
        assert response.status_code == 503

    def test_api_list_address_transactions(self, api_test_client):
        """Test GET /api/v1/{chain}/addresses/{address}/transactions."""
        response = api_test_client.get("/api/v1/test-chain/addresses/addr1/transactions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["txid"] == "tx1"

    def test_api_list_address_transactions_invalid_address(
        self, api_test_client, app_mock_blockchain_service
    ):
        """Test invalid addresses return 404 instead of an empty list."""
        async def invalid_address_call(method, params=None):
            if method == "validateaddress":
                return {"isvalid": False}
            return None

        app_mock_blockchain_service.call = AsyncMock(side_effect=invalid_address_call)

        response = api_test_client.get("/api/v1/test-chain/addresses/bad-address/transactions")
        assert response.status_code == 404


class TestApiAssetsRouter:
    """Test API assets router."""
    
    def test_api_list_assets(self, api_test_client):
        """Test GET /api/v1/{chain}/assets."""
        response = api_test_client.get("/api/v1/test-chain/assets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        assert data[0]["name"] == "asset1"

    def test_api_list_assets_supports_legacy_start_fallback(self, api_test_client):
        """Test assets API accepts legacy start/count pagination inputs."""
        response = api_test_client.get("/api/v1/test-chain/assets?start=1&count=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "assetA"

    def test_api_get_asset(self, api_test_client):
        """Test GET /api/v1/{chain}/assets/{asset_ref}."""
        response = api_test_client.get("/api/v1/test-chain/assets/asset1")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "asset1"

    def test_api_get_asset_returns_502_on_rpc_error(self, api_test_client, app_mock_blockchain_service):
        """Test asset endpoint surfaces RPC failures instead of returning 500."""
        app_mock_blockchain_service.call = AsyncMock(side_effect=RPCError("listassets", "boom"))

        response = api_test_client.get("/api/v1/test-chain/assets/asset1")
        assert response.status_code == 502
        
    def test_api_list_asset_transactions(self, api_test_client):
        """Test GET /api/v1/{chain}/assets/{asset_ref}/transactions."""
        response = api_test_client.get("/api/v1/test-chain/assets/asset1/transactions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["txid"] == "tx1"

    def test_api_list_asset_transactions_does_not_rehydrate_each_tx(
        self, api_test_client, app_mock_blockchain_service
    ):
        """Test asset transaction listing uses the RPC payload directly."""
        app_mock_blockchain_service.get_transaction = AsyncMock(
            side_effect=AssertionError("should not fetch per-transaction details")
        )

        response = api_test_client.get("/api/v1/test-chain/assets/asset1/transactions")

        assert response.status_code == 200
        assert response.json()[0]["txid"] == "tx1"


class TestApiStreamsRouter:
    """Test API streams router."""
    
    def test_api_list_streams(self, api_test_client):
        """Test GET /api/v1/{chain}/streams."""
        response = api_test_client.get("/api/v1/test-chain/streams")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "stream1"

    def test_api_list_streams_returns_503_on_connection_error(self, api_test_client, app_mock_blockchain_service):
        """Test streams list endpoint surfaces backend connection failures."""
        app_mock_blockchain_service.call = AsyncMock(side_effect=ChainConnectionError("test-chain"))

        response = api_test_client.get("/api/v1/test-chain/streams")
        assert response.status_code == 503
        
    def test_api_get_stream(self, api_test_client):
        """Test GET /api/v1/{chain}/streams/{stream_ref}."""
        response = api_test_client.get("/api/v1/test-chain/streams/stream1")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "stream1"
        
    def test_api_list_stream_items(self, api_test_client):
        """Test GET /api/v1/{chain}/streams/{stream_ref}/items."""
        response = api_test_client.get("/api/v1/test-chain/streams/stream1/items")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["key"] == "key1"


class TestApiSearchRouter:
    """Test API search router."""
    
    def test_api_search_block_height(self, api_test_client):
        """Test search block by height."""
        response = api_test_client.get("/api/v1/test-chain/search", params={"q": "999"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["results"][0]["type"] == "block"
        assert data["results"][0]["id"] == "999"

    def test_api_search_includes_urls_from_shared_search_service(self, api_test_client):
        """Test API search now uses the shared search implementation with canonical URLs."""
        response = api_test_client.get("/api/v1/test-chain/search", params={"q": "asset1"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(result.get("url") == "/test-chain/asset/asset1" for result in data["results"])

    def test_api_search_returns_503_on_backend_failure(self, api_test_client, app_mock_blockchain_service):
        """Test API search surfaces backend failures from the shared search service."""
        app_mock_blockchain_service.call = AsyncMock(side_effect=ChainConnectionError("test-chain"))

        response = api_test_client.get("/api/v1/test-chain/search", params={"q": "asset1"})
        assert response.status_code == 503
