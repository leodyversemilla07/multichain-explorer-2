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
from typing import Any, Callable, Dict, Optional, Tuple
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
            key
            for key, (_, expiry) in self._cache.items()
            if expiry > 0 and current_time > expiry
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
            raise TypeError(
                f"@cached decorator only supports async functions. {func.__name__} is synchronous."
            )

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
            cache_key = hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()

            cache = get_cache()
            result = await cache.get(cache_key)
            if result is not None:
                logger.debug(
                    "Cache hit for %s (prefix=%s)",
                    func.__name__,
                    key_prefix or "default",
                )
                return result

            logger.debug(
                "Cache miss for %s (prefix=%s)",
                func.__name__,
                key_prefix or "default",
            )
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result

        async_wrapper.cache_clear = lambda: get_cache().clear()
        async_wrapper.cache_stats = lambda: get_cache().get_stats()

        return async_wrapper

    return decorator


def invalidate_pattern(pattern: str) -> int:
    """Invalidate cache entries matching a pattern.

    Args:
        pattern: Substring pattern to match against cache keys.

    Returns:
        Number of invalidated entries.
    """
    cache = get_cache()
    provider = cache.provider
    if not isinstance(provider, MemoryCacheProvider):
        return 0
    keys_to_delete = [key for key in provider._cache if pattern in key]
    for key in keys_to_delete:
        del provider._cache[key]
        provider._stats["deletes"] += 1
    return len(keys_to_delete)


class RedisCacheProvider(CacheProvider):
    """
    Async Redis cache provider using redis.asyncio.

    Requires: pip install redis[asyncio]
    Activate via: CACHE_BACKEND=redis  REDIS_URL=redis://localhost:6379/0
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            import redis.asyncio as aioredis
        except ImportError as exc:
            raise ImportError(
                "redis package is required for CACHE_BACKEND=redis. "
                "Install it with: pip install 'redis[asyncio]'"
            ) from exc
        self._client = aioredis.from_url(redis_url, decode_responses=False)
        self._stats: Dict[str, int] = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    async def get(self, key: str):
        import json

        raw = await self._client.get(key)
        if raw is None:
            self._stats["misses"] += 1
            return None
        self._stats["hits"] += 1
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        import json

        encoded = json.dumps(value)
        if ttl > 0:
            await self._client.setex(key, ttl, encoded)
        else:
            await self._client.set(key, encoded)
        self._stats["sets"] += 1

    async def delete(self, key: str) -> None:
        deleted = await self._client.delete(key)
        if deleted:
            self._stats["deletes"] += 1

    async def clear(self) -> None:
        await self._client.flushdb()

    def get_stats(self) -> Dict[str, Any]:
        total = self._stats["hits"] + self._stats["misses"]
        return {
            **self._stats,
            "hit_rate": self._stats["hits"] / total if total > 0 else 0.0,
            "size": -1,
        }

    def reset_stats(self) -> None:
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    async def close(self) -> None:
        """Close the Redis connection pool."""
        await self._client.aclose()


def create_cache_provider(
    backend: str = "memory",
    redis_url: str = "redis://localhost:6379/0",
) -> CacheProvider:
    """
    Factory — selects and instantiates the correct cache provider.

    Args:
        backend: 'memory' (default) or 'redis'
        redis_url: Redis connection URL (ignored for memory backend)

    Returns:
        CacheProvider instance ready to use
    """
    if backend == "redis":
        logger.info(f"Initializing Redis cache provider: {redis_url}")
        return RedisCacheProvider(redis_url=redis_url)
    logger.info("Using in-memory cache provider")
    return MemoryCacheProvider()


def _replace_global_cache(new_cache: "CacheService") -> None:
    """
    Replace the module-level global cache instance.

    Called from the app lifespan to swap in a provider selected from env config
    before the first request arrives.
    """
    global _cache
    _cache = new_cache
