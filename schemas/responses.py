"""
Pydantic Response Models for MultiChain Explorer API.

These models define the standardized JSON structure for API responses,
decoupling the internal representation from the external API contract.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    page: int
    page_count: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int]
    prev_page: Optional[int]
    total_items: Optional[int] = None
    items_per_page: Optional[int] = None


class BaseResponse(BaseModel):
    """Base API response model.

    All response schemas inherit from this. `from_attributes=True` allows
    model_validate() to work on ORM objects or attribute-access objects.
    Skill ref: fastapi-agents > schemas > ConfigDict from_attributes
    """
    model_config = ConfigDict(from_attributes=True)


# --- Block Models ---

class BlockResponse(BaseResponse):
    """Block details response."""
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
    transactions: List[str] = Field(default_factory=list)


# --- Transaction Models ---

class TransactionInput(BaseModel):
    """Transaction input."""
    txid: Optional[str] = None
    vout: Optional[int] = None
    scriptSig: Optional[Dict[str, Any]] = None
    sequence: Optional[int] = None
    coinbase: Optional[str] = None


class TransactionOutput(BaseModel):
    """Transaction output."""
    value: float
    n: int
    scriptPubKey: Dict[str, Any]
    addresses: List[str] = Field(default_factory=list)
    assets: List[Dict[str, Any]] = Field(default_factory=list)
    permissions: List[Dict[str, Any]] = Field(default_factory=list)


class TransactionResponse(BaseResponse):
    """Transaction details response."""
    txid: str
    version: int
    locktime: int
    vin: List[TransactionInput] = Field(default_factory=list)
    vout: List[TransactionOutput] = Field(default_factory=list)
    blockhash: Optional[str] = None
    blockheight: Optional[int] = None
    blocktime: Optional[int] = None
    confirmations: int = 0
    time: Optional[int] = None
    size: Optional[int] = None
    hex: Optional[str] = None


# --- Address Models ---

class AddressBalance(BaseModel):
    """Address asset balance."""
    asset: str
    assetref: str
    qty: float
    raw: int
    name: Optional[str] = None


class AddressResponse(BaseResponse):
    """Address details response."""
    address: str
    ismine: bool = False
    iswatchonly: bool = False
    isscript: bool = False
    pubkey: Optional[str] = None
    iscompressed: Optional[bool] = None
    account: Optional[str] = None
    synchronized: bool = True
    balances: List[AddressBalance] = Field(default_factory=list)


# --- Asset Models ---

class AssetResponse(BaseResponse):
    """Asset details response."""
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
    issuers: List[str] = Field(default_factory=list)


# --- Stream Models ---

class StreamResponse(BaseResponse):
    """Stream details response."""
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


class StreamItemResponse(BaseResponse):
    """Stream item details."""
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


# --- Chain Info Models ---

class ChainInfoResponse(BaseResponse):
    """Blockchain info response."""
    chainname: str
    description: str
    protocol: str
    blocks: int
    headers: int
    bestblockhash: str
    difficulty: float
    verificationprogress: float
    chainwork: str
    nodeaddress: Optional[str] = None
    version: Optional[str] = None
