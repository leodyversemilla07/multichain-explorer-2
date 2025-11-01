# -*- coding: utf-8 -*-

# MultiChain Explorer 2 - Performance Module
# Provides caching, compression, and performance monitoring

import gzip
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Simple in-memory cache with TTL support.

    For production, consider using Redis or Memcached.
    This is suitable for single-instance deployments.
    """

    def __init__(self, default_ttl: int = 60):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                self.hits += 1
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                # Expired, remove it
                del self.cache[key]
                logger.debug(f"Cache EXPIRED: {key}")

        self.misses += 1
        logger.debug(f"Cache MISS: {key}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache DELETE: {key}")

    def clear(self) -> None:
        """Clear all cached items."""
        count = len(self.cache)
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info(f"Cache cleared: {count} items removed")

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "items_cached": len(self.cache),
        }


# Global cache instance
_cache = SimpleCache(default_ttl=60)


def get_cache() -> SimpleCache:
    """Get the global cache instance."""
    return _cache


def cached(ttl: int = 60, key_prefix: str = ""):
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache key

    Example:
        @cached(ttl=300, key_prefix='block')
        def get_block(chain_name, height):
            # expensive operation
            return block_data
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


def compress_response(content: bytes, min_size: int = 1024) -> Tuple[bytes, bool]:
    """
    Compress response content using gzip.

    Args:
        content: Response content bytes
        min_size: Minimum size in bytes to compress (default 1KB)

    Returns:
        Tuple of (compressed_content, was_compressed)
    """
    if len(content) < min_size:
        # Don't compress small responses
        return content, False

    try:
        compressed = gzip.compress(content, compresslevel=6)
        # Only use compression if it actually reduces size
        if len(compressed) < len(content):
            logger.debug(
                f"Compressed response: {len(content)} -> {len(compressed)} bytes "
                f"({(1 - len(compressed)/len(content)) * 100:.1f}% reduction)"
            )
            return compressed, True
        else:
            return content, False
    except Exception as e:
        logger.warning(f"Compression failed: {e}")
        return content, False


def get_cache_headers(file_type: str = "static") -> list:
    """
    Get HTTP cache headers for different file types.

    Args:
        file_type: Type of file ('static', 'html', 'json', 'image')

    Returns:
        List of header tuples
    """
    headers = []

    if file_type == "static":
        # Static assets: cache for 1 hour
        headers.append(("Cache-Control", "public, max-age=3600"))
    elif file_type == "image":
        # Images: cache for 1 day
        headers.append(("Cache-Control", "public, max-age=86400"))
    elif file_type == "html":
        # HTML: cache for 5 minutes, revalidate
        headers.append(("Cache-Control", "public, max-age=300, must-revalidate"))
    elif file_type == "json":
        # JSON API: cache for 30 seconds
        headers.append(("Cache-Control", "public, max-age=30"))
    else:
        # Default: no cache
        headers.append(("Cache-Control", "no-cache"))

    return headers


class RequestTimer:
    """
    Context manager for timing requests.

    Example:
        with RequestTimer("GET /block/123") as timer:
            # do work
            pass
        print(f"Request took {timer.elapsed_ms}ms")
    """

    def __init__(self, request_path: str = ""):
        self.request_path = request_path
        self.start_time = 0.0
        self.end_time = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000

        # Log slow requests (>500ms)
        if self.elapsed_ms > 500:
            logger.warning(f"SLOW REQUEST: {self.request_path} took {self.elapsed_ms:.2f}ms")
        else:
            logger.debug(f"Request: {self.request_path} took {self.elapsed_ms:.2f}ms")

        return False  # Don't suppress exceptions


def log_performance_stats():
    """Log performance statistics."""
    cache_stats = _cache.get_stats()

    logger.info("=" * 60)
    logger.info("PERFORMANCE STATISTICS")
    logger.info("=" * 60)
    logger.info(f"Cache hits: {cache_stats['hits']}")
    logger.info(f"Cache misses: {cache_stats['misses']}")
    logger.info(f"Cache hit rate: {cache_stats['hit_rate_percent']}%")
    logger.info(f"Items in cache: {cache_stats['items_cached']}")
    logger.info("=" * 60)


# Export public API
__all__ = [
    "SimpleCache",
    "get_cache",
    "cached",
    "compress_response",
    "get_cache_headers",
    "RequestTimer",
    "log_performance_stats",
]
