#!/usr/bin/env python3
"""
Audit Log Module
================

Track all system activities for compliance and troubleshooting:
- User actions (login, logout, page views)
- XML generation events
- Validation runs
- Upload operations
- Configuration changes

Author: Silvester van der Leer
Version: 2.0
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import csv

logger = logging.getLogger(__name__)


class AuditLogger:
    """Centralized audit logging system"""
    
    # Event categories
    CATEGORY_AUTH = 'authentication'
    CATEGORY_XML = 'xml_generation'
    CATEGORY_VALIDATION = 'subnet_validation'
    CATEGORY_UPLOAD = 'file_upload'
    CATEGORY_CONFIG = 'configuration'
    CATEGORY_VIEW = 'page_view'
    CATEGORY_SEARCH = 'search'
    
    # Event severity levels
    LEVEL_INFO = 'info'
    LEVEL_WARNING = 'warning'
    LEVEL_ERROR = 'error'
    LEVEL_CRITICAL = 'critical'
    
    def __init__(self, storage_path: str = 'logs/audit.jsonl', demo_mode: bool = True):
        """
        Initialize audit logger
        
        Args:
            storage_path: Path to audit log file (JSONL format)
            demo_mode: If True, store in memory only
        """
        self.storage_path = Path(storage_path)
        self.demo_mode = demo_mode
        self.in_memory_log = []  # For demo mode or quick access
        
        if not demo_mode:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Audit logger initialized: {self.storage_path}")
        else:
            logger.info("Audit logger initialized in DEMO MODE (memory only)")
    
    def log_event(self, category: str, action: str, user: str, 
                  level: str = LEVEL_INFO, details: Optional[Dict] = None,
                  ip_address: Optional[str] = None) -> Dict:
        """
        Log an audit event
        
        Args:
            category: Event category (AUTH, XML, VALIDATION, etc.)
            action: Specific action performed
            user: Username or email
            level: Severity level
            details: Additional event details
            ip_address: Client IP address
        
        Returns:
            Complete audit event dictionary
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'action': action,
            'user': user,
            'level': level,
            'details': details or {},
            'ip_address': ip_address
        }
        
        # Store in memory
        self.in_memory_log.append(event)
        
        # Persist to file if not demo mode
        if not self.demo_mode:
            try:
                with open(self.storage_path, 'a') as f:
                    f.write(json.dumps(event) + '\n')
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
        
        logger.info(f"AUDIT: [{category}] {action} by {user}")
        return event
    
    # ========================================================================
    # Convenience Methods for Common Events
    # ========================================================================
    
    def log_login(self, user: str, ip_address: str, success: bool = True):
        """Log user login attempt"""
        return self.log_event(
            category=self.CATEGORY_AUTH,
            action='login_success' if success else 'login_failed',
            user=user,
            level=self.LEVEL_INFO if success else self.LEVEL_WARNING,
            ip_address=ip_address
        )
    
    def log_logout(self, user: str, ip_address: str):
        """Log user logout"""
        return self.log_event(
            category=self.CATEGORY_AUTH,
            action='logout',
            user=user,
            level=self.LEVEL_INFO,
            ip_address=ip_address
        )
    
    def log_xml_generation(self, user: str, mode: str, device_count: int, 
                          success: bool = True, error: Optional[str] = None):
        """Log XML generation event"""
        details = {
            'mode': mode,
            'device_count': device_count
        }
        if error:
            details['error'] = error
        
        return self.log_event(
            category=self.CATEGORY_XML,
            action='generate_xml_success' if success else 'generate_xml_failed',
            user=user,
            level=self.LEVEL_INFO if success else self.LEVEL_ERROR,
            details=details
        )
    
    def log_validation(self, user: str, device_name: Optional[str] = None, 
                      total_validated: int = 0, mismatches: int = 0):
        """Log subnet validation run"""
        details = {
            'total_validated': total_validated,
            'mismatches_found': mismatches
        }
        if device_name:
            details['device_name'] = device_name
        
        return self.log_event(
            category=self.CATEGORY_VALIDATION,
            action='validation_completed',
            user=user,
            level=self.LEVEL_WARNING if mismatches > 0 else self.LEVEL_INFO,
            details=details
        )
    
    def log_upload(self, user: str, filename: str, success: bool = True, 
                   error: Optional[str] = None):
        """Log file upload to EVE LI server"""
        details = {'filename': filename}
        if error:
            details['error'] = error
        
        return self.log_event(
            category=self.CATEGORY_UPLOAD,
            action='upload_success' if success else 'upload_failed',
            user=user,
            level=self.LEVEL_INFO if success else self.LEVEL_ERROR,
            details=details
        )
    
    def log_page_view(self, user: str, page: str, ip_address: str):
        """Log page access (optional, can be verbose)"""
        return self.log_event(
            category=self.CATEGORY_VIEW,
            action='view_page',
            user=user,
            level=self.LEVEL_INFO,
            details={'page': page},
            ip_address=ip_address
        )
    
    def log_search(self, user: str, query: str, result_count: int, ip_address: str):
        """Log subnet search"""
        return self.log_event(
            category=self.CATEGORY_SEARCH,
            action='subnet_search',
            user=user,
            level=self.LEVEL_INFO,
            details={'query': query, 'result_count': result_count},
            ip_address=ip_address
        )
    
    # ========================================================================
    # Query Methods
    # ========================================================================
    
    def get_recent_events(self, limit: int = 100, category: Optional[str] = None,
                         user: Optional[str] = None) -> List[Dict]:
        """
        Get recent audit events
        
        Args:
            limit: Maximum number of events to return
            category: Filter by category
            user: Filter by user
        
        Returns:
            List of audit events (most recent first)
        """
        events = self.in_memory_log.copy()
        
        # Apply filters
        if category:
            events = [e for e in events if e['category'] == category]
        if user:
            events = [e for e in events if e['user'] == user]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        return events[:limit]
    
    def get_events_by_timerange(self, start: datetime, end: datetime) -> List[Dict]:
        """Get events within a time range"""
        events = [
            e for e in self.in_memory_log
            if start.isoformat() <= e['timestamp'] <= end.isoformat()
        ]
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        return events
    
    def get_user_activity(self, user: str, limit: int = 50) -> List[Dict]:
        """Get all activities for a specific user"""
        return self.get_recent_events(limit=limit, user=user)
    
    def get_statistics(self) -> Dict:
        """Get audit log statistics"""
        total_events = len(self.in_memory_log)
        
        # Count by category
        category_counts = {}
        user_counts = {}
        level_counts = {}
        
        for event in self.in_memory_log:
            cat = event['category']
            user = event['user']
            level = event['level']
            
            category_counts[cat] = category_counts.get(cat, 0) + 1
            user_counts[user] = user_counts.get(user, 0) + 1
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            'total_events': total_events,
            'by_category': category_counts,
            'by_user': user_counts,
            'by_level': level_counts,
            'oldest_event': self.in_memory_log[0]['timestamp'] if self.in_memory_log else None,
            'newest_event': self.in_memory_log[-1]['timestamp'] if self.in_memory_log else None
        }
    
    # ========================================================================
    # Export Methods
    # ========================================================================
    
    def export_to_csv(self, output_path: str, events: Optional[List[Dict]] = None):
        """
        Export audit log to CSV
        
        Args:
            output_path: Path to output CSV file
            events: Specific events to export (or all if None)
        """
        events = events or self.in_memory_log
        
        if not events:
            logger.warning("No events to export")
            return
        
        fieldnames = ['timestamp', 'category', 'action', 'user', 'level', 
                     'ip_address', 'details']
        
        try:
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for event in events:
                    row = event.copy()
                    row['details'] = json.dumps(row.get('details', {}))
                    writer.writerow(row)
            
            logger.info(f"Exported {len(events)} events to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
    
    def export_to_json(self, output_path: str, events: Optional[List[Dict]] = None):
        """Export audit log to JSON"""
        events = events or self.in_memory_log
        
        try:
            with open(output_path, 'w') as f:
                json.dump(events, f, indent=2)
            
            logger.info(f"Exported {len(events)} events to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")


# ============================================================================
# Singleton Instance
# ============================================================================

_audit_logger_instance = None

def get_audit_logger(demo_mode: bool = True) -> AuditLogger:
    """Get or create global audit logger instance"""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger(demo_mode=demo_mode)
    return _audit_logger_instance


if __name__ == "__main__":
    # Demo test
    logging.basicConfig(level=logging.INFO)
    
    audit = get_audit_logger(demo_mode=True)
    
    print("\n=== Audit Logger Demo ===\n")
    
    # Log some demo events
    audit.log_login('demo.user@example.com', '192.168.1.100', success=True)
    audit.log_xml_generation('demo.user@example.com', 'both', device_count=17)
    audit.log_validation('demo.user@example.com', total_validated=17, mismatches=5)
    audit.log_upload('demo.user@example.com', 'EVE_NL_Infra_CMTS-20260102.xml.gz')
    audit.log_search('demo.user@example.com', '203.80.0.0/22', result_count=1, 
                    ip_address='192.168.1.100')
    audit.log_logout('demo.user@example.com', '192.168.1.100')
    
    # Get statistics
    print("\nStatistics:")
    stats = audit.get_statistics()
    print(json.dumps(stats, indent=2))
    
    # Get recent events
    print("\nRecent Events:")
    for event in audit.get_recent_events(limit=10):
        print(f"  [{event['timestamp']}] {event['category']:15} | "
              f"{event['action']:20} | {event['user']}")
