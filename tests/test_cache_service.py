#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for cache service."""

import pytest
import asyncio

from services.cache_service import CacheService, cached, get_cache


@pytest.mark.asyncio
class TestCacheService:
    """Test CacheService class."""

    async def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = CacheService()
        await cache.set("test_key", "test_value", ttl=60)

        result = await cache.get("test_key")
        assert result == "test_value"

    async def test_cache_get_nonexistent(self):
        """Test getting a non-existent key."""
        cache = CacheService()
        result = await cache.get("nonexistent_key")
        assert result is None

    async def test_cache_expiry(self):
        """Test cache entry expiration."""
        cache = CacheService()
        await cache.set("test_key", "test_value", ttl=0.5)

        # Should be available immediately
        result = await cache.get("test_key")
        assert result == "test_value"

        # Wait for expiry
        await asyncio.sleep(0.6)

        # Should be expired
        result = await cache.get("test_key")
        assert result is None

    async def test_cache_no_expiry(self):
        """Test cache entry with no expiry."""
        cache = CacheService()
        await cache.set("test_key", "test_value", ttl=0)

        # Should be available
        result = await cache.get("test_key")
        assert result == "test_value"

    async def test_cache_delete(self):
        """Test cache entry deletion."""
        cache = CacheService()
        await cache.set("test_key", "test_value", ttl=60)

        # Should be available
        result = await cache.get("test_key")
        assert result == "test_value"

        # Delete
        await cache.delete("test_key")

        # Should be gone
        result = await cache.get("test_key")
        assert result is None

    async def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = CacheService()
        await cache.set("key1", "value1", ttl=60)
        await cache.set("key2", "value2", ttl=60)

        # Both should be available
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"

        # Clear
        await cache.clear()

        # Both should be gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    async def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = CacheService()
        await cache.set("expired_key", "value1", ttl=0.1)
        await cache.set("valid_key", "value2", ttl=60)

        # Wait for first key to expire
        await asyncio.sleep(0.2)

        # Cleanup
        removed = await cache.cleanup_expired()
        assert removed == 1

        # Expired key should be gone
        assert await cache.get("expired_key") is None

        # Valid key should still be there
        assert await cache.get("valid_key") == "value2"

    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = CacheService()
        cache.reset_stats()

        # Set some values
        await cache.set("key1", "value1", ttl=60)
        await cache.set("key2", "value2", ttl=60)

        # Get some values (hits)
        await cache.get("key1")
        await cache.get("key2")

        # Get non-existent value (miss)
        await cache.get("key3")

        # Delete a value
        await cache.delete("key1")

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["sets"] == 2
        assert stats["deletes"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == pytest.approx(2 / 3)

    async def test_cache_stats_reset(self):
        """Test resetting cache statistics."""
        cache = CacheService()
        await cache.set("key1", "value1", ttl=60)
        await cache.get("key1")

        # Stats should be non-zero
        stats = cache.get_stats()
        assert stats["hits"] > 0

        # Reset
        cache.reset_stats()

        # Stats should be zero
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["sets"] == 0
        assert stats["deletes"] == 0

    async def test_cached_decorator_basic(self):
        """Test basic cached decorator functionality."""
        # Clean global cache
        cache = get_cache()
        await cache.clear()
        cache.reset_stats()

        call_count = 0

        @cached(ttl=60, key_prefix="test")
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Still 1, not called again

    async def test_cached_decorator_different_args(self):
        """Test cached decorator with different arguments."""
        # Clean global cache
        cache = get_cache()
        await cache.clear()
        cache.reset_stats()

        call_count = 0

        @cached(ttl=60, key_prefix="test")
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Different argument should call function again
        result2 = await expensive_function(10)
        assert result2 == 20
        assert call_count == 2

        # Same as first should use cache
        result3 = await expensive_function(5)
        assert result3 == 10
        assert call_count == 2

    async def test_cached_decorator_with_kwargs(self):
        """Test cached decorator with keyword arguments."""
        # Clean global cache
        cache = get_cache()
        await cache.clear()
        cache.reset_stats()

        call_count = 0

        @cached(ttl=60, key_prefix="test")
        async def expensive_function(x: int, y: int = 1) -> int:
            nonlocal call_count
            call_count += 1
            return x * y

        # First call
        result1 = await expensive_function(5, y=3)
        assert result1 == 15
        assert call_count == 1

        # Same call should use cache
        result2 = await expensive_function(5, y=3)
        assert result2 == 15
        assert call_count == 1

        # Different kwargs should call function
        result3 = await expensive_function(5, y=2)
        assert result3 == 10
        assert call_count == 2

    async def test_cached_decorator_expiry(self):
        """Test cached decorator with expiry."""
        # Clean global cache
        cache = get_cache()
        await cache.clear()
        cache.reset_stats()

        call_count = 0

        @cached(ttl=0.5, key_prefix="test")
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Wait for expiry
        await asyncio.sleep(0.6)

        # Should call function again
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 2

    async def test_cached_decorator_cache_clear(self):
        """Test cache clear method on decorated function."""
        # Clean global cache
        cache = get_cache()
        await cache.clear()
        cache.reset_stats()

        call_count = 0

        @cached(ttl=60, key_prefix="test")
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Clear cache
        await expensive_function.cache_clear()

        # Should call function again
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 2

    async def test_cached_decorator_cache_stats(self):
        """Test cache stats method on decorated function."""

        @cached(ttl=60, key_prefix="test")
        async def expensive_function(x: int) -> int:
            return x * 2

        # Clear stats and data first
        cache = get_cache()
        await cache.clear()
        cache.reset_stats()

        # Make some calls
        await expensive_function(5)
        await expensive_function(5)  # Cache hit
        await expensive_function(10)

        stats = expensive_function.cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2


@pytest.mark.asyncio
class TestGlobalCache:
    """Test global cache instance."""

    def test_get_cache_returns_same_instance(self):
        """Test that get_cache returns the same instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    async def test_global_cache_shared_state(self):
        """Test that global cache shares state."""
        cache1 = get_cache()
        await cache1.set("test_key", "test_value", ttl=60)

        cache2 = get_cache()
        result = await cache2.get("test_key")
        assert result == "test_value"


class TestRedisCacheProvider:
    """Test RedisCacheProvider using a mocked redis.asyncio client."""

    def _make_provider(self):
        """Build a RedisCacheProvider with a fully-mocked Redis client."""
        from unittest.mock import AsyncMock, MagicMock
        import sys
        import types

        # Fabricate a minimal redis.asyncio stub so the lazy import works
        aioredis_mod = types.ModuleType("redis.asyncio")
        mock_client = AsyncMock()
        aioredis_mod.from_url = MagicMock(return_value=mock_client)

        redis_mod = types.ModuleType("redis")
        redis_mod.asyncio = aioredis_mod
        sys.modules.setdefault("redis", redis_mod)
        sys.modules.setdefault("redis.asyncio", aioredis_mod)

        from services.cache_service import RedisCacheProvider

        provider = RedisCacheProvider(redis_url="redis://localhost:6379/0")
        provider._client = mock_client
        return provider, mock_client

    async def test_get_cache_hit(self):
        """get() returns deserialised value on cache hit."""
        import json

        provider, client = self._make_provider()
        client.get.return_value = json.dumps("hello").encode()

        result = await provider.get("key1")
        assert result == "hello"
        assert provider._stats["hits"] == 1
        assert provider._stats["misses"] == 0

    async def test_get_cache_miss(self):
        """get() returns None on cache miss."""
        provider, client = self._make_provider()
        client.get.return_value = None

        result = await provider.get("missing")
        assert result is None
        assert provider._stats["misses"] == 1

    async def test_set_with_ttl(self):
        """set() calls setex when ttl > 0."""
        import json

        provider, client = self._make_provider()

        await provider.set("k", {"x": 1}, ttl=30)
        client.setex.assert_called_once_with("k", 30, json.dumps({"x": 1}))
        assert provider._stats["sets"] == 1

    async def test_set_no_ttl(self):
        """set() calls set (no expiry) when ttl == 0."""
        import json

        provider, client = self._make_provider()

        await provider.set("k", "val", ttl=0)
        client.set.assert_called_once_with("k", json.dumps("val"))

    async def test_delete(self):
        """delete() removes key and increments deletes stat."""
        provider, client = self._make_provider()
        client.delete.return_value = 1  # 1 key deleted

        await provider.delete("k")
        client.delete.assert_called_once_with("k")
        assert provider._stats["deletes"] == 1

    async def test_delete_nonexistent(self):
        """delete() on missing key does not increment deletes."""
        provider, client = self._make_provider()
        client.delete.return_value = 0  # nothing deleted

        await provider.delete("ghost")
        assert provider._stats["deletes"] == 0

    async def test_clear(self):
        """clear() calls flushdb."""
        provider, client = self._make_provider()

        await provider.clear()
        client.flushdb.assert_called_once()

    async def test_get_stats(self):
        """get_stats() returns correct hit_rate."""
        provider, _ = self._make_provider()
        provider._stats = {"hits": 3, "misses": 1, "sets": 4, "deletes": 0}

        stats = provider.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(0.75)
        assert stats["size"] == -1  # Redis doesn't track locally

    def test_get_stats_empty(self):
        """get_stats() returns 0.0 hit_rate when no requests made."""
        provider, _ = self._make_provider()

        stats = provider.get_stats()
        assert stats["hit_rate"] == 0.0

    def test_reset_stats(self):
        """reset_stats() zeroes all counters."""
        provider, _ = self._make_provider()
        provider._stats = {"hits": 5, "misses": 2, "sets": 7, "deletes": 3}

        provider.reset_stats()
        assert all(v == 0 for v in provider._stats.values())

    async def test_close(self):
        """close() calls aclose on the Redis client."""
        provider, client = self._make_provider()

        await provider.close()
        client.aclose.assert_called_once()


class TestCreateCacheProvider:
    """Test create_cache_provider factory."""

    def test_returns_memory_provider_by_default(self):
        from services.cache_service import create_cache_provider, MemoryCacheProvider

        provider = create_cache_provider(backend="memory")
        assert isinstance(provider, MemoryCacheProvider)

    def test_returns_redis_provider_when_requested(self):
        """create_cache_provider('redis') returns a RedisCacheProvider (mocked)."""
        from unittest.mock import MagicMock, AsyncMock
        import sys
        import types

        aioredis_mod = types.ModuleType("redis.asyncio")
        aioredis_mod.from_url = MagicMock(return_value=AsyncMock())
        redis_mod = types.ModuleType("redis")
        redis_mod.asyncio = aioredis_mod
        sys.modules.setdefault("redis", redis_mod)
        sys.modules.setdefault("redis.asyncio", aioredis_mod)

        from services.cache_service import create_cache_provider, RedisCacheProvider

        provider = create_cache_provider(
            backend="redis", redis_url="redis://localhost:6379/0"
        )
        assert isinstance(provider, RedisCacheProvider)

    def test_replace_global_cache(self):
        """_replace_global_cache() changes what get_cache() returns."""
        from services.cache_service import (
            CacheService,
            MemoryCacheProvider,
            _replace_global_cache,
            get_cache,
        )

        new_service = CacheService(MemoryCacheProvider())
        _replace_global_cache(new_service)
        assert get_cache() is new_service
