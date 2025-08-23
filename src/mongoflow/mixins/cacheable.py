"""Caching mixin for MongoFlow repositories."""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Dict, Optional

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class CacheableMixin:
    """
    Mixin to add caching functionality to repositories.

    Requires Redis for caching support.

    Example:
        >>> class UserRepository(Repository, CacheableMixin):
        ...     collection_name = 'users'
        ...     cache_ttl = 300  # 5 minutes
        ...
        >>> users = UserRepository()
        >>> users.enable_cache(redis_client)
        >>> user = users.find_cached('user_id')
    """

    cache_enabled: bool = False
    cache_ttl: int = 300  # Default 5 minutes
    cache_prefix: str = 'mongoflow'
    cache_client: Optional[Any] = None

    def enable_cache(self, redis_client: Any, ttl: Optional[int] = None) -> None:
        """
        Enable caching with Redis client.

        Args:
            redis_client: Redis client instance
            ttl: Cache TTL in seconds
        """
        if not HAS_REDIS:
            raise ImportError("Redis is required for caching. Install with: pip install mongoflow[cache]")

        self.cache_client = redis_client
        self.cache_enabled = True

        if ttl:
            self.cache_ttl = ttl

    def disable_cache(self) -> None:
        """Disable caching."""
        self.cache_enabled = False
        self.cache_client = None

    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """
        Generate cache key for method call.

        Args:
            method: Method name
            *args: Method arguments
            **kwargs: Method keyword arguments

        Returns:
            Cache key string
        """
        key_data = {
            'collection': self.collection_name,
            'method': method,
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }

        key_hash = hashlib.md5(
            json.dumps(key_data, sort_keys=True).encode()
        ).hexdigest()

        return f"{self.cache_prefix}:{self.collection_name}:{method}:{key_hash}"

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.cache_enabled or not self.cache_client:
            return None

        try:
            data = self.cache_client.get(key)
            if data:
                return json.loads(data)
        except Exception:
            # Log error but don't fail
            pass

        return None

    def _set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set cache value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
        """
        if not self.cache_enabled or not self.cache_client:
            return

        try:
            ttl = ttl or self.cache_ttl
            self.cache_client.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
        except Exception:
            # Log error but don't fail
            pass

    def _delete_cache(self, pattern: Optional[str] = None) -> None:
        """
        Delete cache entries.

        Args:
            pattern: Optional pattern to match keys
        """
        if not self.cache_enabled or not self.cache_client:
            return

        try:
            if pattern:
                keys = self.cache_client.keys(f"{self.cache_prefix}:{self.collection_name}:{pattern}*")
            else:
                keys = self.cache_client.keys(f"{self.cache_prefix}:{self.collection_name}:*")

            if keys:
                self.cache_client.delete(*keys)
        except Exception:
            pass

    def find_cached(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Find document by ID with caching.

        Args:
            id: Document ID

        Returns:
            Document or None
        """
        # Try cache first
        cache_key = self._get_cache_key('find', id)
        cached = self._get_from_cache(cache_key)

        if cached is not None:
            return cached

        # Fetch from database
        result = self.find(id)

        # Cache result
        if result:
            self._set_cache(cache_key, result)

        return result

    def query_cached(self, cache_key: str, ttl: Optional[int] = None):
        """
        Decorator for caching query results.

        Args:
            cache_key: Cache key for the query
            ttl: Optional TTL override

        Example:
            >>> @users.query_cached('active_users', ttl=600)
            ... def get_active_users():
            ...     return users.where('status', 'active').get()
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Try cache first
                key = self._get_cache_key(cache_key, *args, **kwargs)
                cached = self._get_from_cache(key)

                if cached is not None:
                    return cached

                # Execute query
                result = func(*args, **kwargs)

                # Cache result
                self._set_cache(key, result, ttl)

                return result

            return wrapper
        return decorator

    def invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """
        Invalidate cache entries.

        Args:
            pattern: Optional pattern to match
        """
        self._delete_cache(pattern)

    # Override mutation methods to invalidate cache

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create with cache invalidation."""
        result = super().create(data)
        self.invalidate_cache()
        return result

    def update(self, id: str, data: Dict[str, Any]) -> bool:
        """Update with cache invalidation."""
        result = super().update(id, data)
        if result:
            self.invalidate_cache()
        return result

    def delete(self, id: str) -> bool:
        """Delete with cache invalidation."""
        result = super().delete(id)
        if result:
            self.invalidate_cache()
        return result

    def cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.cache_enabled or not self.cache_client:
            return {'enabled': False}

        try:
            keys = self.cache_client.keys(f"{self.cache_prefix}:{self.collection_name}:*")

            return {
                'enabled': True,
                'keys_count': len(keys),
                'ttl': self.cache_ttl,
                'prefix': f"{self.cache_prefix}:{self.collection_name}"
            }
        except Exception:
            return {'enabled': True, 'error': 'Failed to get stats'}
