#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cache service for MultiChain Explorer.

Provides caching with backend support (Memory, Redis).
"""

import functools
import hashlib
import time
import abc
from typing import Any, Callable, Dict, Optional, Tuple, List
import logging
import inspect

# Configure logging
logger = logging.getLogger(__name__)


class CacheProvider(abc.ABC):
    """Abstract base class for cache providers."""

    @abc.abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abc.abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        pass

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abc.abstractmethod
    async def clear(self) -> None:
        pass
    
    @abc.abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def reset_stats(self) -> None:
        pass


class MemoryCacheProvider(CacheProvider):
    """In-memory cache provider."""

    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    async def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            self._stats["misses"] += 1
            return None

        value, expiry = self._cache[key]
        if expiry > 0 and time.time() > expiry:
            del self._cache[key]
            self._stats["misses"] += 1
            return None

        self._stats["hits"] += 1
        return value

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        expiry = time.time() + ttl if ttl > 0 else 0
        self._cache[key] = (value, expiry)
        self._stats["sets"] += 1

    async def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]
            self._stats["deletes"] += 1

    async def clear(self) -> None:
        count = len(self._cache)
        self._cache.clear()
        self._stats["deletes"] += count
        
    async def cleanup_expired(self) -> int:
        """Memory-specific cleanup."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items() if expiry > 0 and current_time > expiry
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
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
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}


class CacheService:
    """
    Cache Service acting as a facade/adapter for specific providers.
    """

    def __init__(self, provider: Optional[CacheProvider] = None):
        """
        Initialize with a provider. Defaults to MemoryCacheProvider.
        """
        self.provider = provider or MemoryCacheProvider()

    async def get(self, key: str) -> Optional[Any]:
        return await self.provider.get(key)

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        await self.provider.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        await self.provider.delete(key)

    async def clear(self) -> None:
        await self.provider.clear()

    async def cleanup_expired(self) -> int:
        """
        Trigger cleanup if supported by provider.
        """
        if hasattr(self.provider, "cleanup_expired"):
            return await self.provider.cleanup_expired()
        return 0

    def get_stats(self) -> Dict[str, Any]:
        return self.provider.get_stats()

    def reset_stats(self) -> None:
        self.provider.reset_stats()


# Global cache instance
_cache = CacheService()


def get_cache() -> CacheService:
    """Get the global cache instance."""
    return _cache


def cached(ttl: int = 60, key_prefix: str = "") -> Callable:
    """
    Decorator for caching function results (Async only).
    """
    def decorator(func: Callable) -> Callable:
        if not inspect.iscoroutinefunction(func):
             raise TypeError(f"@cached decorator only supports async functions. {func.__name__} is synchronous.")

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            key_parts = [key_prefix, func.__name__]
            for arg in args:
                if hasattr(arg, "__dict__"):
                    key_parts.append(str(id(arg)))
                else:
                    key_parts.append(str(arg))
            for k in sorted(kwargs.keys()):
                key_parts.append(f"{k}={kwargs[k]}")
            
            key_str = ":".join(key_parts)
            cache_key = hashlib.md5(key_str.encode()).hexdigest()

            cache = get_cache()
            result = await cache.get(cache_key)
            if result is not None:
                return result

            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result

        async_wrapper.cache_clear = lambda: get_cache().clear()
        async_wrapper.cache_stats = lambda: get_cache().get_stats()

        return async_wrapper

    return decorator


def invalidate_pattern(pattern: str) -> int:
    """Invalidate cache entries matching a pattern."""
    pass
