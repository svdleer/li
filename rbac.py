#!/usr/bin/env python3
"""
Role-Based Access Control (RBAC) Module
========================================

Manages user roles and permissions with MySQL backend:
- Admin: Full access (generate XML, upload, configure, validate)
- Operator: Can generate XML, view validations, cannot upload or configure
- Viewer: Read-only access (view devices, XML status, no actions)

Admin bypass: admin@example.com always has admin access even if DB is down

Author: Silvester van der Leer
Version: 2.2
"""

import logging
import os
import mysql.connector
import bcrypt
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, flash, redirect, url_for, abort
from typing import List, Dict, Optional, Callable

logger = logging.getLogger(__name__)


class Role:
    """User role definitions"""
    ADMIN = 'admin'
    OPERATOR = 'operator'
    VIEWER = 'viewer'
    
    ALL_ROLES = [ADMIN, OPERATOR, VIEWER]


class Permission:
    """Permission definitions"""
    # Read permissions
    VIEW_DASHBOARD = 'view_dashboard'
    VIEW_DEVICES = 'view_devices'
    VIEW_XML_STATUS = 'view_xml_status'
    VIEW_VALIDATION = 'view_validation'
    VIEW_AUDIT_LOG = 'view_audit_log'
    
    # Write permissions
    GENERATE_XML = 'generate_xml'
    UPLOAD_XML = 'upload_xml'
    RUN_VALIDATION = 'run_validation'
    MODIFY_CONFIG = 'modify_config'
    MANAGE_USERS = 'manage_users'
    
    # Search permissions
    SEARCH_SUBNETS = 'search_subnets'


# Role -> Permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        # All permissions
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_DEVICES,
        Permission.VIEW_XML_STATUS,
        Permission.VIEW_VALIDATION,
        Permission.VIEW_AUDIT_LOG,
        Permission.GENERATE_XML,
        Permission.UPLOAD_XML,
        Permission.RUN_VALIDATION,
        Permission.MODIFY_CONFIG,
        Permission.MANAGE_USERS,
        Permission.SEARCH_SUBNETS,
    ],
    Role.OPERATOR: [
        # Can view and generate, but not upload or configure
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_DEVICES,
        Permission.VIEW_XML_STATUS,
        Permission.VIEW_VALIDATION,
        Permission.VIEW_AUDIT_LOG,
        Permission.GENERATE_XML,
        Permission.RUN_VALIDATION,
        Permission.SEARCH_SUBNETS,
    ],
    Role.VIEWER: [
        # Read-only access
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_DEVICES,
        Permission.VIEW_XML_STATUS,
        Permission.VIEW_VALIDATION,
        Permission.SEARCH_SUBNETS,
    ]
}


