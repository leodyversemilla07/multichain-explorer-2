"""
MultiChain Explorer 2 - Input Validators
Type-safe validation for all request parameters
"""

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, validator


class BlockHeightParams(BaseModel):
    """Validate block height parameter"""

    height: int = Field(..., ge=0, le=999_999_999, description="Block height (0 to 999,999,999)")

    class Config:
        str_strip_whitespace = True


class TransactionParams(BaseModel):
    """Validate transaction ID parameter"""

    txid: str = Field(
        ..., min_length=64, max_length=64, description="Transaction ID (64 hex characters)"
    )

    @field_validator("txid")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        if not re.match(r"^[0-9a-fA-F]{64}$", v):
            raise ValueError("Transaction ID must be 64 hexadecimal characters")
        return v.lower()


class AddressParams(BaseModel):
    """Validate MultiChain address parameter"""

    address: str = Field(..., min_length=26, max_length=35, description="MultiChain address")

    @field_validator("address")
    @classmethod
    def validate_address_format(cls, v: str) -> str:
        # Basic MultiChain address validation (starts with 1 or 3, base58)
        # Allow uppercase A for test addresses
        if not re.match(r"^[13][a-km-zA-HJ-NP-Z0-9]{25,34}$", v):
            raise ValueError("Invalid MultiChain address format")
        return v


class PaginationParams(BaseModel):
    """Validate pagination parameters"""

    size: int = Field(default=20, ge=1, le=500, description="Items per page (1-500)")

    from_: int = Field(default=0, ge=0, alias="from", description="Starting offset (0+)")

    class Config:
        populate_by_name = True


class EntityNameParams(BaseModel):
    """Validate asset/stream name parameter"""

    name: str = Field(..., min_length=1, max_length=32, description="Asset or stream name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Allow alphanumeric, dash, underscore
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Name must contain only letters, numbers, dash, and underscore")
        return v


class SearchParams(BaseModel):
    """Validate search query parameters"""

    search_value: str = Field(..., min_length=1, max_length=128, description="Search query")

    @field_validator("search_value")
    @classmethod
    def sanitize_search(cls, v: str) -> str:
        # Remove dangerous characters
        v = v.strip()
        # Allow hex, alphanumeric, and basic punctuation
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", v):
            raise ValueError("Search query contains invalid characters")
        return v


class AssetReferenceParams(BaseModel):
    """Validate asset reference (assetref) parameter"""

    assetref: str = Field(
        ..., pattern=r"^\d+-\d+-\d+$", description="Asset reference (format: n-n-n)"
    )


class StreamKeyParams(BaseModel):
    """Validate stream key parameter"""

    key: str = Field(..., min_length=1, max_length=256, description="Stream key")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        # URL decode if needed
        from urllib.parse import unquote_plus

        v = unquote_plus(v)

        # Basic sanitization - allow most characters but prevent nulls
        if "\x00" in v:
            raise ValueError("Key contains null characters")

        return v


class PermissionTypeParams(BaseModel):
    """Validate permission type parameter"""

    permission_type: str = Field(..., description="Permission type")

    @field_validator("permission_type")
    @classmethod
    def validate_permission(cls, v: str) -> str:
        valid_permissions = [
            "admin",
            "activate",
            "mine",
            "issue",
            "create",
            "send",
            "receive",
            "write",
            "read",
            "connect",
            "low1",
            "low2",
            "low3",
            "high1",
            "high2",
            "high3",
        ]

        if v.lower() not in valid_permissions:
            raise ValueError(f"Invalid permission type: {v}")

        return v.lower()


# Validation helper functions


def validate_block_height(height: str) -> int:
    """Validate and convert block height parameter"""
    try:
        params = BlockHeightParams(height=int(height))
        return params.height
    except ValueError as e:
        raise ValueError(f"Invalid block height: {e}")


def validate_transaction_id(txid: str) -> str:
    """Validate transaction ID parameter"""
    try:
        params = TransactionParams(txid=txid)
        return params.txid
    except ValueError as e:
        raise ValueError(f"Invalid transaction ID: {e}")


def validate_address(address: str) -> str:
    """Validate MultiChain address parameter"""
    try:
        params = AddressParams(address=address)
        return params.address
    except ValueError as e:
        raise ValueError(f"Invalid address: {e}")


def validate_pagination(nparams: dict) -> PaginationParams:
    """Validate pagination parameters"""
    try:
        return PaginationParams(**nparams)
    except ValueError as e:
        raise ValueError(f"Invalid pagination parameters: {e}")


def validate_entity_name(name: str) -> str:
    """Validate asset or stream name"""
    try:
        params = EntityNameParams(name=name)
        return params.name
    except ValueError as e:
        raise ValueError(f"Invalid entity name: {e}")


# Security helpers


def sanitize_html(text: str) -> str:
    """Sanitize text to prevent XSS"""
    from html import escape

    return escape(str(text), quote=True)


def sanitize_sql(text: str) -> str:
    """Sanitize text to prevent SQL injection"""
    # MultiChain Explorer doesn't use SQL, but keep for safety
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
    for char in dangerous_chars:
        text = text.replace(char, "")
    return text


def validate_numeric_string(value: str, min_val: int = 0, max_val: int = 999999999) -> int:
    """Validate numeric string parameter"""
    try:
        num = int(value)
        if num < min_val or num > max_val:
            raise ValueError(f"Value must be between {min_val} and {max_val}")
        return num
    except ValueError:
        raise ValueError(f"Invalid numeric value: {value}")
