#!/usr/bin/env python3
"""
Role-Based Access Control (RBAC) Module
========================================

Manages user roles and permissions:
- Admin: Full access (generate XML, upload, configure, validate)
- Operator: Can generate XML, view validations, cannot upload or configure
- Viewer: Read-only access (view devices, XML status, no actions)

Author: Silvester van der Leer
Version: 2.0
"""

import logging
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
    """Role-Based Access Control Manager"""
    
    def __init__(self, demo_mode: bool = True):
        """
        Initialize RBAC manager
        
        Args:
            demo_mode: If True, use demo user database
        """
        self.demo_mode = demo_mode
        
        if demo_mode:
            # Demo users with different roles
            self.users = {
                'admin@example.com': {
                    'name': 'Admin User',
                    'email': 'admin@example.com',
                    'role': Role.ADMIN
                },
                'operator@example.com': {
                    'name': 'Operator User',
                    'email': 'operator@example.com',
                    'role': Role.OPERATOR
                },
                'viewer@example.com': {
                    'name': 'Viewer User',
                    'email': 'viewer@example.com',
                    'role': Role.VIEWER
                },
                # Default demo user is operator
                'demo.user@example.com': {
                    'name': 'Demo User',
                    'email': 'demo.user@example.com',
                    'role': Role.OPERATOR
                }
            }
        else:
            # In production, this would query a database
            self.users = {}
        
        logger.info(f"RBAC Manager initialized ({len(self.users)} demo users)")
    
    def get_user_role(self, user_email: str) -> Optional[str]:
        """Get role for a user"""
        user = self.users.get(user_email)
        return user['role'] if user else None
    
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
        """Get list of all users (admin only)"""
        return list(self.users.values())


# ============================================================================
# Flask Decorators for Permission Checking
# ============================================================================

_rbac_manager_instance = None

def get_rbac_manager(demo_mode: bool = True) -> RBACManager:
    """Get or create global RBAC manager instance"""
    global _rbac_manager_instance
    if _rbac_manager_instance is None:
        _rbac_manager_instance = RBACManager(demo_mode=demo_mode)
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