class RBACManager:
    """Role-Based Access Control Manager with MySQL backend"""
    
    # Bypass admin - always has access even if DB is down
    BYPASS_ADMIN = {
        'email': 'admin@example.com',
        'name': 'System Administrator',
        'role': Role.ADMIN
    }
    
    def __init__(self):
        """Initialize RBAC manager with MySQL connection"""
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'li_cache')
        }
        self.db_available = False
        self._init_database()
        logger.info(f"RBAC Manager initialized (MySQL: {'OK' if self.db_available else 'UNAVAILABLE'})")
    
    def _init_database(self):
        """Initialize database table and default users on first setup"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = 'users'
            """, (self.db_config['database'],))
            table_exists = cursor.fetchone()[0] > 0
            
            # Create users table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    password_hash VARCHAR(255),
                    role ENUM('admin', 'operator', 'viewer') NOT NULL DEFAULT 'viewer',
                    reset_token VARCHAR(255),
                    reset_token_expiry DATETIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_email (email),
                    INDEX idx_role (role),
                    INDEX idx_reset_token (reset_token)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # If table was just created (didn't exist before), insert default users
            if not table_exists:
                logger.info("First-time setup: Creating default users")
                default_users = [
                    ('admin@example.com', 'Admin User', 'admin'),
                    ('operator@example.com', 'Operator User', 'operator'),
                    ('viewer@example.com', 'Viewer User', 'viewer'),
                ]
                for email, name, role in default_users:
                    cursor.execute(
                        "INSERT IGNORE INTO users (email, name, role) VALUES (%s, %s, %s)",
                        (email, name, role)
                    )
            else:
                # Table existed, check if it's empty (user might have deleted all)
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                if user_count == 0:
                    logger.warning("No users found, creating bypass admin only")
                    cursor.execute(
                        "INSERT INTO users (email, name, role) VALUES (%s, %s, %s)",
                        (self.BYPASS_ADMIN['email'], self.BYPASS_ADMIN['name'], self.BYPASS_ADMIN['role'])
                    )
            
            conn.commit()
            cursor.close()
            conn.close()
            self.db_available = True
            logger.info("Users table initialized")
        except Exception as e:
            logger.warning(f"MySQL not available for RBAC, using fallback mode: {e}")
            self.db_available = False
    
    def _get_connection(self):
        """Get database connection"""
        return mysql.connector.connect(**self.db_config)
    
    def get_user_role(self, user_email: str) -> Optional[str]:
        """Get role for a user"""
        # Bypass admin always has access
        if user_email == self.BYPASS_ADMIN['email']:
            return self.BYPASS_ADMIN['role']
        
        # If DB unavailable, deny access except bypass admin
        if not self.db_available:
            logger.warning(f"DB unavailable, denying access to {user_email}")
            return None
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT role FROM users WHERE email = %s", (user_email,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result['role'] if result else None
        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            self.db_available = False
            return None
    
    def get_user_permissions(self, user_email: str) -> List[str]:
        """Get all permissions for a user"""
        role = self.get_user_role(user_email)
        return ROLE_PERMISSIONS.get(role, []) if role else []
    
    def has_permission(self, user_email: str, permission: str) -> bool:
        """Check if user has a specific permission"""
        permissions = self.get_user_permissions(user_email)
        return permission in permissions
    
    def has_any_permission(self, user_email: str, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions"""
        user_permissions = self.get_user_permissions(user_email)
        return any(p in user_permissions for p in permissions)
    
    def has_all_permissions(self, user_email: str, permissions: List[str]) -> bool:
        """Check if user has all of the specified permissions"""
        user_permissions = self.get_user_permissions(user_email)
        return all(p in user_permissions for p in permissions)
    
    def is_admin(self, user_email: str) -> bool:
        """Check if user is admin"""
        return self.get_user_role(user_email) == Role.ADMIN
    
    def is_operator(self, user_email: str) -> bool:
        """Check if user is operator"""
        return self.get_user_role(user_email) == Role.OPERATOR
    
    def is_viewer(self, user_email: str) -> bool:
        """Check if user is viewer"""
        return self.get_user_role(user_email) == Role.VIEWER
    
    def get_all_users(self) -> List[Dict]:
        """Get list of all users"""
        # If DB unavailable, return bypass admin only
        if not self.db_available:
            logger.warning("DB unavailable, returning bypass admin only")
            return [self.BYPASS_ADMIN]
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT email, username, name, role FROM users ORDER BY email")
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            self.db_available = False
            # Return bypass admin as fallback
            return [self.BYPASS_ADMIN]
    
    def add_user(self, email: str, name: str, role: str, password: str = None) -> bool:
        """Add new user"""
        if role not in Role.ALL_ROLES:
            return False
        
        # Hash password if provided
        password_hash = self.hash_password(password) if password else None
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (email, name, role, password_hash) VALUES (%s, %s, %s, %s)",
                (email, name, role, password_hash)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Added user: {email} ({role})")
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def update_user_role(self, email: str, new_role: str) -> bool:
        """Update user role"""
        # Cannot modify bypass admin
        if email == self.BYPASS_ADMIN['email']:
            logger.warning("Cannot modify bypass admin")
            return False
        
        if new_role not in Role.ALL_ROLES:
            return False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET role = %s WHERE email = %s",
                (new_role, email)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Updated user role: {email} -> {new_role}")
            return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def delete_user(self, email: str) -> bool:
        """Delete user"""
        # Cannot delete bypass admin
        if email == self.BYPASS_ADMIN['email']:
            logger.warning("Cannot delete bypass admin")
            return False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email = %s", (email,))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Deleted user: {email}")
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, email: str, password: str) -> bool:
        """Verify user password"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not result or not result.get('password_hash'):
                return False
            
            return bcrypt.checkpw(password.encode('utf-8'), result['password_hash'].encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def set_password(self, email: str, password: str) -> bool:
        """Set user password"""
        try:
            password_hash = self.hash_password(password)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (password_hash, email)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Password updated for user: {email}")
            return True
        except Exception as e:
            logger.error(f"Error setting password: {e}")
            return False
    
    def create_reset_token(self, email: str) -> Optional[str]:
        """Generate and store password reset token"""
        try:
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=24)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE email = %s",
                (token, expiry, email)
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Reset token created for: {email}")
            return token
        except Exception as e:
            logger.error(f"Error creating reset token: {e}")
            return None
    
    def verify_reset_token(self, token: str) -> Optional[str]:
        """Verify reset token and return email if valid"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT email FROM users WHERE reset_token = %s AND reset_token_expiry > NOW()",
                (token,)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return result['email'] if result else None
        except Exception as e:
            logger.error(f"Error verifying reset token: {e}")
            return None
    
    def clear_reset_token(self, email: str) -> bool:
        """Clear reset token after use"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET reset_token = NULL, reset_token_expiry = NULL WHERE email = %s",
                (email,)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error clearing reset token: {e}")
            return False


# ============================================================================
# Flask Decorators for Permission Checking
# ============================================================================

_rbac_manager_instance = None

def get_rbac_manager() -> RBACManager:
    """Get or create global RBAC manager instance"""
    global _rbac_manager_instance
    if _rbac_manager_instance is None:
        _rbac_manager_instance = RBACManager()
    return _rbac_manager_instance


def require_permission(permission: str, redirect_to: str = 'dashboard'):
    """
    Decorator to require specific permission
    
    Usage:
        @app.route('/admin/config')
        @require_permission(Permission.MODIFY_CONFIG)
        def admin_config():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get('user')
            if not user:
                flash("Please log in to access this page", "warning")
                return redirect(url_for('login'))
            
            rbac = get_rbac_manager()
            user_email = user.get('email', user.get('preferred_username', ''))
            
            if not rbac.has_permission(user_email, permission):
                flash("You don't have permission to access this page", "danger")
                return redirect(url_for(redirect_to))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(role: str, redirect_to: str = 'dashboard'):
    """
    Decorator to require specific role
    
    Usage:
        @app.route('/admin')
        @require_role(Role.ADMIN)
        def admin_page():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get('user')
            if not user:
                flash("Please log in to access this page", "warning")
                return redirect(url_for('login'))
            
            rbac = get_rbac_manager()
            user_email = user.get('email', user.get('preferred_username', ''))
            user_role = rbac.get_user_role(user_email)
            
            if user_role != role:
                flash(f"Admin access required", "danger")
                return redirect(url_for(redirect_to))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_permission(permission: str) -> bool:
    """
    Check if current session user has permission
    
    Usage in templates:
        {% if check_permission('generate_xml') %}
            <button>Generate XML</button>
        {% endif %}
    """
    user = session.get('user')
    if not user:
        return False
    
    rbac = get_rbac_manager()
    user_email = user.get('email', user.get('preferred_username', ''))
    return rbac.has_permission(user_email, permission)


if __name__ == "__main__":
    # Demo test
    logging.basicConfig(level=logging.INFO)
    
    rbac = get_rbac_manager(demo_mode=True)
    
    print("\n=== RBAC Manager Demo ===\n")
    
    # Test each user role
    for email in ['admin@example.com', 'operator@example.com', 'viewer@example.com']:
        role = rbac.get_user_role(email)
        permissions = rbac.get_user_permissions(email)
        
        print(f"\n{email} ({role}):")
        print(f"  Permissions: {len(permissions)}")
        print(f"  Can generate XML: {rbac.has_permission(email, Permission.GENERATE_XML)}")
        print(f"  Can upload XML: {rbac.has_permission(email, Permission.UPLOAD_XML)}")
        print(f"  Can modify config: {rbac.has_permission(email, Permission.MODIFY_CONFIG)}")
