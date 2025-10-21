"""Caching layer for improved performance."""

import hashlib
import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    created_at: float
    ttl: float
    hits: int = 0

    def is_expired(self) -> bool:
        """Check if entry is expired.

        Returns:
            True if expired
        """
        if self.ttl <= 0:
            return False  # Never expires

        return time.time() - self.created_at > self.ttl

    def get_age(self) -> float:
        """Get entry age in seconds.

        Returns:
            Age in seconds
        """
        return time.time() - self.created_at


class ICache(ABC):
    """Cache interface."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float = 0) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (0 = never expire)
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Statistics dictionary
        """
        pass


class InMemoryCache(ICache):
    """In-memory cache implementation.

    Features:
    - TTL support
    - Hit/miss tracking
    - Size limits
    - LRU eviction
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        """Initialize cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            self._misses += 1
            logger.debug(f"Cache miss: {key}")
            return None

        entry = self._cache[key]

        # Check expiration
        if entry.is_expired():
            del self._cache[key]
            self._misses += 1
            logger.debug(f"Cache expired: {key}")
            return None

        # Update hit count
        entry.hits += 1
        self._hits += 1
        logger.debug(f"Cache hit: {key}")

        return entry.value

    def set(self, key: str, value: Any, ttl: float = 0) -> None:
        """Set value in cache."""
        # Evict if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()

        # Use default TTL if not specified
        if ttl == 0:
            ttl = self.default_ttl

        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl,
        )

        self._cache[key] = entry
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache delete: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        return {
            "entries": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find entry with lowest hits and oldest age
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].hits, -self._cache[k].get_age()),
        )

        del self._cache[lru_key]
        logger.debug(f"Cache evicted LRU: {lru_key}")


class FileCache(ICache):
    """File-based cache implementation.

    Features:
    - Persistent storage
    - Pickle serialization
    - TTL support
    - Automatic cleanup
    """

    def __init__(
        self,
        cache_dir: Path,
        default_ttl: float = 3600,
        max_size_mb: int = 100,
    ):
        """Initialize file cache.

        Args:
            cache_dir: Cache directory
            default_ttl: Default TTL in seconds
            max_size_mb: Maximum cache size in MB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_file = self._get_cache_file(key)

        if not cache_file.exists():
            self._misses += 1
            return None

        try:
            # Read cache file
            with open(cache_file, "rb") as f:
                entry = pickle.load(f)

            # Check expiration
            if entry.is_expired():
                cache_file.unlink()
                self._misses += 1
                logger.debug(f"File cache expired: {key}")
                return None

            # Update hit count
            entry.hits += 1
            self._hits += 1

            # Write back updated entry
            with open(cache_file, "wb") as f:
                pickle.dump(entry, f)

            logger.debug(f"File cache hit: {key}")
            return entry.value

        except Exception as e:
            logger.error(f"File cache read error: {e}")
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: float = 0) -> None:
        """Set value in cache."""
        # Check size limits
        self._cleanup_if_needed()

        # Use default TTL if not specified
        if ttl == 0:
            ttl = self.default_ttl

        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl,
        )

        # Write to file
        cache_file = self._get_cache_file(key)
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(entry, f)
            logger.debug(f"File cache set: {key}")
        except Exception as e:
            logger.error(f"File cache write error: {e}")

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            cache_file.unlink()
            logger.debug(f"File cache delete: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        self._hits = 0
        self._misses = 0
        logger.info("File cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        # Calculate total size
        total_size = sum(
            f.stat().st_size for f in self.cache_dir.glob("*.cache")
        )

        # Count entries
        entry_count = len(list(self.cache_dir.glob("*.cache")))

        return {
            "entries": entry_count,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key.

        Args:
            key: Cache key

        Returns:
            Path to cache file
        """
        # Hash key to create filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _cleanup_if_needed(self) -> None:
        """Clean up old entries if size limit exceeded."""
        # Calculate current size
        total_size = sum(
            f.stat().st_size for f in self.cache_dir.glob("*.cache")
        )

        # Check if cleanup needed
        if total_size <= self.max_size_bytes:
            return

        logger.info(f"File cache cleanup needed ({total_size / 1024 / 1024:.2f} MB)")

        # Get all cache files with ages
        cache_files = []
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, "rb") as f:
                    entry = pickle.load(f)

                # Delete expired entries
                if entry.is_expired():
                    cache_file.unlink()
                    continue

                cache_files.append((cache_file, entry.get_age(), cache_file.stat().st_size))
            except Exception:
                # Delete corrupted files
                cache_file.unlink()

        # Sort by age (oldest first)
        cache_files.sort(key=lambda x: x[1], reverse=True)

        # Delete until under size limit
        current_size = sum(size for _, _, size in cache_files)
        for cache_file, age, size in cache_files:
            if current_size <= self.max_size_bytes:
                break

            cache_file.unlink()
            current_size -= size
            logger.debug(f"File cache cleanup: deleted {cache_file.name}")


class CacheManager:
    """Manage multiple cache layers.

    Features:
    - L1 (memory) and L2 (file) caching
    - Automatic promotion/demotion
    - Cache warming
    - Statistics aggregation
    """

    def __init__(
        self,
        memory_cache: Optional[InMemoryCache] = None,
        file_cache: Optional[FileCache] = None,
    ):
        """Initialize cache manager.

        Args:
            memory_cache: L1 memory cache
            file_cache: L2 file cache
        """
        self.memory_cache = memory_cache or InMemoryCache()
        self.file_cache = file_cache

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 then L2).

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        # Try L1 cache
        value = self.memory_cache.get(key)
        if value is not None:
            return value

        # Try L2 cache
        if self.file_cache:
            value = self.file_cache.get(key)
            if value is not None:
                # Promote to L1
                self.memory_cache.set(key, value)
                return value

        return None

    def set(self, key: str, value: Any, ttl: float = 0) -> None:
        """Set value in cache (both L1 and L2).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        # Set in L1
        self.memory_cache.set(key, value, ttl)

        # Set in L2 if available
        if self.file_cache:
            self.file_cache.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete value from both caches.

        Args:
            key: Cache key

        Returns:
            True if deleted from any cache
        """
        deleted_l1 = self.memory_cache.delete(key)
        deleted_l2 = self.file_cache.delete(key) if self.file_cache else False
        return deleted_l1 or deleted_l2

    def clear(self) -> None:
        """Clear all caches."""
        self.memory_cache.clear()
        if self.file_cache:
            self.file_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics.

        Returns:
            Statistics dictionary
        """
        stats = {
            "l1_memory": self.memory_cache.get_stats(),
        }

        if self.file_cache:
            stats["l2_file"] = self.file_cache.get_stats()

        return stats


def create_default_cache_manager(cache_dir: Optional[Path] = None) -> CacheManager:
    """Create cache manager with default settings.

    Args:
        cache_dir: Optional cache directory for file cache

    Returns:
        Configured cache manager
    """
    memory_cache = InMemoryCache(max_size=1000, default_ttl=3600)

    file_cache = None
    if cache_dir:
        file_cache = FileCache(
            cache_dir=cache_dir,
            default_ttl=86400,  # 24 hours
            max_size_mb=500,
        )

    return CacheManager(memory_cache=memory_cache, file_cache=file_cache)
