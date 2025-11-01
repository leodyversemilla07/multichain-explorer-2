"""
Tests for domain models.
"""

from datetime import datetime

import pytest

from models import (
    Address,
    AddressBalance,
    Asset,
    Block,
    ChainInfo,
    PeerInfo,
    Permission,
    Stream,
    StreamItem,
    Transaction,
    TransactionInput,
    TransactionOutput,
)


class TestBlock:
    """Test Block model."""

    def test_block_creation(self):
        """Test creating a block."""
        block = Block(
            hash="abc123",
            height=100,
            confirmations=5,
            size=1024,
            version=1,
            merkleroot="def456",
            time=1609459200,
        )

        assert block.hash == "abc123"
        assert block.height == 100
        assert block.confirmations == 5

    def test_block_datetime(self):
        """Test block datetime property."""
        block = Block(
            hash="abc123",
            height=100,
            confirmations=5,
            size=1024,
            version=1,
            merkleroot="def456",
            time=1609459200,
        )

        dt = block.datetime
        assert isinstance(dt, datetime)
        assert dt.year == 2021

    def test_genesis_block(self):
        """Test genesis block detection."""
        genesis = Block(
            hash="genesis",
            height=0,
            confirmations=1000,
            size=256,
            version=1,
            merkleroot="root",
            previousblockhash=None,
        )

        assert genesis.is_genesis is True

        regular = Block(
            hash="block2",
            height=1,
            confirmations=999,
            size=256,
            version=1,
            merkleroot="root",
            previousblockhash="genesis",
        )

        assert regular.is_genesis is False

    def test_block_to_dict(self):
        """Test block serialization."""
        block = Block(
            hash="abc123",
            height=100,
            confirmations=5,
            size=1024,
            version=1,
            merkleroot="def456",
        )

        data = block.to_dict()
        assert isinstance(data, dict)
        assert data["hash"] == "abc123"
        assert data["height"] == 100


class TestTransaction:
    """Test Transaction model."""

    def test_transaction_creation(self):
        """Test creating a transaction."""
        tx = Transaction(
            txid="tx123",
            version=1,
            locktime=0,
            confirmations=10,
        )

        assert tx.txid == "tx123"
        assert tx.confirmations == 10

    def test_transaction_confirmed(self):
        """Test transaction confirmation status."""
        confirmed = Transaction(txid="tx1", version=1, locktime=0, confirmations=5)
        unconfirmed = Transaction(txid="tx2", version=1, locktime=0, confirmations=0)

        assert confirmed.is_confirmed is True
        assert unconfirmed.is_confirmed is False

    def test_coinbase_transaction(self):
        """Test coinbase transaction detection."""
        coinbase_input = TransactionInput(txid="0" * 64, vout=0, coinbase="coinbase_data")
        coinbase = Transaction(txid="tx1", version=1, locktime=0, vin=[coinbase_input])

        assert coinbase.is_coinbase is True

        regular_input = TransactionInput(txid="prevtx", vout=0)
        regular = Transaction(txid="tx2", version=1, locktime=0, vin=[regular_input])

        assert regular.is_coinbase is False

    def test_transaction_with_outputs(self):
        """Test transaction with outputs."""
        output = TransactionOutput(
            value=10.5,
            n=0,
            scriptPubKey={"type": "pubkeyhash"},
            addresses=["addr1"],
        )

        tx = Transaction(
            txid="tx123",
            version=1,
            locktime=0,
            vout=[output],
        )

        assert len(tx.vout) == 1
        assert tx.vout[0].value == 10.5


class TestTransactionInput:
    """Test TransactionInput model."""

    def test_regular_input(self):
        """Test regular transaction input."""
        inp = TransactionInput(txid="prevtx", vout=1)

        assert inp.txid == "prevtx"
        assert inp.vout == 1
        assert inp.is_coinbase is False

    def test_coinbase_input(self):
        """Test coinbase input."""
        inp = TransactionInput(txid="0" * 64, vout=0, coinbase="reward")

        assert inp.is_coinbase is True


