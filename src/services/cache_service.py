"""Cache Service - In-memory caching for performance optimization.

This service provides a simple TTL-based cache to reduce redundant
API calls and improve response times.
"""

import time
from typing import Any, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from threading import Lock

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with TTL support."""
    value: T
    expires_at: float
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class CacheService:
    """Thread-safe in-memory cache with TTL support.
    
    Features:
    - Automatic expiration
    - Thread-safe operations
    - Configurable default TTL
    - Cache statistics
    """
    
    def __init__(self, default_ttl: int = 300):
        """Initialize the cache service.
        
        Args:
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl
        
        with self._lock:
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> int:
        """Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._cache.items() 
                if v.expires_at < now
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
    
    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "entries": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%"
            }


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create the cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(default_ttl=300)  # 5 minute default
    return _cache_service


# Cache key generators
def candidate_cache_key(candidate_id: str) -> str:
    """Generate cache key for candidate data."""
    return f"candidate:{candidate_id}"


def job_cache_key(job_id: str) -> str:
    """Generate cache key for job data."""
    return f"job:{job_id}"


def search_cache_key(candidate_id: str, criteria: str = "") -> str:
    """Generate cache key for search results."""
    return f"search:{candidate_id}:{hash(criteria)}"

