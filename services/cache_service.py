#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cache service for MultiChain Explorer.

Provides in-memory caching with TTL support. Can be extended to use Redis
for distributed caching in production environments.
"""

import functools
import hashlib
import time
from typing import Any, Callable, Dict, Optional, Tuple


class CacheService:
    """
    In-memory cache service with TTL support.

    This implementation uses a simple dictionary-based cache. For production
    deployments with multiple workers, consider using Redis or Memcached.
    """

    def __init__(self):
        """Initialize the cache."""
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self._cache:
            self._stats["misses"] += 1
            return None

        value, expiry = self._cache[key]
        if expiry > 0 and time.time() > expiry:
            # Expired
            del self._cache[key]
            self._stats["misses"] += 1
            return None

        self._stats["hits"] += 1
        return value

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (0 = no expiry)
        """
        expiry = time.time() + ttl if ttl > 0 else 0
        self._cache[key] = (value, expiry)
        self._stats["sets"] += 1

    def delete(self, key: str) -> None:
        """
        Delete a value from cache.

        Args:
            key: Cache key
        """
        if key in self._cache:
            del self._cache[key]
            self._stats["deletes"] += 1

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._stats["deletes"] += count

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items() if expiry > 0 and current_time > expiry
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "deletes": self._stats["deletes"],
            "hit_rate": hit_rate,
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}


# Global cache instance
_cache = CacheService()


def get_cache() -> CacheService:
    """
    Get the global cache instance.

    Returns:
        Global CacheService instance
    """
    return _cache


def cached(ttl: int = 60, key_prefix: str = "") -> Callable:
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key

    Returns:
        Decorated function

    Example:
        @cached(ttl=300, key_prefix='block')
        def get_block(chain_id: str, height: int):
            return fetch_block_from_api(chain_id, height)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name, args, and kwargs
            key_parts = [key_prefix, func.__name__]

            # Add args to key
            for arg in args:
                if hasattr(arg, "__dict__"):
                    # For objects, use a simplified representation
                    key_parts.append(str(id(arg)))
                else:
                    key_parts.append(str(arg))

            # Add kwargs to key (sorted for consistency)
            for k in sorted(kwargs.keys()):
                key_parts.append(f"{k}={kwargs[k]}")

            # Create hash of the key parts
            key_str = ":".join(key_parts)
            cache_key = hashlib.md5(key_str.encode()).hexdigest()  # nosec B324 - Not for security

            # Try to get from cache
            cache = get_cache()
            result = cache.get(cache_key)

            if result is not None:
                return result

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        # Add cache control methods to wrapper
        wrapper.cache_clear = lambda: get_cache().clear()
        wrapper.cache_stats = lambda: get_cache().get_stats()

        return wrapper

    return decorator


def invalidate_pattern(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.

    Args:
        pattern: Pattern to match (simple string prefix)

    Returns:
        Number of entries invalidated

    Note:
        This is a simple implementation. For production use with Redis,
        use Redis SCAN with pattern matching.
    """
    cache = get_cache()
    # For now, just clear the entire cache
    # A more sophisticated implementation would track keys by pattern
    cache.clear()
    return 0