class TestTransactionOutput:
    """Test TransactionOutput model."""

    def test_output_creation(self):
        """Test creating an output."""
        output = TransactionOutput(
            value=50.0,
            n=0,
            scriptPubKey={"type": "pubkeyhash"},
            addresses=["addr1", "addr2"],
        )

        assert output.value == 50.0
        assert output.n == 0
        assert len(output.addresses) == 2

    def test_output_with_assets(self):
        """Test output with assets."""
        output = TransactionOutput(
            value=0.0,
            n=0,
            scriptPubKey={},
            assets=[{"name": "asset1", "qty": 100}],
        )

        assert output.has_assets is True

    def test_output_with_permissions(self):
        """Test output with permissions."""
        output = TransactionOutput(
            value=0.0,
            n=0,
            scriptPubKey={},
            permissions=[{"type": "send"}],
        )

        assert output.has_permissions is True


class TestAddress:
    """Test Address model."""

    def test_address_creation(self):
        """Test creating an address."""
        addr = Address(address="1ABC...XYZ", ismine=True)

        assert addr.address == "1ABC...XYZ"
        assert addr.ismine is True

    def test_address_with_balances(self):
        """Test address with balances."""
        balance = AddressBalance(asset="USD", assetref="123-456-789", qty=100.0, raw=10000)

        addr = Address(
            address="addr1",
            balances=[balance],
        )

        assert addr.has_balances is True
        assert len(addr.balances) == 1


class TestAddressBalance:
    """Test AddressBalance model."""

    def test_balance_creation(self):
        """Test creating a balance."""
        balance = AddressBalance(
            asset="USD",
            assetref="123-456-789",
            qty=100.5,
            raw=10050,
            name="US Dollar",
        )

        assert balance.asset == "USD"
        assert balance.qty == 100.5
        assert balance.name == "US Dollar"


class TestAsset:
    """Test Asset model."""

    def test_asset_creation(self):
        """Test creating an asset."""
        asset = Asset(
            name="USD",
            assetref="123-456-789",
            multiple=100,
            units=0.01,
            open=True,
            issueqty=1000000.0,
        )

        assert asset.name == "USD"
        assert asset.issueqty == 1000000.0

    def test_fungible_asset(self):
        """Test fungible asset detection."""
        fungible = Asset(name="COIN", assetref="ref1", multiple=1, units=1.0, open=True)
        nft = Asset(name="NFT", assetref="ref2", multiple=100, units=0.01, open=False)

        assert fungible.is_fungible is True
        assert nft.is_fungible is False

    def test_open_asset(self):
        """Test open asset detection."""
        open_asset = Asset(name="OPEN", assetref="ref1", multiple=1, units=1.0, open=True)
        closed_asset = Asset(name="CLOSED", assetref="ref2", multiple=1, units=1.0, open=False)

        assert open_asset.is_open is True
        assert closed_asset.is_open is False

    def test_total_supply(self):
        """Test total supply calculation."""
        asset = Asset(
            name="TOKEN",
            assetref="ref1",
            multiple=1,
            units=1.0,
            open=False,
            issueqty=1000000.0,
        )

        assert asset.total_supply == 1000000.0


class TestStream:
    """Test Stream model."""

    def test_stream_creation(self):
        """Test creating a stream."""
        stream = Stream(
            name="log",
            streamref="123-456-789",
            createtxid="txid123",
            open=True,
            items=100,
        )

        assert stream.name == "log"
        assert stream.items == 100

    def test_open_stream(self):
        """Test open stream detection."""
        open_stream = Stream(name="open", streamref="ref1", createtxid="tx1", open=True)
        closed_stream = Stream(name="closed", streamref="ref2", createtxid="tx2", open=False)

        assert open_stream.is_open is True
        assert closed_stream.is_open is False

    def test_stream_has_items(self):
        """Test stream items detection."""
        empty = Stream(name="empty", streamref="ref1", createtxid="tx1", items=0)
        populated = Stream(name="data", streamref="ref2", createtxid="tx2", items=100)

        assert empty.has_items is False
        assert populated.has_items is True


class TestStreamItem:
    """Test StreamItem model."""

    def test_item_creation(self):
        """Test creating a stream item."""
        item = StreamItem(
            publishers=["addr1"],
            key="mykey",
            data={"message": "hello"},
            confirmations=5,
            blocktime=1609459200,
            txid="tx123",
        )

        assert item.key == "mykey"
        assert item.confirmations == 5

    def test_confirmed_item(self):
        """Test item confirmation status."""
        confirmed = StreamItem(
            publishers=["addr1"],
            key="key1",
            data="data1",
            confirmations=5,
            blocktime=1609459200,
            txid="tx1",
        )
        unconfirmed = StreamItem(
            publishers=["addr1"],
            key="key2",
            data="data2",
            confirmations=0,
            blocktime=1609459200,
            txid="tx2",
        )

        assert confirmed.is_confirmed is True
        assert unconfirmed.is_confirmed is False

    def test_item_datetime(self):
        """Test item datetime conversion."""
        item = StreamItem(
            publishers=["addr1"],
            key="key1",
            data="data1",
            confirmations=1,
            blocktime=1609459200,
            txid="tx1",
        )

        dt = item.datetime
        assert isinstance(dt, datetime)


