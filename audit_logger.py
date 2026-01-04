#!/usr/bin/env python3
"""
Audit Logger
=============
Tracks user actions and system events for compliance and monitoring.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List
from app_cache import AppCache
import json

class AuditLogger:
    """Audit logging system for tracking user actions"""
    
    CATEGORY_LOGIN = 'login'
    CATEGORY_LOGOUT = 'logout'
    CATEGORY_XML_GENERATE = 'xml_generate'
    CATEGORY_XML_UPLOAD = 'xml_upload'
    CATEGORY_XML_DOWNLOAD = 'xml_download'
    CATEGORY_DEVICE_REFRESH = 'device_refresh'
    CATEGORY_CACHE_REFRESH = 'cache_refresh'
    CATEGORY_CONFIG_CHANGE = 'config_change'
    CATEGORY_VIEW = 'view'
    CATEGORY_ERROR = 'error'
    
    LEVEL_INFO = 'info'
    LEVEL_WARNING = 'warning'
    LEVEL_ERROR = 'error'
    LEVEL_CRITICAL = 'critical'
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache = AppCache()
    
    def log(self, 
            username: str,
            category: str,
            action: str,
            details: Optional[str] = None,
            level: str = LEVEL_INFO,
            ip_address: Optional[str] = None) -> bool:
        """
        Log an audit event
        
        Args:
            username: User who performed the action
            category: Event category (login, xml_generate, etc.)
            action: Brief description of action
            details: Additional details (optional)
            level: Log level (info, warning, error, critical)
            ip_address: User's IP address (optional)
            
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            timestamp = datetime.utcnow()
            
            log_entry = {
                'timestamp': timestamp.isoformat(),
                'username': username,
                'category': category,
                'action': action,
                'details': details or '',
                'level': level,
                'ip_address': ip_address or 'unknown'
            }
            
            # Store in MySQL cache
            if self.cache.connect():
                self.cache.set(
                    cache_key=f'audit_log:{timestamp.timestamp()}:{username}',
                    cache_type='audit_log',
                    data=log_entry,
                    ttl_seconds=31536000  # 1 year retention
                )
                self.cache.disconnect()
            
            # Also log to file
            log_msg = f"[{category.upper()}] {username}: {action}"
            if details:
                log_msg += f" - {details}"
            
            if level == self.LEVEL_ERROR or level == self.LEVEL_CRITICAL:
                self.logger.error(log_msg)
            elif level == self.LEVEL_WARNING:
                self.logger.warning(log_msg)
            else:
                self.logger.info(log_msg)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
            return False
    
    def get_logs(self,
                 category: Optional[str] = None,
                 username: Optional[str] = None,
                 level: Optional[str] = None,
                 limit: int = 100,
                 offset: int = 0) -> List[Dict]:
        """
        Retrieve audit logs with optional filtering
        
        Args:
            category: Filter by category (optional)
            username: Filter by username (optional)
            level: Filter by level (optional)
            limit: Maximum number of logs to return
            offset: Offset for pagination
            
        Returns:
            List of audit log entries
        """
        try:
            logs = []
            
            if self.cache.connect():
                cursor = self.cache.connection.cursor()
                
                # Build query with filters
                query = "SELECT cache_key, data FROM cache WHERE cache_type = 'audit_log'"
                params = []
                
                if username:
                    query += " AND cache_key LIKE %s"
                    params.append(f'%:{username}')
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                
                for row in cursor.fetchall():
                    data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                    
                    # Apply filters
                    if category and data.get('category') != category:
                        continue
                    if level and data.get('level') != level:
                        continue
                    
                    logs.append(data)
                
                self.cache.disconnect()
            
            return logs[:limit]  # Ensure we don't exceed limit after filtering
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit logs: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """
        Get audit log statistics
        
        Returns:
            Dictionary with statistics (total_events, by_category, by_level)
        """
        try:
            stats = {
                'total_events': 0,
                'by_category': {},
                'by_level': {}
            }
            
            if self.cache.connect():
                cursor = self.cache.connection.cursor()
                cursor.execute("SELECT data FROM cache WHERE cache_type = 'audit_log'")
                
                for row in cursor.fetchall():
                    data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                    
                    stats['total_events'] += 1
                    
                    category = data.get('category', 'unknown')
                    stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                    
                    level = data.get('level', 'info')
                    stats['by_level'][level] = stats['by_level'].get(level, 0) + 1
                
                self.cache.disconnect()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get audit stats: {e}")
            return {'total_events': 0, 'by_category': {}, 'by_level': {}}


# Global audit logger instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
