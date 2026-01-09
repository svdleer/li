#!/usr/bin/env python3
"""
Cache Manager Module
====================

Provides caching with TTL management for Netshot API data with Redis support.
Falls back to file-based cache if Redis is unavailable.

Features:
- Redis in-memory caching (primary)
- File-based JSON caching (fallback)
- TTL (Time To Live) expiration
- Thread-safe operations
- Docker volume compatible
- Cache statistics and monitoring

Author: Silvester van der Leer
Version: 2.0
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, List, Callable
from functools import wraps
import threading
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisCache:
    """Redis-based cache with automatic fallback to file cache"""
    
    def __init__(self, redis_url: str = 'redis://localhost:6379/0', default_ttl: int = 86400):
        """
        Initialize Redis cache
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds (default: 24 hours)
        """
        self.default_ttl = default_ttl
        self.logger = logging.getLogger('redis_cache')
        self._redis = None
        self._use_redis = False
        
        if REDIS_AVAILABLE:
            try:
                self._redis = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
                # Test connection
                self._redis.ping()
                self._use_redis = True
                self.logger.info(f"Redis cache initialized: {redis_url}")
            except Exception as e:
                self.logger.warning(f"Redis not available, using file cache: {e}")
        else:
            self.logger.warning("Redis module not installed, using file cache")
        
        # Fallback to file cache
        if not self._use_redis:
            self._file_cache = CacheManager(default_ttl=default_ttl)
            self.logger.info("Using file-based cache as fallback")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in cache"""
        if self._use_redis:
            try:
                ttl = ttl or self.default_ttl
                serialized = json.dumps(value)
                self._redis.setex(key, ttl, serialized)
                return True
            except Exception as e:
                self.logger.error(f"Redis set error: {e}")
                return False
        else:
            return self._file_cache.set(key, value, ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache"""
        if self._use_redis:
            try:
                value = self._redis.get(key)
                if value is not None:
                    return json.loads(value)
                return None
            except Exception as e:
                self.logger.error(f"Redis get error: {e}")
                return None
        else:
            return self._file_cache.get(key)
    
    def get_or_set(self, key: str, func: callable, ttl: Optional[int] = None) -> Any:
        """Get value from cache or compute and cache it"""
        # Try to get from cache
        value = self.get(key)
        if value is not None:
            self.logger.debug(f"Cache HIT for key: {key}")
            return value
        
        # Compute value
        self.logger.debug(f"Cache MISS for key: {key}, computing...")
        value = func()
        
        # Store in cache
        self.set(key, value, ttl)
        self.logger.debug(f"Cached computed value for key: {key}")
        return value
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if self._use_redis:
            try:
                self._redis.delete(key)
                return True
            except Exception as e:
                self.logger.error(f"Redis delete error: {e}")
                return False
        else:
            return self._file_cache.delete(key)
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if self._use_redis:
            try:
                keys = self._redis.keys(pattern)
                if keys:
                    return self._redis.delete(*keys)
                return 0
            except Exception as e:
                self.logger.error(f"Redis clear_pattern error: {e}")
                return 0
        else:
            return self._file_cache.clear_pattern(pattern)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self._use_redis:
            try:
                info = self._redis.info('stats')
                return {
                    'backend': 'redis',
                    'total_keys': self._redis.dbsize(),
                    'hits': info.get('keyspace_hits', 0),
                    'misses': info.get('keyspace_misses', 0),
                    'memory_used': info.get('used_memory_human', 'N/A')
                }
            except Exception as e:
                self.logger.error(f"Redis stats error: {e}")
                return {'backend': 'redis', 'error': str(e)}
        else:
            stats = self._file_cache.get_stats()
            stats['backend'] = 'file'
            return stats


class CacheManager:
    """
    File-based cache manager with TTL support
    
    Features:
    - Automatic cache expiration based on TTL
    - Thread-safe operations
    - Cache statistics tracking
    - Docker volume compatibility
    """
    
    def __init__(self, cache_dir: str = '.cache', default_ttl: int = 86400):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory for cache storage (Docker volume mountpoint)
            default_ttl: Default TTL in seconds (default: 24 hours)
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.logger = logging.getLogger('cache_manager')
        self._lock = threading.Lock()
        
        # Create cache directory
        self._ensure_cache_dir()
        
        self.logger.info(f"Cache manager initialized: {self.cache_dir}")
        self.logger.info(f"Default TTL: {default_ttl} seconds ({default_ttl/3600:.1f} hours)")
    
    def _ensure_cache_dir(self):
        """Ensure cache directory exists with proper permissions"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Create metadata directory
            (self.cache_dir / '_meta').mkdir(exist_ok=True)
            
            self.logger.debug(f"Cache directory ready: {self.cache_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create cache directory: {e}")
            raise
    
    def _get_cache_file_path(self, key: str) -> Path:
        """
        Get cache file path for a given key
        
        Args:
            key: Cache key
            
        Returns:
            Path to cache file
        """
        # Use hash to create safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def _get_meta_file_path(self, key: str) -> Path:
        """
        Get metadata file path for a given key
        
        Args:
            key: Cache key
            
        Returns:
            Path to metadata file
        """
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / '_meta' / f"{key_hash}.meta"
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store value in cache
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (uses default if not specified)
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                cache_file = self._get_cache_file_path(key)
                meta_file = self._get_meta_file_path(key)
                
                # Prepare cache data
                cache_data = {
                    'value': value,
                    'cached_at': datetime.now().isoformat(),
                    'key': key
                }
                
                # Prepare metadata
                ttl_seconds = ttl if ttl is not None else self.default_ttl
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
                
                meta_data = {
                    'key': key,
                    'cached_at': datetime.now().isoformat(),
                    'expires_at': expires_at.isoformat(),
                    'ttl': ttl_seconds,
                    'size': len(json.dumps(value))
                }
                
                # Write cache file
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                
                # Write metadata file
                with open(meta_file, 'w') as f:
                    json.dump(meta_data, f, indent=2)
                
                self.logger.debug(f"Cached: {key} (TTL: {ttl_seconds}s, expires: {expires_at})")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to cache {key}: {e}")
                return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve value from cache
        
        Args:
            key: Cache key
            default: Default value if not found or expired
            
        Returns:
            Cached value or default
        """
        with self._lock:
            try:
                cache_file = self._get_cache_file_path(key)
                meta_file = self._get_meta_file_path(key)
                
                # Check if cache file exists
                if not cache_file.exists():
                    self.logger.debug(f"Cache miss: {key} (not found)")
                    return default
                
                # Check expiration
                if meta_file.exists():
                    with open(meta_file, 'r') as f:
                        meta_data = json.load(f)
                    
                    expires_at = datetime.fromisoformat(meta_data['expires_at'])
                    
                    if datetime.now() > expires_at:
                        self.logger.debug(f"Cache miss: {key} (expired)")
                        # Clean up expired cache
                        self._delete_cache_files(key)
                        return default
                
                # Read cache file
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                self.logger.debug(f"Cache hit: {key}")
                return cache_data.get('value', default)
                
            except Exception as e:
                self.logger.error(f"Failed to retrieve cache {key}: {e}")
                return default
    
    def delete(self, key: str) -> bool:
        """
        Delete cached value
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                self._delete_cache_files(key)
                self.logger.debug(f"Deleted cache: {key}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to delete cache {key}: {e}")
                return False
    
    def _delete_cache_files(self, key: str):
        """Delete cache and metadata files for a key"""
        cache_file = self._get_cache_file_path(key)
        meta_file = self._get_meta_file_path(key)
        
        if cache_file.exists():
            cache_file.unlink()
        
        if meta_file.exists():
            meta_file.unlink()
    
    def clear(self) -> bool:
        """
        Clear all cache
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                count = 0
                for cache_file in self.cache_dir.glob('*.json'):
                    cache_file.unlink()
                    count += 1
                
                # Clear metadata
                meta_dir = self.cache_dir / '_meta'
                if meta_dir.exists():
                    for meta_file in meta_dir.glob('*.meta'):
                        meta_file.unlink()
                
                self.logger.info(f"Cleared {count} cache entries")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to clear cache: {e}")
                return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache and is not expired
        
        Args:
            key: Cache key
            
        Returns:
            True if exists and valid, False otherwise
        """
        cache_file = self._get_cache_file_path(key)
        
        if not cache_file.exists():
            return False
        
        # Check expiration
        meta_file = self._get_meta_file_path(key)
        if meta_file.exists():
            try:
                with open(meta_file, 'r') as f:
                    meta_data = json.load(f)
                
                expires_at = datetime.fromisoformat(meta_data['expires_at'])
                return datetime.now() <= expires_at
            except Exception:
                return False
        
        return True
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            cache_files = list(self.cache_dir.glob('*.json'))
            total_count = len(cache_files)
            expired_count = 0
            total_size = 0
            
            for cache_file in cache_files:
                total_size += cache_file.stat().st_size
                
                # Check if expired
                key_hash = cache_file.stem
                meta_file = self.cache_dir / '_meta' / f"{key_hash}.meta"
                
                if meta_file.exists():
                    try:
                        with open(meta_file, 'r') as f:
                            meta_data = json.load(f)
                        
                        expires_at = datetime.fromisoformat(meta_data['expires_at'])
                        if datetime.now() > expires_at:
                            expired_count += 1
                    except Exception:
                        pass
            
            return {
                'total_entries': total_count,
                'valid_entries': total_count - expired_count,
                'expired_entries': expired_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'cache_dir': str(self.cache_dir)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            try:
                removed = 0
                cache_files = list(self.cache_dir.glob('*.json'))
                
                for cache_file in cache_files:
                    key_hash = cache_file.stem
                    meta_file = self.cache_dir / '_meta' / f"{key_hash}.meta"
                    
                    if meta_file.exists():
                        try:
                            with open(meta_file, 'r') as f:
                                meta_data = json.load(f)
                            
                            expires_at = datetime.fromisoformat(meta_data['expires_at'])
                            
                            if datetime.now() > expires_at:
                                cache_file.unlink()
                                meta_file.unlink()
                                removed += 1
                                
                        except Exception as e:
                            self.logger.warning(f"Error checking expiration for {cache_file}: {e}")
                
                self.logger.info(f"Cleaned up {removed} expired cache entries")
                return removed
                
            except Exception as e:
                self.logger.error(f"Failed to cleanup expired cache: {e}")
                return 0
    
    def get_metadata(self, key: str) -> Optional[Dict]:
        """
        Get metadata for a cached key
        
        Args:
            key: Cache key
            
        Returns:
            Metadata dictionary or None
        """
        try:
            meta_file = self._get_meta_file_path(key)
            
            if not meta_file.exists():
                return None
            
            with open(meta_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to get metadata for {key}: {e}")
            return None


def cached(key_func: Callable = None, ttl: int = None):
    """
    Decorator for caching function results
    
    Args:
        key_func: Function to generate cache key from args
        ttl: Time to live in seconds
        
    Example:
        @cached(key_func=lambda hostname: f"device_{hostname}", ttl=3600)
        def get_device(hostname):
            return api.fetch_device(hostname)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache manager from first argument (self)
            if len(args) > 0 and hasattr(args[0], 'cache'):
                cache_manager = args[0].cache
            else:
                # No cache manager available
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key based on function name and args
                cache_key = f"{func.__name__}_{args}_{kwargs}"
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache_manager.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


# Global cache manager instance
_global_cache = None


def get_cache_manager(cache_dir: str = None, ttl: int = None) -> CacheManager:
    """
    Get or create global cache manager instance
    
    Args:
        cache_dir: Cache directory (default: from env or '.cache')
        ttl: Default TTL in seconds (default: from env or 24 hours)
        
    Returns:
        CacheManager instance
    """
    global _global_cache
    
    if _global_cache is None:
        cache_dir = cache_dir or os.getenv('CACHE_DIR', '.cache')
        ttl = ttl or int(os.getenv('CACHE_TTL', '86400'))
        _global_cache = CacheManager(cache_dir=cache_dir, default_ttl=ttl)
    
    return _global_cache


if __name__ == '__main__':
    # Test cache manager
    logging.basicConfig(level=logging.DEBUG)
    
    cache = CacheManager(cache_dir='.cache_test', default_ttl=10)
    
    # Test set/get
    print("Testing set/get...")
    cache.set('test_key', {'data': 'test_value'}, ttl=5)
    value = cache.get('test_key')
    print(f"Retrieved: {value}")
    
    # Test stats
    print("\nCache stats:")
    stats = cache.get_stats()
    for key, val in stats.items():
        print(f"  {key}: {val}")
    
    # Test expiration
    print("\nWaiting for expiration...")
    time.sleep(6)
    value = cache.get('test_key')
    print(f"After expiration: {value}")
    
    # Cleanup
    cache.clear()
    print("\nCache cleared")
