"""
Domain models for MultiChain Explorer.

Provides type-safe data models for blockchain entities with validation,
serialization, and documentation.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BaseModel:
    """Base class for all domain models."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model from dictionary."""
        return cls(**data)

    def to_json(self) -> Dict[str, Any]:
        """Convert model to JSON-serializable dictionary."""
        return self.to_dict()


@dataclass
class Block(BaseModel):
    """Represents a blockchain block."""

    hash: str
    height: int
    confirmations: int
    size: int
    version: int
    merkleroot: str
    miner: Optional[str] = None
    time: Optional[int] = None
    nonce: Optional[int] = None
    bits: Optional[str] = None
    difficulty: Optional[float] = None
    chainwork: Optional[str] = None
    previousblockhash: Optional[str] = None
    nextblockhash: Optional[str] = None
    tx_count: int = 0
    transactions: List[str] = field(default_factory=list)

    @property
    def datetime(self) -> Optional[datetime]:
        """Get block time as datetime object."""
        if self.time:
            return datetime.fromtimestamp(self.time)
        return None

    @property
    def is_genesis(self) -> bool:
        """Check if this is the genesis block."""
        return self.height == 0 or self.previousblockhash is None


@dataclass
class TransactionInput(BaseModel):
    """Represents a transaction input."""

    txid: str
    vout: int
    scriptSig: Optional[Dict[str, Any]] = None
    sequence: Optional[int] = None
    coinbase: Optional[str] = None

    @property
    def is_coinbase(self) -> bool:
        """Check if this is a coinbase input."""
        return self.coinbase is not None


@dataclass
class TransactionOutput(BaseModel):
    """Represents a transaction output."""

    value: float
    n: int
    scriptPubKey: Dict[str, Any]
    addresses: List[str] = field(default_factory=list)
    assets: List[Dict[str, Any]] = field(default_factory=list)
    permissions: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def has_assets(self) -> bool:
        """Check if output contains assets."""
        return len(self.assets) > 0

    @property
    def has_permissions(self) -> bool:
        """Check if output contains permissions."""
        return len(self.permissions) > 0


@dataclass
class Transaction(BaseModel):
    """Represents a blockchain transaction."""

    txid: str
    version: int
    locktime: int
    vin: List[TransactionInput] = field(default_factory=list)
    vout: List[TransactionOutput] = field(default_factory=list)
    blockhash: Optional[str] = None
    blockheight: Optional[int] = None
    blocktime: Optional[int] = None
    confirmations: int = 0
    time: Optional[int] = None
    size: Optional[int] = None
    hex: Optional[str] = None

    @property
    def is_confirmed(self) -> bool:
        """Check if transaction is confirmed."""
        return self.confirmations > 0

    @property
    def is_coinbase(self) -> bool:
        """Check if this is a coinbase transaction."""
        return len(self.vin) > 0 and self.vin[0].is_coinbase

    @property
    def datetime(self) -> Optional[datetime]:
        """Get transaction time as datetime object."""
        if self.time:
            return datetime.fromtimestamp(self.time)
        return None


@dataclass
class AddressBalance(BaseModel):
    """Represents an asset balance for an address."""

    asset: str
    assetref: str
    qty: float
    raw: int
    name: Optional[str] = None
    issueqty: Optional[float] = None
    units: Optional[float] = None


@dataclass
class Address(BaseModel):
    """Represents a blockchain address."""

    address: str
    ismine: bool = False
    iswatchonly: bool = False
    isscript: bool = False
    pubkey: Optional[str] = None
    iscompressed: Optional[bool] = None
    account: Optional[str] = None
    synchronized: bool = True
    balances: List[AddressBalance] = field(default_factory=list)

    @property
    def has_balances(self) -> bool:
        """Check if address has any balances."""
        return len(self.balances) > 0


@dataclass
class Asset(BaseModel):
    """Represents a blockchain asset."""

    name: str
    assetref: str
    multiple: int
    units: float
    open: bool
    restrict: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None
    issueqty: float = 0.0
    issueraw: int = 0
    subscribed: bool = False
    synchronized: bool = True
    transactions: int = 0
    confirmed: int = 0
    issuers: List[str] = field(default_factory=list)

    @property
    def is_fungible(self) -> bool:
        """Check if asset is fungible."""
        return self.multiple == 1

    @property
    def is_open(self) -> bool:
        """Check if asset is open for additional issuance."""
        return self.open

    @property
    def total_supply(self) -> float:
        """Get total asset supply."""
        return self.issueqty


@dataclass
class StreamItem(BaseModel):
    """Represents an item in a stream."""

    publishers: List[str]
    key: str
    data: Any
    confirmations: int
    blocktime: int
    txid: str
    vout: Optional[int] = None
    offchain: bool = False
    available: bool = True
    size: Optional[int] = None

    @property
    def is_confirmed(self) -> bool:
        """Check if item is confirmed."""
        return self.confirmations > 0

    @property
    def datetime(self) -> datetime:
        """Get item time as datetime object."""
        return datetime.fromtimestamp(self.blocktime)


@dataclass
class Stream(BaseModel):
    """Represents a blockchain stream."""

    name: str
    streamref: str
    createtxid: str
    open: bool = True
    restrict: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None
    subscribed: bool = False
    synchronized: bool = True
    items: int = 0
    confirmed: int = 0
    keys: int = 0
    publishers: int = 0

    @property
    def is_open(self) -> bool:
        """Check if stream is open for writing."""
        return self.open

    @property
    def has_items(self) -> bool:
        """Check if stream has any items."""
        return self.items > 0


@dataclass
class Permission(BaseModel):
    """Represents a blockchain permission."""

    address: str
    type: str
    startblock: int
    endblock: Optional[int] = None
    admins: List[str] = field(default_factory=list)
    pending: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        """Check if permission is currently active."""
        # If endblock is None, permission is permanent
        return self.endblock is None

    @property
    def is_admin(self) -> bool:
        """Check if this is an admin permission."""
        return self.type == "admin"


@dataclass
class ChainInfo(BaseModel):
    """Represents blockchain information."""

    chainname: str
    description: str
    protocol: str
    blocks: int
    headers: int
    bestblockhash: str
    difficulty: float
    verificationprogress: float
    chainwork: str
    setupblocks: Optional[int] = None
    nodeaddress: Optional[str] = None
    incomingpaused: bool = False
    miningpaused: bool = False
    walletversion: Optional[int] = None
    balance: float = 0.0
    walletdbversion: Optional[int] = None
    reindex: bool = False
    blocks_per_day: Optional[float] = None

    @property
    def is_synced(self) -> bool:
        """Check if blockchain is fully synced."""
        return self.blocks == self.headers

    @property
    def sync_percentage(self) -> float:
        """Get sync progress as percentage."""
        return self.verificationprogress * 100


@dataclass
class PeerInfo(BaseModel):
    """Represents a network peer."""

    id: int
    addr: str
    addrlocal: Optional[str] = None
    services: Optional[str] = None
    lastsend: int = 0
    lastrecv: int = 0
    bytessent: int = 0
    bytesrecv: int = 0
    conntime: int = 0
    timeoffset: int = 0
    pingtime: Optional[float] = None
    version: Optional[int] = None
    subver: Optional[str] = None
    inbound: bool = False
    startingheight: int = 0
    banscore: int = 0
    synced_headers: int = 0
    synced_blocks: int = 0
    handshakelocal: Optional[str] = None
    handshake: Optional[str] = None

    @property
    def is_inbound(self) -> bool:
        """Check if this is an inbound connection."""
        return self.inbound
