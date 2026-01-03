#!/usr/bin/env python3
"""
Application Cache Module - MySQL Backend
==========================================
Generic cache interface for li_xml database

Author: Silvester van der Leer
Version: 1.0
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pymysql

logger = logging.getLogger(__name__)


class AppCache:
    """MySQL-based application cache using li_xml.cache table"""
    
    def __init__(self):
        # Use same credentials as DHCP database
        self.host = os.getenv('DHCP_DB_HOST', '127.0.0.1')
        self.port = int(os.getenv('DHCP_DB_PORT', 3306))
        self.user = os.getenv('DHCP_DB_USER', 'root')
        self.password = os.getenv('DHCP_DB_PASSWORD', '')
        self.database = 'li_xml'
        self.connection = None
        
    def connect(self) -> bool:
        """Connect to MySQL database"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(f"Connected to cache database: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to cache database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def get(self, cache_key: str, cache_type: str = None) -> Optional[Dict[Any, Any]]:
        """
        Get cached data by key
        
        Args:
            cache_key: Cache key to retrieve
            cache_type: Optional cache type filter
            
        Returns:
            Cached data dict or None if not found/expired
        """
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                # Check expiration
                sql = """
                    SELECT data, expires_at 
                    FROM cache 
                    WHERE cache_key = %s
                """
                params = [cache_key]
                
                if cache_type:
                    sql += " AND cache_type = %s"
                    params.append(cache_type)
                
                cursor.execute(sql, params)
                result = cursor.fetchone()
                
                if result:
                    # Check if expired
                    if result['expires_at'] and datetime.now() > result['expires_at']:
                        logger.debug(f"Cache expired for key: {cache_key}")
                        self.delete(cache_key)
                        return None
                    
                    logger.debug(f"Cache hit for key: {cache_key}")
                    # Parse JSON data if it's a string
                    data = result['data']
                    if isinstance(data, str):
                        return json.loads(data)
                    return data
                
                logger.debug(f"Cache miss for key: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return None
    
    def set(self, cache_key: str, cache_type: str, data: Dict[Any, Any], 
            ttl_seconds: int = 86400):
        """
        Store data in cache
        
        Args:
            cache_key: Unique cache key
            cache_type: Cache category (device_list, device_validation, etc.)
            data: Data to cache (must be JSON serializable)
            ttl_seconds: Time to live in seconds (default 24 hours)
        """
        try:
            if not self.connection:
                self.connect()
            
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            
            with self.connection.cursor() as cursor:
                sql = """
                    INSERT INTO cache (cache_key, cache_type, data, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        data = VALUES(data),
                        expires_at = VALUES(expires_at),
                        updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(sql, (cache_key, cache_type, json.dumps(data), expires_at))
                self.connection.commit()
                
                logger.debug(f"Cached {cache_type}: {cache_key} (expires: {expires_at})")
                
        except Exception as e:
            logger.error(f"Error writing to cache: {e}")
            if self.connection:
                self.connection.rollback()
    
    def delete(self, cache_key: str):
        """Delete cache entry by key"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                cursor.execute("DELETE FROM cache WHERE cache_key = %s", (cache_key,))
                self.connection.commit()
                logger.debug(f"Deleted cache key: {cache_key}")
                
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            if self.connection:
                self.connection.rollback()
    
    def clear_type(self, cache_type: str):
        """Clear all cache entries of a specific type"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                cursor.execute("DELETE FROM cache WHERE cache_type = %s", (cache_type,))
                deleted = cursor.rowcount
                self.connection.commit()
                logger.info(f"Cleared {deleted} cache entries of type: {cache_type}")
                
        except Exception as e:
            logger.error(f"Error clearing cache type: {e}")
            if self.connection:
                self.connection.rollback()
    
    def cleanup_expired(self):
        """Remove expired cache entries"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < NOW()"
                )
                deleted = cursor.rowcount
                self.connection.commit()
                logger.info(f"Cleaned up {deleted} expired cache entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            if self.connection:
                self.connection.rollback()