class TestPermission:
    """Test Permission model."""

    def test_permission_creation(self):
        """Test creating a permission."""
        perm = Permission(
            address="addr1",
            type="send",
            startblock=100,
            endblock=None,
        )

        assert perm.address == "addr1"
        assert perm.type == "send"

    def test_active_permission(self):
        """Test active permission detection."""
        active = Permission(address="addr1", type="send", startblock=0, endblock=None)
        expired = Permission(address="addr2", type="receive", startblock=0, endblock=1000)

        assert active.is_active is True
        assert expired.is_active is False

    def test_admin_permission(self):
        """Test admin permission detection."""
        admin = Permission(address="addr1", type="admin", startblock=0)
        regular = Permission(address="addr2", type="send", startblock=0)

        assert admin.is_admin is True
        assert regular.is_admin is False


class TestChainInfo:
    """Test ChainInfo model."""

    def test_chaininfo_creation(self):
        """Test creating chain info."""
        info = ChainInfo(
            chainname="mychain",
            description="Test Chain",
            protocol="multichain",
            blocks=1000,
            headers=1000,
            bestblockhash="hash123",
            difficulty=1.0,
            verificationprogress=1.0,
            chainwork="work123",
        )

        assert info.chainname == "mychain"
        assert info.blocks == 1000

    def test_synced_chain(self):
        """Test synced chain detection."""
        synced = ChainInfo(
            chainname="chain1",
            description="desc",
            protocol="multichain",
            blocks=1000,
            headers=1000,
            bestblockhash="hash",
            difficulty=1.0,
            verificationprogress=1.0,
            chainwork="work",
        )

        not_synced = ChainInfo(
            chainname="chain2",
            description="desc",
            protocol="multichain",
            blocks=900,
            headers=1000,
            bestblockhash="hash",
            difficulty=1.0,
            verificationprogress=0.9,
            chainwork="work",
        )

        assert synced.is_synced is True
        assert not_synced.is_synced is False

    def test_sync_percentage(self):
        """Test sync percentage calculation."""
        info = ChainInfo(
            chainname="chain",
            description="desc",
            protocol="multichain",
            blocks=950,
            headers=1000,
            bestblockhash="hash",
            difficulty=1.0,
            verificationprogress=0.95,
            chainwork="work",
        )

        assert info.sync_percentage == 95.0


class TestPeerInfo:
    """Test PeerInfo model."""

    def test_peer_creation(self):
        """Test creating peer info."""
        peer = PeerInfo(
            id=1,
            addr="192.168.1.1:7447",
            inbound=False,
        )

        assert peer.id == 1
        assert peer.addr == "192.168.1.1:7447"

    def test_inbound_peer(self):
        """Test inbound peer detection."""
        inbound = PeerInfo(id=1, addr="addr1", inbound=True)
        outbound = PeerInfo(id=2, addr="addr2", inbound=False)

        assert inbound.is_inbound is True
        assert outbound.is_inbound is False


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_block_serialization(self):
        """Test block to_dict and from_dict."""
        block = Block(
            hash="abc123",
            height=100,
            confirmations=5,
            size=1024,
            version=1,
            merkleroot="def456",
        )

        data = block.to_dict()
        assert isinstance(data, dict)

        restored = Block.from_dict(data)
        assert restored.hash == block.hash
        assert restored.height == block.height

    def test_transaction_serialization(self):
        """Test transaction serialization."""
        tx = Transaction(
            txid="tx123",
            version=1,
            locktime=0,
            confirmations=10,
        )

        data = tx.to_json()
        assert isinstance(data, dict)
        assert data["txid"] == "tx123"

    def test_asset_serialization(self):
        """Test asset serialization."""
        asset = Asset(
            name="USD",
            assetref="123-456-789",
            multiple=100,
            units=0.01,
            open=True,
        )

        data = asset.to_dict()
        restored = Asset.from_dict(data)

        assert restored.name == asset.name
        assert restored.assetref == asset.assetref
