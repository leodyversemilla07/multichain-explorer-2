# -*- coding: utf-8 -*-

"""
Tests for specialized handler classes.

Tests all handler classes to ensure they work with the new architecture
using BlockchainService instead of MCEDataHandler delegation.
"""

import pytest

from handlers.address_handler import AddressHandler
from handlers.asset_handler import AssetHandler
from handlers.block_handler import BlockHandler
from handlers.chain_handler import ChainHandler
from handlers.permission_handler import PermissionHandler
from handlers.stream_handler import StreamHandler
from handlers.transaction_handler import TransactionHandler


# Block Handler Tests
def test_block_handler_imports():
    """Test BlockHandler can be imported."""
    assert BlockHandler is not None


def test_block_handler_creation():
    """Test BlockHandler can be instantiated."""
    handler = BlockHandler()
    assert handler is not None


def test_block_handler_has_methods():
    """Test BlockHandler has expected methods."""
    handler = BlockHandler()
    assert hasattr(handler, "handle_blocks_list")
    assert hasattr(handler, "handle_block_detail")
    assert hasattr(handler, "handle_block_transactions")


# Transaction Handler Tests
def test_transaction_handler_imports():
    """Test TransactionHandler can be imported."""
    assert TransactionHandler is not None


def test_transaction_handler_creation():
    """Test TransactionHandler can be instantiated."""
    handler = TransactionHandler()
    assert handler is not None


def test_transaction_handler_has_methods():
    """Test TransactionHandler has expected methods."""
    handler = TransactionHandler()
    assert hasattr(handler, "handle_transaction_detail")


# Address Handler Tests
def test_address_handler_imports():
    """Test AddressHandler can be imported."""
    assert AddressHandler is not None


def test_address_handler_creation():
    """Test AddressHandler can be instantiated."""
    handler = AddressHandler()
    assert handler is not None


def test_address_handler_has_methods():
    """Test AddressHandler has expected methods."""
    handler = AddressHandler()
    assert hasattr(handler, "handle_address_detail")
    assert hasattr(handler, "handle_address_transactions")


# Asset Handler Tests
def test_asset_handler_imports():
    """Test AssetHandler can be imported."""
    assert AssetHandler is not None


def test_asset_handler_creation():
    """Test AssetHandler can be instantiated."""
    handler = AssetHandler()
    assert handler is not None


def test_asset_handler_has_methods():
    """Test AssetHandler has expected methods."""
    handler = AssetHandler()
    assert hasattr(handler, "handle_assets_list")
    assert hasattr(handler, "handle_asset_detail")
    assert hasattr(handler, "handle_asset_holders")


# Stream Handler Tests
def test_stream_handler_imports():
    """Test StreamHandler can be imported."""
    assert StreamHandler is not None


def test_stream_handler_creation():
    """Test StreamHandler can be instantiated."""
    handler = StreamHandler()
    assert handler is not None


def test_stream_handler_has_methods():
    """Test StreamHandler has expected methods."""
    handler = StreamHandler()
    assert hasattr(handler, "handle_streams_list")
    assert hasattr(handler, "handle_stream_detail")
    assert hasattr(handler, "handle_stream_items")


# Chain Handler Tests
def test_chain_handler_imports():
    """Test ChainHandler can be imported."""
    assert ChainHandler is not None


def test_chain_handler_creation():
    """Test ChainHandler can be instantiated."""
    handler = ChainHandler()
    assert handler is not None


def test_chain_handler_has_methods():
    """Test ChainHandler has expected methods."""
    handler = ChainHandler()
    assert hasattr(handler, "handle_chains")
    assert hasattr(handler, "handle_chain_home")


# Permission Handler Tests
def test_permission_handler_imports():
    """Test PermissionHandler can be imported."""
    assert PermissionHandler is not None


def test_permission_handler_creation():
    """Test PermissionHandler can be instantiated."""
    handler = PermissionHandler()
    assert handler is not None


def test_permission_handler_has_methods():
    """Test PermissionHandler has expected methods."""
    handler = PermissionHandler()
    assert hasattr(handler, "handle_permissions_list")


# Integration Tests
def test_all_handlers_available_from_package():
    """Test all handlers can be imported from handlers package."""
    from handlers import (
        AddressHandler,
        AssetHandler,
        BaseHandler,
        BlockHandler,
        ChainHandler,
        PermissionHandler,
        StreamHandler,
        TransactionHandler,
    )

    assert BaseHandler is not None
    assert BlockHandler is not None
    assert TransactionHandler is not None
    assert AddressHandler is not None
    assert AssetHandler is not None
    assert StreamHandler is not None
    assert ChainHandler is not None
    assert PermissionHandler is not None


def test_all_handlers_can_be_instantiated():
    """Test all handlers can be instantiated without parameters."""
    from handlers import (
        AddressHandler,
        AssetHandler,
        BlockHandler,
        ChainHandler,
        PermissionHandler,
        StreamHandler,
        TransactionHandler,
    )

    for handler_class in [
        BlockHandler,
        TransactionHandler,
        AddressHandler,
        AssetHandler,
        StreamHandler,
        ChainHandler,
        PermissionHandler,
    ]:
        handler = handler_class()
        assert handler is not None


def test_handler_registry_pattern():
    """Test handler registry pattern (useful for routing)."""
    from handlers import (
        AddressHandler,
        AssetHandler,
        BlockHandler,
        ChainHandler,
        PermissionHandler,
        StreamHandler,
        TransactionHandler,
    )

    # Simulate a handler registry
    handler_registry = {
        "block": BlockHandler(),
        "transaction": TransactionHandler(),
        "address": AddressHandler(),
        "asset": AssetHandler(),
        "stream": StreamHandler(),
        "chain": ChainHandler(),
        "permission": PermissionHandler(),
    }

    # All handlers should be registered
    assert len(handler_registry) == 7
    assert all(handler is not None for handler in handler_registry.values())


def test_handlers_inherit_from_base():
    """Test all handlers inherit from BaseHandler."""
    from handlers import (
        AddressHandler,
        AssetHandler,
        BaseHandler,
        BlockHandler,
        ChainHandler,
        PermissionHandler,
        StreamHandler,
        TransactionHandler,
    )

    for handler_class in [
        BlockHandler,
        TransactionHandler,
        AddressHandler,
        AssetHandler,
        StreamHandler,
        ChainHandler,
        PermissionHandler,
    ]:
        assert issubclass(handler_class, BaseHandler)
