#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for cache service."""

import time

import pytest

from services.cache_service import CacheService, cached, get_cache


class TestCacheService:
    """Test CacheService class."""

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = CacheService()
        cache.set("test_key", "test_value", ttl=60)

        result = cache.get("test_key")
        assert result == "test_value"

    def test_cache_get_nonexistent(self):
        """Test getting a non-existent key."""
        cache = CacheService()
        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_expiry(self):
        """Test cache entry expiration."""
        cache = CacheService()
        cache.set("test_key", "test_value", ttl=1)

        # Should be available immediately
        result = cache.get("test_key")
        assert result == "test_value"

        # Wait for expiry
        time.sleep(1.1)

        # Should be expired
        result = cache.get("test_key")
        assert result is None

    def test_cache_no_expiry(self):
        """Test cache entry with no expiry."""
        cache = CacheService()
        cache.set("test_key", "test_value", ttl=0)

        # Should be available
        result = cache.get("test_key")
        assert result == "test_value"

    def test_cache_delete(self):
        """Test cache entry deletion."""
        cache = CacheService()
        cache.set("test_key", "test_value", ttl=60)

        # Should be available
        result = cache.get("test_key")
        assert result == "test_value"

        # Delete
        cache.delete("test_key")

        # Should be gone
        result = cache.get("test_key")
        assert result is None

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = CacheService()
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)

        # Both should be available
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # Clear
        cache.clear()

        # Both should be gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = CacheService()
        cache.set("expired_key", "value1", ttl=1)
        cache.set("valid_key", "value2", ttl=60)

        # Wait for first key to expire
        time.sleep(1.1)

        # Cleanup
        removed = cache.cleanup_expired()
        assert removed == 1

        # Expired key should be gone
        assert cache.get("expired_key") is None

        # Valid key should still be there
        assert cache.get("valid_key") == "value2"

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = CacheService()
        cache.reset_stats()

        # Set some values
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)

        # Get some values (hits)
        cache.get("key1")
        cache.get("key2")

        # Get non-existent value (miss)
        cache.get("key3")

        # Delete a value
        cache.delete("key1")

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["sets"] == 2
        assert stats["deletes"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == pytest.approx(2 / 3)

    def test_cache_stats_reset(self):
        """Test resetting cache statistics."""
        cache = CacheService()
        cache.set("key1", "value1", ttl=60)
        cache.get("key1")

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

    def test_cache_stats_hit_rate_zero_requests(self):
        """Test hit rate calculation with zero requests."""
        cache = CacheService()
        cache.reset_stats()

        stats = cache.get_stats()
        assert stats["hit_rate"] == 0


class TestCachedDecorator:
    """Test cached decorator."""

    def setup_method(self):
        """Clear cache before each test."""
        cache = get_cache()
        cache.clear()
        cache.reset_stats()

    def test_cached_decorator_basic(self):
        """Test basic cached decorator functionality."""
        call_count = 0

        @cached(ttl=60, key_prefix="test")
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Still 1, not called again

    def test_cached_decorator_different_args(self):
        """Test cached decorator with different arguments."""
        call_count = 0

        @cached(ttl=60, key_prefix="test")
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Different argument should call function again
        result2 = expensive_function(10)
        assert result2 == 20
        assert call_count == 2

        # Same as first should use cache
        result3 = expensive_function(5)
        assert result3 == 10
        assert call_count == 2

    def test_cached_decorator_with_kwargs(self):
        """Test cached decorator with keyword arguments."""
        call_count = 0

        @cached(ttl=60, key_prefix="test")
        def expensive_function(x: int, y: int = 1) -> int:
            nonlocal call_count
            call_count += 1
            return x * y

        # First call
        result1 = expensive_function(5, y=3)
        assert result1 == 15
        assert call_count == 1

        # Same call should use cache
        result2 = expensive_function(5, y=3)
        assert result2 == 15
        assert call_count == 1

        # Different kwargs should call function
        result3 = expensive_function(5, y=2)
        assert result3 == 10
        assert call_count == 2

    def test_cached_decorator_expiry(self):
        """Test cached decorator with expiry."""
        call_count = 0

        @cached(ttl=1, key_prefix="test")
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Wait for expiry
        time.sleep(1.1)

        # Should call function again
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 2

    def test_cached_decorator_cache_clear(self):
        """Test cache clear method on decorated function."""
        call_count = 0

        @cached(ttl=60, key_prefix="test")
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Clear cache
        expensive_function.cache_clear()

        # Should call function again
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 2

    def test_cached_decorator_cache_stats(self):
        """Test cache stats method on decorated function."""

        @cached(ttl=60, key_prefix="test")
        def expensive_function(x: int) -> int:
            return x * 2

        # Clear stats first
        cache = get_cache()
        cache.reset_stats()

        # Make some calls
        expensive_function(5)
        expensive_function(5)  # Cache hit
        expensive_function(10)

        stats = expensive_function.cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2


class TestGlobalCache:
    """Test global cache instance."""

    def test_get_cache_returns_same_instance(self):
        """Test that get_cache returns the same instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2

    def test_global_cache_shared_state(self):
        """Test that global cache shares state."""
        cache1 = get_cache()
        cache1.set("test_key", "test_value", ttl=60)

        cache2 = get_cache()
        result = cache2.get("test_key")
        assert result == "test_value"
