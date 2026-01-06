#!/usr/bin/env python3
"""
EVE LI Web Application
======================

Flask-based web interface for EVE LI XML Generator with:
- Office 365 authentication
- Device management
- XML status monitoring
- Health checks
- Manual XML generation and push

Author: Silvester van der Leer
Version: 2.0
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
import uuid

from flask import Flask, render_template, redirect, url_for, session, request, jsonify, flash, send_file
from flask_session import Session
import msal
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
import pytz

# Import our modules
from netshot_api import get_netshot_client
from dhcp_integration import get_dhcp_integration
from eve_li_xml_generator_v2 import EVEXMLGeneratorV2
from audit_logger import get_audit_logger
from rbac import get_rbac_manager, require_permission, check_permission, Role, Permission, ROLE_PERMISSIONS
from config_manager import get_config_manager
import bcrypt

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', str(uuid.uuid4()))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_FILE_DIR'] = Path('.flask_session')
app.config['SESSION_FILE_DIR'].mkdir(exist_ok=True)

Session(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('eve_li_webapp')

# Initialize APScheduler with MySQL persistence
mysql_host = os.getenv('MYSQL_HOST', 'localhost')
mysql_port = os.getenv('MYSQL_PORT', '3306')
mysql_user = os.getenv('MYSQL_USER', 'root')
mysql_password = os.getenv('MYSQL_PASSWORD', '')
mysql_database = os.getenv('MYSQL_DATABASE', 'dhcp_validation_cache')

mysql_url = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}'
jobstores = {
    'default': SQLAlchemyJobStore(url=mysql_url)
}
task_scheduler = BackgroundScheduler(jobstores=jobstores, timezone=pytz.UTC)
task_scheduler.start()
logger.info("APScheduler started with MySQL job store")

# Azure AD / Office 365 Configuration
AUTHORITY = os.getenv('AZURE_AUTHORITY', 'https://login.microsoftonline.com/common')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET', '')
REDIRECT_PATH = "/auth/callback"
SCOPE = ["User.Read"]  # Basic user profile

# Application configuration
APP_TITLE = os.getenv('APP_TITLE', 'EVE LI XML Generator')
APP_VERSION = "2.0"


def _build_msal_app(cache=None, authority=None):
    """Build MSAL confidential client application"""
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=authority or AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache
    )


def _build_auth_url(authority=None, scopes=None, state=None):
    """Build authorization URL for OAuth flow"""
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=url_for("authorized", _external=True)
    )


# Scheduled task functions
def run_cache_warmer():
    """Run cache warmer task"""
    try:
        logger.info("Running cache warmer task...")
        from cache_warmer import warm_device_validation_cache
        warm_device_validation_cache()
        logger.info("Cache warmer task completed")
        
        # Log to audit
        audit = get_audit_logger()
        audit.log(
            username='system',
            category=audit.CATEGORY_CACHE_REFRESH,
            action='Cache Warmer completed successfully',
            details='Refreshed device and subnet validation cache',
            ip_address='127.0.0.1'
        )
    except Exception as e:
        logger.error(f"Cache warmer task failed: {e}")
        # Log failure to audit
        audit = get_audit_logger()
        audit.log(
            username='system',
            category=audit.CATEGORY_CACHE_REFRESH,
            action='Cache Warmer failed',
            details=str(e),
            ip_address='127.0.0.1'
        )


def run_dhcp_cache():
    """Run DHCP cache refresh task"""
    try:
        logger.info("Running DHCP cache refresh task...")
        from dhcp_cache_warmer import warm_dhcp_cache
        warm_dhcp_cache()
        logger.info("DHCP cache refresh task completed")
        
        # Log to audit
        audit = get_audit_logger()
        audit.log(
            username='system',
            category=audit.CATEGORY_CACHE_REFRESH,
            action='DHCP Cache Refresh completed successfully',
            details='Refreshed DHCP subnet cache',
            ip_address='127.0.0.1'
        )
    except Exception as e:
        logger.error(f"DHCP cache refresh task failed: {e}")
        # Log failure to audit
        audit = get_audit_logger()
        audit.log(
            username='system',
            category=audit.CATEGORY_CACHE_REFRESH,
            action='DHCP Cache Refresh failed',
            details=str(e),
            ip_address='127.0.0.1'
        )


def run_xml_generation():
    """Run XML generation and upload task"""
    try:
        logger.info("Running XML generation task...")
        from eve_li_xml_generator_v2 import EVEXMLGeneratorV2
        
        generator = EVEXMLGeneratorV2()
        
        # Generate both CMTS and PE
        cmts_result = generator.process_vfz_devices()
        pe_result = generator.process_pe_devices()
        
        if cmts_result.get('success') and pe_result.get('success'):
            logger.info("XML generation task completed successfully")
            
            # Log to audit
            audit = get_audit_logger()
            audit.log(
                username='system',
                category=audit.CATEGORY_XML_GENERATE,
                action='XML Generation completed successfully',
                details=f"Generated CMTS ({cmts_result.get('device_count')} devices) and PE ({pe_result.get('device_count')} devices) XML files",
                ip_address='127.0.0.1'
            )
        else:
            error_msg = f"CMTS: {cmts_result.get('message')}, PE: {pe_result.get('message')}"
            logger.error(f"XML generation task failed: {error_msg}")
            # Log failure to audit
            audit = get_audit_logger()
            audit.log(
                username='system',
                category=audit.CATEGORY_XML_GENERATE,
                action='XML Generation failed',
                details='Failed to generate XML files',
                ip_address='127.0.0.1'
            )
    except Exception as e:
        logger.error(f"XML generation task failed: {e}")
        # Log failure to audit
        audit = get_audit_logger()
        audit.log(
            username='system',
            category=audit.CATEGORY_XML_GENERATE,
            action='XML Generation failed',
            details=str(e),
            ip_address='127.0.0.1'
        )


# Initialize default scheduled jobs
def init_scheduled_jobs():
    """Initialize default scheduled jobs"""
    try:
        # Cache warmer: Daily at midnight
        if not task_scheduler.get_job('cache_warmer'):
            task_scheduler.add_job(
                func=run_cache_warmer,
                trigger=CronTrigger(hour=0, minute=0),
                id='cache_warmer',
                name='Cache Warmer',
                replace_existing=True
            )
            logger.info("Scheduled: Cache Warmer (daily at midnight)")
        
        # DHCP cache: Every 30 minutes
        if not task_scheduler.get_job('dhcp_cache'):
            task_scheduler.add_job(
                func=run_dhcp_cache,
                trigger=CronTrigger(minute='*/30'),
                id='dhcp_cache',
                name='DHCP Cache Refresh',
                replace_existing=True
            )
            logger.info("Scheduled: DHCP Cache Refresh (every 30 minutes)")
        
        # XML Generation: Configurable (default: disabled)
        # Enable by setting in GUI or adding cron schedule
        xml_enabled = os.getenv('XML_GENERATION_ENABLED', 'false').lower() == 'true'
        xml_cron = os.getenv('XML_GENERATION_CRON', '0 9 * * 1-5')  # Default: 9 AM weekdays
        
        if xml_enabled and not task_scheduler.get_job('xml_generation'):
            # Parse cron: minute hour day month day_of_week
            parts = xml_cron.split()
            if len(parts) == 5:
                task_scheduler.add_job(
                    func=run_xml_generation,
                    trigger=CronTrigger(
                        minute=parts[0],
                        hour=parts[1],
                        day=parts[2],
                        month=parts[3],
                        day_of_week=parts[4]
                    ),
                    id='xml_generation',
                    name='XML Generation & Upload',
                    replace_existing=True
                )
                logger.info(f"Scheduled: XML Generation ({xml_cron})")
    except Exception as e:
        logger.error(f"Failed to initialize scheduled jobs: {e}")


# Initialize jobs on startup
init_scheduled_jobs()


def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Bypass authentication in debug mode for local testing
        if app.debug:
            if not session.get("user"):
                # Create a fake user session for local testing (bypass admin)
                session["user"] = {
                    "name": "System Administrator",
                    "preferred_username": "admin@example.com",
                    "email": "admin@example.com"
                }
                logger.info("Debug mode: Using local dev user session")
        
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# Authentication Routes
# ============================================================================

@app.route("/login")
def login():
    """Show login form"""
    # For local development with debug, skip to form
    if app.debug:
        return render_template("login_form.html", app_title=APP_TITLE)
    
    # Production: Show login form with O365 option
    return render_template("login_form.html", app_title=APP_TITLE)


@app.route("/login/submit", methods=["POST"])
def login_submit():
    """Handle login form submission"""
    username = request.form.get("username")
    password = request.form.get("password")
    
    if not username or not password:
        flash("Username/email and password are required", "danger")
        return redirect(url_for("login"))
    
    rbac = get_rbac_manager()
    
    # Try to find user by username or email
    users = rbac.get_all_users()
    user = next((u for u in users if u.get('username') == username or u['email'] == username), None)
    
    if user and rbac.verify_password(user['email'], password):
        session["user"] = {
            "name": user['name'],
            "preferred_username": user.get('username') or user['email'],
            "email": user['email']
        }
        logger.info(f"User logged in: {user.get('username') or user['email']}")
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("index"))
    
    flash("Invalid username/email or password", "danger")
    return redirect(url_for("login"))


@app.route("/login/o365")
def login_o365():
    """Initiate OAuth login flow"""
    session["state"] = str(uuid.uuid4())
    auth_url = _build_auth_url(scopes=SCOPE, state=session["state"])
    return redirect(auth_url)


@app.route("/forgot-password")
def forgot_password():
    """Show forgot password form"""
    return render_template("forgot_password.html", app_title=APP_TITLE)


@app.route("/forgot-password/submit", methods=["POST"])
def forgot_password_submit():
    """Handle forgot password form"""
    email = request.form.get("email")
    
    if not email:
        flash("Email is required", "danger")
        return redirect(url_for("forgot_password"))
    
    rbac = get_rbac_manager()
    
    # Check if user exists
    users = rbac.get_all_users()
    user = next((u for u in users if u['email'] == email), None)
    
    if user:
        # Generate reset token
        token = rbac.create_reset_token(email)
        
        if token:
            # Send email with reset link
            from email_notifier import EmailNotifier
            notifier = EmailNotifier()
            
            reset_url = url_for('reset_password', token=token, _external=True)
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Password Reset Request</h2>
                <p>Hello {user['name']},</p>
                <p>We received a request to reset your password. Click the link below to reset it:</p>
                <p style="margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                        Reset Password
                    </a>
                </p>
                <p>This link will expire in 24 hours.</p>
                <p>If you didn't request this, please ignore this email.</p>
                <hr style="margin: 30px 0;">
                <small style="color: #666;">EVE LI XML Generator - VodafoneZiggo</small>
            </body>
            </html>
            """
            
            text_body = f"""
            Password Reset Request
            
            Hello {user['name']},
            
            We received a request to reset your password.
            
            Reset link: {reset_url}
            
            This link will expire in 24 hours.
            
            If you didn't request this, please ignore this email.
            """
            
            notifier.send_email(
                subject="Password Reset Request - EVE LI XML Generator",
                html_body=html_body,
                text_body=text_body
            )
    
    # Always show success message (security: don't reveal if email exists)
    flash("If an account exists with that email, a password reset link has been sent.", "info")
    return redirect(url_for("login"))


@app.route("/reset-password/<token>")
def reset_password(token):
    """Show reset password form"""
    rbac = get_rbac_manager()
    email = rbac.verify_reset_token(token)
    
    if not email:
        flash("Invalid or expired reset link", "danger")
        return redirect(url_for("login"))
    
    return render_template("reset_password.html", token=token, app_title=APP_TITLE)


@app.route("/reset-password/<token>/submit", methods=["POST"])
def reset_password_submit(token):
    """Handle reset password form"""
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    
    if not password or not confirm_password:
        flash("Both password fields are required", "danger")
        return redirect(url_for("reset_password", token=token))
    
    if password != confirm_password:
        flash("Passwords do not match", "danger")
        return redirect(url_for("reset_password", token=token))
    
    if len(password) < 8:
        flash("Password must be at least 8 characters", "danger")
        return redirect(url_for("reset_password", token=token))
    
    rbac = get_rbac_manager()
    email = rbac.verify_reset_token(token)
    
    if not email:
        flash("Invalid or expired reset link", "danger")
        return redirect(url_for("login"))
    
    # Set new password
    if rbac.set_password(email, password):
        rbac.clear_reset_token(email)
        flash("Password reset successfully! You can now log in.", "success")
        logger.info(f"Password reset completed for: {email}")
    else:
        flash("Failed to reset password. Please try again.", "danger")
    
    return redirect(url_for("login"))


@app.route("/auth/callback")
def authorized():
    """Handle OAuth callback"""
    if request.args.get('state') != session.get("state"):
        return redirect(url_for("index"))
    
    if "error" in request.args:
        logger.error(f"Authentication error: {request.args.get('error')}")
        flash(f"Authentication failed: {request.args.get('error')}", "danger")
        return redirect(url_for("index"))
    
    if request.args.get('code'):
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=SCOPE,
            redirect_uri=url_for("authorized", _external=True)
        )
        
        if "error" in result:
            logger.error(f"Token acquisition error: {result.get('error')}")
            flash(f"Login failed: {result.get('error')}", "danger")
            return redirect(url_for("index"))
        
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
        
        username = session['user'].get('preferred_username')
        logger.info(f"User logged in: {username}")
        
        # Audit log
        audit = get_audit_logger()
        audit.log(
            username=username,
            category=audit.CATEGORY_LOGIN,
            action='User logged in successfully',
            ip_address=request.remote_addr
        )
        
        flash(f"Welcome, {session['user'].get('name')}!", "success")
    
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    """Logout user"""
    username = session.get("user", {}).get("preferred_username", "Unknown")
    
    # Audit log
    audit = get_audit_logger()
    audit.log(
        username=username,
        category=audit.CATEGORY_LOGOUT,
        action='User logged out',
        ip_address=request.remote_addr
    )
    
    session.clear()
    logger.info(f"User logged out: {username}")
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


def check_permission(permission):
    """Check if user has permission (debug mode: always True)"""
    if app.debug:
        return True
    # TODO: Implement RBAC when O365 is enabled
    return True


# Make check_permission available in templates
app.jinja_env.globals['check_permission'] = check_permission


def _load_cache():
    """Load token cache from session"""
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache


def _save_cache(cache):
    """Save token cache to session"""
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()


def check_permission(permission):
    """
    Check if current user has permission
    """
    if not session.get("user"):
        return False
    
    user_email = session['user'].get('email', session['user'].get('preferred_username'))
    rbac = get_rbac_manager()
    
    # Map permission strings to Permission constants
    permission_map = {
        'view_dashboard': Permission.VIEW_DASHBOARD,
        'view_devices': Permission.VIEW_DEVICES,
        'view_xml_status': Permission.VIEW_XML_STATUS,
        'view_validation': Permission.VIEW_VALIDATION,
        'view_audit_log': Permission.VIEW_AUDIT_LOG,
        'generate_xml': Permission.GENERATE_XML,
        'upload_xml': Permission.UPLOAD_XML,
        'run_validation': Permission.RUN_VALIDATION,
        'modify_config': Permission.MODIFY_CONFIG,
        'manage_users': Permission.MANAGE_USERS,
        'search_subnets': Permission.SEARCH_SUBNETS
    }
    
    perm = permission_map.get(permission, permission)
    return rbac.has_permission(user_email, perm)


# Make check_permission available in all templates
@app.context_processor
def inject_permissions():
    """Inject permission checker into all templates"""
    return dict(check_permission=check_permission)


@app.context_processor
def inject_system_status():
    """Inject system status into all templates"""
    if not session.get('user'):
        return dict(netshot_available=True, mysql_available=True)
    
    # Quick check - only when user is logged in
    netshot_client = get_netshot_client()
    netshot_available = netshot_client.test_connection()
    
    mysql_available = False
    try:
        from app_cache import AppCache
        cache = AppCache()
        mysql_available = cache.connect()
        if mysql_available:
            cache.disconnect()
    except Exception:
        pass
    
    return dict(
        netshot_available=netshot_available,
        mysql_available=mysql_available,
        system_critical=(not netshot_available or not mysql_available)
    )


# ============================================================================
# Main Application Routes
# ============================================================================

@app.route("/setup", methods=["GET", "POST"])
def setup():
    """Initial setup wizard"""
    config_mgr = get_config_manager()
    
    # If already initialized, redirect to dashboard
    if config_mgr.is_app_initialized():
        return redirect(url_for('index'))
    
    if request.method == "POST":
        try:
            # Get current user (should be admin)
            username = session.get("user", {}).get("name", "setup")
            
            # Save all settings
            settings_to_save = [
                'mysql_host', 'mysql_port', 'mysql_user', 'mysql_password', 'mysql_database',
                'netshot_url', 'netshot_api_key', 'netshot_cmts_group', 'netshot_pe_group'
            ]
            
            for setting_key in settings_to_save:
                value = request.form.get(setting_key, '')
                config_mgr.set_setting(setting_key, value, username)
            
            # Mark app as initialized
            config_mgr.mark_app_initialized(username)
            
            flash("Configuration saved successfully! Please log in to continue.", "success")
            logger.info(f"Initial setup completed by {username}")
            
            # Clear session and redirect to login
            session.clear()
            return redirect(url_for('login'))
            
        except Exception as e:
            logger.error(f"Error saving setup configuration: {e}")
            flash(f"Error saving configuration: {str(e)}", "danger")
    
    # GET: show setup form
    settings = config_mgr.get_all_settings()
    return render_template("setup.html", 
                         settings=settings,
                         app_title=APP_TITLE)


@app.route("/")
def index():
    """Home page / Dashboard"""
    # Check if app needs setup
    config_mgr = get_config_manager()
    if not config_mgr.is_app_initialized():
        return redirect(url_for('setup'))
    
    return render_template("index.html", 
                         user=session.get("user"),
                         app_title=APP_TITLE,
                         app_version=APP_VERSION)


@app.route("/audit-log")
@login_required
def audit_log_page():
    """Audit log page"""
    try:
        audit = get_audit_logger()
        
        # Get filters from query params
        category = request.args.get('category', '')
        user = request.args.get('user', '')
        level = request.args.get('level', '')
        page = int(request.args.get('page', 1))
        per_page = 50
        
        # Get logs
        logs = audit.get_logs(
            category=category if category else None,
            username=user if user else None,
            level=level if level else None,
            limit=per_page,
            offset=(page - 1) * per_page
        )
        
        # Get stats
        stats = audit.get_stats()
        
        return render_template("audit_log.html",
                             user=session.get("user"),
                             app_title=APP_TITLE,
                             events=logs,
                             total_logs=stats['total_events'],
                             stats=stats,
                             current_category=category,
                             current_user=user,
                             current_level=level)
    except Exception as e:
        logger.error(f"Error loading audit log: {e}")
        return render_template("audit_log.html",
                             user=session.get("user"),
                             app_title=APP_TITLE,
                             events=[],
                             total_logs=0,
                             stats={'total_events': 0, 'by_category': {}, 'by_level': {}},
                             current_category='',
                             current_user='',
                             current_level='')


@app.route("/api/audit/export")
@login_required
def api_audit_export():
    """Export audit logs in CSV or JSON format"""
    try:
        audit = get_audit_logger()
        
        format_type = request.args.get('format', 'csv')
        category = request.args.get('category', '')
        user = request.args.get('user', '')
        level = request.args.get('level', '')
        
        # Get logs
        logs = audit.get_logs(
            category=category if category else None,
            username=user if user else None,
            level=level if level else None,
            limit=10000  # Export up to 10k logs
        )
        
        if format_type == 'csv':
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['Timestamp', 'User', 'Category', 'Action', 'Details', 'Level', 'IP Address'])
            
            for log in logs:
                writer.writerow([
                    log.get('timestamp', ''),
                    log.get('username', ''),
                    log.get('category', ''),
                    log.get('action', ''),
                    log.get('details', ''),
                    log.get('level', ''),
                    log.get('ip_address', '')
                ])
            
            return output.getvalue(), 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename=audit_log_{category or "all"}.csv'
            }
        else:  # JSON
            return jsonify({
                'success': True,
                'logs': logs,
                'count': len(logs)
            })
            
    except Exception as e:
        logger.error(f"Error exporting audit logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/settings", methods=["GET", "POST"])
@login_required
@require_permission(Permission.MODIFY_CONFIG)
def settings_page():
    """Application settings page (admin only)"""
    config_mgr = get_config_manager()
    
    if request.method == "POST":
        try:
            username = session.get("user", {}).get("name", "admin")
            
            # Update settings
            settings_to_update = [
                'mysql_host', 'mysql_port', 'mysql_user', 'mysql_password', 'mysql_database',
                'cache_host', 'cache_port', 'cache_user', 'cache_password', 'cache_database',
                'netshot_url', 'netshot_api_key', 'netshot_cmts_group', 'netshot_pe_group'
            ]
            
            for setting_key in settings_to_update:
                value = request.form.get(setting_key, '')
                config_mgr.set_setting(setting_key, value, username)
            
            # Clear cache to force reload
            config_mgr.clear_cache()
            
            flash("Settings updated successfully!", "success")
            logger.info(f"Settings updated by {username}")
            
            # Audit log
            audit = get_audit_logger()
            audit.log(
                username=username,
                category=audit.CATEGORY_CONFIG_CHANGE,
                action="Updated application settings"
            )
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            flash(f"Error updating settings: {str(e)}", "danger")
    
    # Get all settings
    settings = config_mgr.get_all_settings()
    logger.info(f"Retrieved {len(settings)} settings from database")
    
    # Add environment variable fallbacks for display
    env_defaults = {
        'mysql_host': os.getenv('MYSQL_HOST', 'localhost'),
        'mysql_port': os.getenv('MYSQL_PORT', '3306'),
        'mysql_user': os.getenv('MYSQL_USER', 'access'),
        'mysql_password': os.getenv('MYSQL_PASSWORD', ''),
        'mysql_database': os.getenv('MYSQL_DATABASE', 'access'),
        'cache_host': os.getenv('CACHE_HOST', 'localhost'),
        'cache_port': os.getenv('CACHE_PORT', '3306'),
        'cache_user': os.getenv('CACHE_USER', 'access'),
        'cache_password': os.getenv('CACHE_PASSWORD', ''),
        'cache_database': os.getenv('CACHE_DATABASE', 'li_xml'),
        'netshot_url': os.getenv('NETSHOT_API_URL', 'https://netshot.oss.local/api'),
        'netshot_api_key': os.getenv('NETSHOT_API_KEY', ''),
        'netshot_cmts_group': os.getenv('NETSHOT_CMTS_GROUP', '207'),
        'netshot_pe_group': os.getenv('NETSHOT_PE_GROUP', '205')
    }
    
    # Use database value if exists, otherwise use env default
    for key, env_default in env_defaults.items():
        if key in settings:
            if not settings[key]['value']:
                settings[key]['value'] = env_default
                logger.debug(f"Prefilled {key} with env default: {env_default if 'password' not in key else '***'}")
        else:
            # Setting doesn't exist in DB yet, create it with env default
            settings[key] = {
                'value': env_default,
                'type': 'password' if 'password' in key or 'key' in key else 'string',
                'description': f'{key} from environment',
                'is_required': True,
                'updated_at': None,
                'updated_by': None
            }
            logger.debug(f"Created setting {key} with env default")
    
    return render_template("settings.html",
                         user=session.get("user"),
                         app_title=APP_TITLE,
                         settings=settings)


@app.route("/user-management")
@login_required
@require_permission(Permission.MANAGE_USERS)
def user_management():
    """User management page"""
    rbac = get_rbac_manager()
    users = rbac.get_all_users()
    
    return render_template("user_management.html",
                         user=session.get("user"),
                         app_title=APP_TITLE,
                         users=users,
                         all_roles=Role.ALL_ROLES,
                         role_permissions=ROLE_PERMISSIONS)


@app.route("/api/users", methods=["GET"])
@login_required
@require_permission(Permission.MANAGE_USERS)
def api_get_users():
    """API endpoint to get all users"""
    try:
        rbac = get_rbac_manager()
        users = rbac.get_all_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/users/<email>", methods=["PUT", "PATCH"])
@login_required
@require_permission(Permission.MANAGE_USERS)
def api_update_user(email):
    """API endpoint to update user (role or name)"""
    try:
        rbac = get_rbac_manager()
        data = request.json
        
        # Handle role update
        if 'role' in data:
            new_role = data.get('role')
            if new_role not in Role.ALL_ROLES:
                return jsonify({'success': False, 'error': 'Invalid role'}), 400
            
            if not rbac.update_user_role(email, new_role):
                return jsonify({'success': False, 'error': 'Failed to update user'}), 500
            
            # Audit log
            audit = get_audit_logger()
            audit.log(
                username=session['user'].get('preferred_username'),
                category=audit.CATEGORY_CONFIG_CHANGE,
                action=f'Updated user role: {email}',
                details=f'New role: {new_role}',
                ip_address=request.remote_addr
            )
            
            return jsonify({'success': True, 'message': 'User updated successfully'})
        
        # Handle name and/or email and/or username update
        if 'name' in data or 'email' in data or 'username' in data:
            name = data.get('name')
            new_email = data.get('email')
            username = data.get('username')
            
            if not name:
                return jsonify({'success': False, 'error': 'Name is required'}), 400
            
            # Build update query dynamically
            conn = rbac._get_connection()
            cursor = conn.cursor()
            
            if new_email and new_email != email:
                # Update email, name, and username
                cursor.execute(
                    "UPDATE users SET email = %s, name = %s, username = %s WHERE email = %s",
                    (new_email, name, username, email)
                )
                details = f'Changed email to: {new_email}, name to: {name}, username to: {username or "None"}'
                
                # Update session if editing yourself
                current_user_email = session['user'].get('email', session['user'].get('preferred_username'))
                if email == current_user_email:
                    session['user']['email'] = new_email
                    session['user']['preferred_username'] = username or new_email
            else:
                # Update name and username only
                cursor.execute(
                    "UPDATE users SET name = %s, username = %s WHERE email = %s",
                    (name, username, email)
                )
                details = f'Changed name to: {name}, username to: {username or "None"}'
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Audit log
            audit = get_audit_logger()
            audit.log(
                username=session['user'].get('preferred_username'),
                category=audit.CATEGORY_CONFIG_CHANGE,
                action=f'Updated user: {email}',
                details=details,
                ip_address=request.remote_addr
            )
            
            return jsonify({'success': True, 'message': 'User updated successfully'})
        
        return jsonify({'success': False, 'error': 'No updates provided'}), 400
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/users", methods=["POST"])
@login_required
@require_permission(Permission.MANAGE_USERS)
def api_add_user():
    """API endpoint to add new user with auto-generated password"""
    try:
        import secrets
        import string
        
        rbac = get_rbac_manager()
        data = request.json
        
        email = data.get('email')
        username = data.get('username')
        name = data.get('name')
        role = data.get('role')
        
        if not email or not name or not role:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Generate secure random password
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(alphabet) for i in range(16))
        
        # Add user with username
        conn = rbac._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, username, name, role, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (email, username, name, role, rbac.hash_password(password))
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        # Audit log
        audit = get_audit_logger()
        audit.log(
            username=session['user'].get('preferred_username'),
            category=audit.CATEGORY_CONFIG_CHANGE,
            action=f'Added new user: {email}',
            details=f'Role: {role}',
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True, 
            'message': 'User added successfully',
            'password': password  # Return generated password
        })
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/users/<email>/reset-password", methods=["POST"])
@login_required
@require_permission(Permission.MANAGE_USERS)
def api_reset_user_password(email):
    """API endpoint to reset user password"""
    try:
        import secrets
        import string
        
        rbac = get_rbac_manager()
        
        # Generate secure random password
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(alphabet) for i in range(16))
        
        if not rbac.set_password(email, password):
            return jsonify({'success': False, 'error': 'Failed to reset password'}), 500
        
        # Audit log
        audit = get_audit_logger()
        audit.log(
            username=session['user'].get('preferred_username'),
            category=audit.CATEGORY_CONFIG_CHANGE,
            action=f'Reset password for user: {email}',
            details='',
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True, 
            'message': 'Password reset successfully',
            'password': password  # Return generated password
        })
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/users/<email>", methods=["DELETE"])
@login_required
@require_permission(Permission.MANAGE_USERS)
def api_delete_user(email):
    """API endpoint to delete user"""
    try:
        rbac = get_rbac_manager()
        
        # Prevent deleting yourself
        current_user_email = session['user'].get('email', session['user'].get('preferred_username'))
        if email == current_user_email:
            return jsonify({'success': False, 'error': 'Cannot delete yourself'}), 400
        
        if not rbac.delete_user(email):
            return jsonify({'success': False, 'error': 'Failed to delete user (may be protected)'}), 400
        
        # Audit log
        audit = get_audit_logger()
        audit.log(
            username=session['user'].get('preferred_username'),
            category=audit.CATEGORY_CONFIG_CHANGE,
            action=f'Deleted user: {email}',
            details='',
            ip_address=request.remote_addr
        )
        
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/search")
@login_required
def search_page():
    """Search for IP/subnet across devices and show DHCP/XML status"""
    query = request.args.get('q', '').strip()
    results = []
    
    if query:
        try:
            netshot_client = get_netshot_client()
            
            # Get all devices (CMTS and PE)
            cmts_devices = netshot_client.get_cmts_devices()
            pe_devices = netshot_client.get_pe_devices()
            all_devices = cmts_devices + pe_devices
            
            logger.info(f"Search query: '{query}', checking {len(all_devices)} devices")
            
            # Search through devices for matching subnets
            import ipaddress
            for device in all_devices:
                device_name = device.get('name', '')
                device_type = 'CMTS' if device in cmts_devices else 'PE'
                subnets = device.get('subnets', [])
                
                # Check if query matches any subnet (exact, partial match, or IP in subnet)
                matching_subnets = []
                for s in subnets:
                    # String match (partial or exact)
                    if query in s:
                        matching_subnets.append(s)
                    else:
                        # Try IP address match (check if query IP is in subnet)
                        try:
                            query_ip = ipaddress.ip_address(query)
                            subnet_network = ipaddress.ip_network(s, strict=False)
                            if query_ip in subnet_network:
                                matching_subnets.append(s)
                        except:
                            pass
                
                if matching_subnets:
                    logger.info(f"Found {len(matching_subnets)} matches in {device_name}: {matching_subnets[:3]}")
                    
                    # Extract vendor from family (e.g., "Arris E6000" -> "Arris")
                    family = device.get('family', 'Unknown')
                    vendor = family.split()[0] if family and family != 'Unknown' else 'Unknown'
                    
                    # Get DHCP validation status
                    dhcp_status = 'Unknown'
                    in_dhcp = False
                    
                    if device_type == 'CMTS':
                        # Check DHCP validation cache
                        try:
                            from dhcp_database import DHCPDatabase
                            dhcp_db = DHCPDatabase()
                            if dhcp_db.connect():
                                cursor = dhcp_db.connection.cursor()
                                cursor.execute(
                                    f"SELECT matched, missing_in_dhcp FROM {dhcp_db.cache_database}.dhcp_validation_cache WHERE device_name = %s",
                                    (device_name,)
                                )
                                row = cursor.fetchone()
                                cursor.close()
                                dhcp_db.disconnect()
                                
                                if row:
                                    import json
                                    matched = json.loads(row['matched']) if row['matched'] else []
                                    missing = json.loads(row['missing_in_dhcp']) if row['missing_in_dhcp'] else []
                                    
                                    # Check if any matching subnet is in DHCP
                                    for subnet in matching_subnets:
                                        if subnet in matched:
                                            in_dhcp = True
                                            dhcp_status = 'Connected'
                                            break
                                        elif subnet in missing:
                                            dhcp_status = 'Missing'
                        except Exception as e:
                            logger.error(f"Error checking DHCP status: {e}")
                    
                    logger.info(f"Adding result for {device_name}: {len(matching_subnets)} subnets, DHCP: {dhcp_status}")
                    results.append({
                        'device_name': device_name,
                        'device_type': device_type,
                        'subnets': matching_subnets,
                        'subnet_cidr': ', '.join(matching_subnets),
                        'dhcp_status': dhcp_status,
                        'in_dhcp': in_dhcp,
                        'device_info': {
                            'mgmtAddress': device.get('loopback'),
                            'location': device.get('location', 'N/A'),
                            'oss10_hostname': device.get('oss10_hostname', 'N/A'),
                            'vendor': vendor,
                            'device_type': device.get('family', 'Unknown'),
                            'software_version': device.get('softwareVersion', 'Unknown'),
                            'loopback': device.get('loopback', 'N/A')
                        },
                        'validation_status': dhcp_status,
                        'validation_reason': 'DHCP scope found and configured' if in_dhcp else 'DHCP scope missing or not configured',
                        'included_in_xml': True,  # Assume included for now
                        'loopback': device.get('loopback'),
                        'primary_subnet': device.get('primary_subnet')
                    })
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            flash(f"Search error: {str(e)}", "danger")
    
    logger.info(f"Search complete: {len(results)} results found")
    return render_template("search.html",
                         user=session.get("user"),
                         app_title=APP_TITLE,
                         query=query,
                         results={'total_matches': len(results), 'results': results, 'query_type': 'subnet_search'})


@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard with overview statistics"""
    try:
        netshot_client = get_netshot_client()
        
        # Test Netshot connection
        netshot_available = netshot_client.test_connection()
        
        # Test MySQL cache connection
        mysql_available = False
        try:
            from app_cache import AppCache
            cache = AppCache()
            mysql_available = cache.connect()
            if mysql_available:
                cache.disconnect()
        except Exception as e:
            logger.error(f"MySQL cache test failed: {e}")
            mysql_available = False
        
        # Get cached device counts (fast - from cache)
        cmts_devices = netshot_client.get_cmts_devices(force_refresh=False)
        pe_devices = netshot_client.get_pe_devices()
        
        # Filter out [NONAME] and VCAS devices
        cmts_filtered = [d for d in cmts_devices 
                        if d.get('name') != '[NONAME]' 
                        and d.get('oss10_hostname') != '[NONAME]'
                        and 'VCAS' not in d.get('name', '').upper()]
        pe_filtered = [d for d in pe_devices if d.get('name') != '[NONAME]']
        
        # Count public subnets
        from subnet_utils import is_public_ipv4, is_public_ipv6
        total_public_subnets = 0
        devices_with_dhcp = 0
        devices_with_loopback = 0
        
        for device in cmts_filtered:
            subnets = device.get('subnets', [])
            primary = device.get('primary_subnet')
            public_ipv4 = [s for s in subnets if '.' in s and ':' not in s and s != primary and is_public_ipv4(s.split('/')[0])]
            public_ipv6 = [s for s in subnets if ':' in s and is_public_ipv6(s.split('/')[0])]
            total_public_subnets += len(public_ipv4) + len(public_ipv6)
            
            if device.get('dhcp_validation', {}).get('has_dhcp'):
                devices_with_dhcp += 1
            if device.get('loopback'):
                devices_with_loopback += 1
        
        # Get recent XML files
        output_dir = Path(os.getenv('OUTPUT_DIR', 'output'))
        recent_files = []
        last_xml_update = 'Never'
        last_generation_status = 'pending'
        last_upload_status = 'pending'
        
        if output_dir.exists():
            xml_files = sorted(output_dir.glob('*.xml.gz'), key=lambda p: p.stat().st_mtime, reverse=True)
            if xml_files:
                # Get most recent file timestamp
                last_xml_update = datetime.fromtimestamp(xml_files[0].stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                last_generation_status = 'success'  # If files exist, generation was successful
                
                # Check upload status from response files
                response_files = sorted(output_dir.glob('*.response.json'), key=lambda p: p.stat().st_mtime, reverse=True)
                if response_files:
                    try:
                        import json
                        with open(response_files[0], 'r') as f:
                            response_data = json.load(f)
                            # Check if upload was successful (customize based on your response format)
                            if response_data.get('success') or response_data.get('status') == 'success':
                                last_upload_status = 'success'
                            else:
                                last_upload_status = 'failed'
                    except Exception:
                        last_upload_status = 'pending'
            
            for xml_file in xml_files[:10]:
                stat = xml_file.stat()
                recent_files.append({
                    'name': xml_file.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        stats = {
            'netshot_status': 'connected' if netshot_available else 'disconnected',
            'cmts_count': len(cmts_filtered),
            'pe_count': len(pe_filtered),
            'total_devices': len(cmts_filtered) + len(pe_filtered),
            'public_subnets': total_public_subnets,
            'devices_with_dhcp': devices_with_dhcp,
            'devices_with_loopback': devices_with_loopback,
            'recent_files': recent_files,
            'last_xml_update': last_xml_update,
            'last_generation_status': last_generation_status,
            'last_upload_status': last_upload_status
        }
        
        return render_template("dashboard.html",
                             user=session.get("user"),
                             stats=stats,
                             netshot_available=netshot_available,
                             mysql_available=mysql_available,
                             system_critical=(not netshot_available or not mysql_available),
                             app_title=APP_TITLE)
                             
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return render_template("dashboard.html",
                             user=session.get("user"),
                             stats={},
                             netshot_available=False,
                             mysql_available=False,
                             system_critical=True,
                             app_title=APP_TITLE)


@app.route("/devices/refresh/<device_name>", methods=['POST'])
@login_required
def refresh_device(device_name):
    """Refresh device data by clearing cache and re-fetching from Netshot/DHCP"""
    try:
        from cache_manager import CacheManager
        from app_cache import AppCache
        from dhcp_database import DHCPDatabase
        import hashlib
        
        # Get the device ID first (we need it for cache keys)
        netshot_client = get_netshot_client()
        devices = netshot_client.get_cmts_devices(force_refresh=False)
        device_id = None
        for dev in devices:
            if dev.get('name') == device_name:
                device_id = dev.get('id')
                break
        
        if not device_id:
            return jsonify({'success': False, 'error': f'Device {device_name} not found'}), 404
        
        # Clear file cache for this specific device
        cache_mgr = CacheManager('.cache')
        cache_keys_to_clear = [
            f'device_loopback_{device_id}',
            f'device_subnets_{device_id}',
            f'device_primary_{device_id}',
        ]
        
        cleared_count = 0
        for cache_key in cache_keys_to_clear:
            try:
                cache_mgr.delete(cache_key)
                cleared_count += 1
                logger.info(f"Cleared file cache: {cache_key}")
            except Exception as e:
                logger.warning(f"Could not clear {cache_key}: {e}")
        
        # Re-fetch device data from Netshot with force_refresh
        try:
            device_data = None
            for dev in netshot_client.get_cmts_devices(force_refresh=False):
                if dev.get('name') == device_name:
                    device_data = dev
                    break
            
            if device_data:
                # Re-fetch fresh data for this device
                device_data['loopback'] = netshot_client.get_loopback_interface(device_id, device_name, force_refresh=True)
                subnets, vendor = netshot_client.get_device_subnets(device_id, device_name, force_refresh=True)
                device_data['subnets'] = subnets
                device_data['primary_subnet'] = netshot_client.get_device_primary_subnet(device_id, device_name)
                
                # Re-validate DHCP
                dhcp_db = DHCPDatabase()
                if dhcp_db.connect():
                    # Determine OSS10 hostname for DHCP lookup
                    dhcp_hostname = device_data.get('oss10_hostname') or device_name
                    primary = device_data.get('primary_subnet')
                    
                    # Separate IPv4 and IPv6 subnets
                    from subnet_utils import is_public_ipv4, is_public_ipv6
                    ipv4_subnets = [s for s in subnets if '.' in s and ':' not in s and is_public_ipv4(s.split('/')[0])]
                    ipv6_subnets = [s for s in subnets if ':' in s and is_public_ipv6(s.split('/')[0])]
                    
                    if primary and dhcp_hostname:
                        validation = dhcp_db.validate_device_dhcp(dhcp_hostname, primary, ipv4_subnets, ipv6_subnets)
                        validation['dhcp_hostname'] = dhcp_hostname
                        
                        # Store in MySQL cache
                        app_cache = AppCache()
                        if app_cache.connect():
                            app_cache.set(
                                cache_key=f'device_validation:{device_name}',
                                cache_type='device_validation',
                                data=validation,
                                ttl_seconds=86400
                            )
                            app_cache.disconnect()
                            logger.info(f"Updated DHCP validation for {device_name}")
                    
                    dhcp_db.disconnect()
                
                # Update the device in the main cache list
                try:
                    import json
                    cache_key = 'cmts_devices_207'
                    key_hash = hashlib.md5(cache_key.encode()).hexdigest()
                    cache_file = cache_mgr.cache_dir / f"{key_hash}.json"
                    
                    if cache_file.exists():
                        with open(cache_file, 'r') as f:
                            cache_data = json.load(f)
                        
                        devices_list = cache_data.get('value', [])
                        # Find and update this device in the list
                        for i, d in enumerate(devices_list):
                            if d.get('name') == device_name:
                                devices_list[i] = device_data
                                logger.info(f"Updated device {device_name} in main cache")
                                break
                        
                        # Save back
                        cache_data['value'] = devices_list
                        with open(cache_file, 'w') as f:
                            json.dump(cache_data, f)
                except Exception as e:
                    logger.warning(f"Could not update main cache: {e}")
                
                logger.info(f"Successfully refreshed device {device_name} from Netshot and DHCP")
        except Exception as e:
            logger.error(f"Error re-fetching device data: {e}")
        
        return jsonify({
            'success': True, 
            'message': f'Refreshed {device_name} from Netshot and DHCP. Page will reload automatically.'
        })
    except Exception as e:
        logger.error(f"Error refreshing device {device_name}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/devices")
@login_required
def devices():
    """Device list page - load data server-side"""
    device_type = request.args.get('type', 'cmts')  # Default to CMTS only
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        netshot_client = get_netshot_client()
        
        # Test Netshot connection first
        if not netshot_client.test_connection():
            flash("⚠ Netshot API is not responding. Device data may be stale or unavailable.", "danger")
            logger.error("Netshot API connection failed")
        
        cmts_devices = []
        pe_devices = []
        
        if device_type in ['all', 'cmts']:
            import concurrent.futures
            from dhcp_database import DHCPDatabase
            
            # Fetch CMTS devices from Netshot
            all_cmts = netshot_client.get_cmts_devices(force_refresh)
            
            # Filter out [NONAME] devices, VCAS devices, and sort by hostname (use OSS10 name if available)
            filtered_cmts = [d for d in all_cmts 
                           if d.get('name') != '[NONAME]' 
                           and d.get('oss10_hostname') != '[NONAME]'
                           and 'VCAS' not in d.get('name', '').upper()]
            cmts_devices = sorted(filtered_cmts, key=lambda d: (d.get('oss10_hostname') or d.get('name', '')).lower())
            
            # Add DHCP validation from MySQL cache (batch fetch for performance)
            try:
                from dhcp_database import DHCPDatabase
                dhcp_db = DHCPDatabase()
                logger.info(f"Attempting DHCP database connection to {dhcp_db.host}:{dhcp_db.port}/{dhcp_db.database}")
                if dhcp_db.connect():
                    # Fetch all device validations from dhcp_validation_cache table in one query
                    cursor = dhcp_db.connection.cursor()
                    cursor.execute(
                        f"SELECT device_name, dhcp_hostname, has_dhcp, dhcp_scopes_count, missing_in_dhcp, matched FROM {dhcp_db.cache_database}.dhcp_validation_cache WHERE updated_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"
                    )
                    validation_rows = cursor.fetchall()
                    cursor.close()
                    validation_cache = {}
                    for row in validation_rows:
                            validation_cache[row['device_name']] = {
                                'dhcp_hostname': row['dhcp_hostname'],
                                'has_dhcp': bool(row['has_dhcp']),
                                'dhcp_scopes_count': row['dhcp_scopes_count'],
                                'missing_in_dhcp': json.loads(row['missing_in_dhcp']) if row['missing_in_dhcp'] else [],
                                'matched': json.loads(row['matched']) if row['matched'] else []
                            }
                    
                    logger.info(f"Loaded DHCP validation for {len(validation_cache)} devices from cache")
                    
                    # Apply cached validation data to devices
                    from subnet_utils import is_public_ipv4, is_public_ipv6
                    devices_with_dhcp = 0
                    for device in cmts_devices:
                        device_name = device.get('name')
                        cached_data = validation_cache.get(device_name)
                        if cached_data and isinstance(cached_data, dict):
                            device['dhcp_validation'] = cached_data
                            device['dhcp_hostname'] = cached_data.get('dhcp_hostname')
                            devices_with_dhcp += 1
                        
                        # Calculate public subnet count (excluding primary subnet)
                        subnets = device.get('subnets', [])
                        primary = device.get('primary_subnet')
                        # Exclude primary subnet from count
                        public_ipv4 = [s for s in subnets if '.' in s and ':' not in s and s != primary and is_public_ipv4(s.split('/')[0])]
                        public_ipv6 = [s for s in subnets if ':' in s and is_public_ipv6(s.split('/')[0])]
                        device['public_subnet_count'] = len(public_ipv4) + len(public_ipv6)
                    
                    logger.info(f"Applied DHCP validation to {devices_with_dhcp}/{len(cmts_devices)} devices")
                    dhcp_db.disconnect()
                else:
                    flash("⚠ DHCP database is not available. DHCP validation data will not be displayed.", "warning")
                    logger.error("DHCP database connection failed")
            except Exception as cache_err:
                flash(f"⚠ DHCP database connection error. DHCP validation unavailable.", "warning")
                logger.error(f"DHCP cache lookup failed: {cache_err}", exc_info=True)
        
        if device_type in ['all', 'pe']:
            all_pe = netshot_client.get_pe_devices(force_refresh)
            # Filter out [NONAME] devices
            filtered_pe = [d for d in all_pe if d.get('name') != '[NONAME]' and d.get('oss10_hostname') != '[NONAME]']
            pe_devices = sorted(filtered_pe, key=lambda d: (d.get('oss10_hostname') or d.get('name', '')).lower())
        
        return render_template("devices.html",
                             user=session.get("user"),
                             cmts_devices=cmts_devices,
                             pe_devices=pe_devices,
                             device_type=device_type,
                             app_title=APP_TITLE)
                             
    except Exception as e:
        logger.error(f"Error loading devices: {e}")
        return render_template("devices.html",
                             user=session.get("user"),
                             cmts_devices=[],
                             pe_devices=[],
                             device_type=device_type,
                             error=str(e),
                             app_title=APP_TITLE)


@app.route("/api/devices/data")
@login_required
def devices_data():
    """API endpoint to fetch device data asynchronously"""
    device_type = request.args.get('type', 'cmts')  # Default to CMTS only
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        netshot_client = get_netshot_client()
        
        cmts_devices = []
        pe_devices = []
        
        if device_type in ['all', 'cmts']:
            import concurrent.futures
            from dhcp_database import DHCPDatabase
            
            # Start fetching CMTS devices from Netshot (this may use cache or hit API)
            all_cmts_future = concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(
                netshot_client.get_cmts_devices, force_refresh
            )
            
            # Pre-connect to DHCP database while waiting for Netshot
            dhcp_db = DHCPDatabase()
            dhcp_connected = dhcp_db.connect()
            
            # Wait for Netshot data
            all_cmts = all_cmts_future.result()
            
            # Filter out [NONAME] devices, VCAS devices, and sort by hostname (use OSS10 name if available)
            filtered_cmts = [d for d in all_cmts 
                           if d.get('name') != '[NONAME]' 
                           and d.get('oss10_hostname') != '[NONAME]'
                           and 'VCAS' not in d.get('name', '').upper()]
            cmts_devices = sorted(filtered_cmts, key=lambda d: (d.get('oss10_hostname') or d.get('name', '')).lower())
            
            # Close DHCP connection (not needed here)
            if dhcp_connected:
                dhcp_db.disconnect()
            
            # Add DHCP validation from MySQL cache (batch fetch for performance)
            try:
                from dhcp_database import DHCPDatabase
                dhcp_db = DHCPDatabase()
                if dhcp_db.connect():
                    # Fetch all device validations from dhcp_validation_cache table in one query
                    cursor = dhcp_db.connection.cursor()
                    cursor.execute(
                        f"SELECT device_name, dhcp_hostname, has_dhcp, dhcp_scopes_count, missing_in_dhcp, matched FROM {dhcp_db.cache_database}.dhcp_validation_cache WHERE updated_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"
                    )
                    validation_rows = cursor.fetchall()
                    cursor.close()
                    
                    validation_cache = {}
                    for row in validation_rows:
                            validation_cache[row['device_name']] = {
                                'dhcp_hostname': row['dhcp_hostname'],
                                'has_dhcp': bool(row['has_dhcp']),
                                'dhcp_scopes_count': row['dhcp_scopes_count'],
                                'missing_in_dhcp': json.loads(row['missing_in_dhcp']) if row['missing_in_dhcp'] else [],
                                'matched': json.loads(row['matched']) if row['matched'] else []
                            }
                    
                    # Apply cached validation data to devices
                    from subnet_utils import is_public_ipv4, is_public_ipv6
                    for device in cmts_devices:
                        device_name = device.get('name')
                        cached_data = validation_cache.get(device_name)
                        if cached_data and isinstance(cached_data, dict):
                            device['dhcp_validation'] = cached_data
                            device['dhcp_hostname'] = cached_data.get('dhcp_hostname')
                        
                        # Calculate public subnet count (excluding primary subnet)
                        subnets = device.get('subnets', [])
                        primary = device.get('primary_subnet')
                        # Exclude primary subnet from count
                        public_ipv4 = [s for s in subnets if '.' in s and ':' not in s and s != primary and is_public_ipv4(s.split('/')[0])]
                        public_ipv6 = [s for s in subnets if ':' in s and is_public_ipv6(s.split('/')[0])]
                        device['public_subnet_count'] = len(public_ipv4) + len(public_ipv6)
                    
                    cache.disconnect()
            except Exception as cache_err:
                logger.warning(f"DHCP cache lookup failed: {cache_err}")
        
        if device_type in ['all', 'pe']:
            pe_devices = []  # No PE devices in pilot
        
        return jsonify({
            'success': True,
            'cmts_devices': cmts_devices,
            'pe_devices': pe_devices,
            'device_type': device_type
        })
                             
    except Exception as e:
        logger.error(f"Error loading devices: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'cmts_devices': [],
            'pe_devices': [],
            'device_type': device_type
        })


@app.route("/xml-status")
@login_required
def xml_status():
    """XML generation status and history"""
    try:
        # Check system status
        netshot_client = get_netshot_client()
        netshot_available = netshot_client.test_connection()
        
        mysql_available = False
        try:
            from app_cache import AppCache
            cache = AppCache()
            mysql_available = cache.connect()
            if mysql_available:
                cache.disconnect()
        except Exception:
            mysql_available = False
        
        system_critical = not netshot_available or not mysql_available
        
        output_dir = Path(os.getenv('OUTPUT_DIR', 'output'))
        log_dir = Path('logs')
        
        # Get XML files
        xml_files = []
        if output_dir.exists():
            for xml_file in sorted(output_dir.glob('*.xml*'), key=lambda p: p.stat().st_mtime, reverse=True):
                stat = xml_file.stat()
                xml_files.append({
                    'name': xml_file.name,
                    'path': str(xml_file),
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'modified_str': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'CMTS' if 'CMTS' in xml_file.name or 'Infra' in xml_file.name else 'PE'
                })
        
        # Get recent logs
        recent_logs = []
        if log_dir.exists():
            for log_file in sorted(log_dir.glob('eve_xml_*.log'), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
                stat = log_file.stat()
                recent_logs.append({
                    'name': log_file.name,
                    'path': str(log_file),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return render_template("xml_status.html",
                             user=session.get("user"),
                             xml_files=xml_files,
                             recent_logs=recent_logs,
                             netshot_available=netshot_available,
                             mysql_available=mysql_available,
                             system_critical=system_critical,
                             app_title=APP_TITLE)
                             
    except Exception as e:
        logger.error(f"Error loading XML status: {e}")
        flash(f"Error loading XML status: {str(e)}", "danger")
        return render_template("xml_status.html",
                             user=session.get("user"),
                             xml_files=[],
                             recent_logs=[],
                             netshot_available=False,
                             mysql_available=False,
                             system_critical=True,
                             app_title=APP_TITLE)


@app.route("/download_xml/<filename>")
@login_required
def download_xml(filename):
    """Download XML file"""
    try:
        output_dir = Path(os.getenv('OUTPUT_DIR', 'output'))
        xml_file = output_dir / filename
        
        if not xml_file.exists():
            flash(f"File not found: {filename}", "danger")
            return redirect(url_for('xml_status'))
        
        logger.info(f"User {session['user'].get('preferred_username')} downloading {filename}")
        
        return send_file(
            xml_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/gzip' if filename.endswith('.gz') else 'application/xml'
        )
        
    except Exception as e:
        logger.error(f"Error downloading XML: {e}")
        flash(f"Error downloading file: {str(e)}", "danger")
        return redirect(url_for('xml_status'))


@app.route("/api/view-xml/<filename>")
@login_required
def api_view_xml(filename):
    """API endpoint to view XML file content"""
    try:
        import gzip
        output_dir = Path(os.getenv('OUTPUT_DIR', 'output'))
        xml_file = output_dir / filename
        
        if not xml_file.exists():
            return "File not found", 404
        
        # If it's a .gz file, decompress it
        if filename.endswith('.gz'):
            with gzip.open(xml_file, 'rt', encoding='utf-8') as f:
                content = f.read()
        else:
            with open(xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
        
        return content, 200, {'Content-Type': 'application/xml'}
        
    except Exception as e:
        logger.error(f"Error viewing XML: {e}")
        return f"Error reading file: {str(e)}", 500


@app.route("/scheduled-tasks")
@login_required
@require_permission(Permission.VIEW_VALIDATION)
def scheduled_tasks():
    """Scheduled tasks page"""
    # Get job info from scheduler
    jobs_info = []
    for job in task_scheduler.get_jobs():
        trigger_str = str(job.trigger)
        jobs_info.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else 'N/A',
            'trigger': trigger_str
        })
    
    return render_template("scheduled_tasks.html",
                         user=session.get("user"),
                         app_title=APP_TITLE,
                         app_version=APP_VERSION,
                         jobs=jobs_info)


@app.route("/api/tasks/status", methods=["GET"])
@login_required
def api_tasks_status():
    """Get current status of all scheduled tasks"""
    try:
        jobs_status = []
        for job in task_scheduler.get_jobs():
            jobs_status.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jsonify({
            'success': True,
            'jobs': jobs_status
        })
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/tasks/history", methods=["GET"])
@login_required
def api_tasks_history():
    """Get recent task execution history from audit log"""
    try:
        audit = get_audit_logger()
        rbac = get_rbac_manager()
        
        # Get recent task-related audit logs
        logs = audit.get_logs(
            category='xml_generate',
            limit=10,
            offset=0
        )
        
        # Also get cache refresh logs
        cache_logs = audit.get_logs(
            category='cache_refresh',
            limit=10,
            offset=0
        )
        
        # Combine and sort by timestamp
        all_logs = logs + cache_logs
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        all_logs = all_logs[:10]  # Keep only last 10
        
        # Get all users for name lookup
        users = rbac.get_all_users()
        user_map = {u['email']: u['name'] for u in users}
        user_map['system'] = 'System (Scheduled)'
        
        # Format for display
        history = []
        for log in all_logs:
            # Determine status from action text
            action = log.get('action', '')
            status = 'success'
            if 'failed' in action.lower() or 'error' in action.lower():
                status = 'failed'
            
            username = log.get('username', 'system')
            display_name = user_map.get(username, username)
            
            history.append({
                'timestamp': log.get('timestamp'),
                'task_name': log.get('action', 'Unknown Task'),
                'user': display_name,
                'status': status,
                'details': log.get('details', '')
            })
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        logger.error(f"Error getting task history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/tasks/<task_id>/run", methods=["POST"])
@login_required
@require_permission(Permission.GENERATE_XML)
def api_run_task(task_id):
    """API endpoint to run a scheduled task manually"""
    try:
        task_functions = {
            'cache_warmer': run_cache_warmer,
            'dhcp_cache': run_dhcp_cache,
            'xml_generation': run_xml_generation
        }
        
        if task_id not in task_functions:
            return jsonify({'success': False, 'error': 'Invalid task ID'}), 400
        
        # Get the job to check if it exists
        job = task_scheduler.get_job(task_id)
        if not job:
            return jsonify({'success': False, 'error': 'Task not found in scheduler'}), 404
        
        # Run the task immediately
        task_functions[task_id]()
        
        # Audit log
        audit = get_audit_logger()
        audit.log(
            username=session['user'].get('preferred_username'),
            category=audit.CATEGORY_XML_GENERATE,
            action=f'Manually triggered task: {task_id}',
            details=f'Job: {job.name}',
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Task "{job.name}" executed successfully'
        })
    except Exception as e:
        logger.error(f"Error running task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/tasks/<task_id>/schedule", methods=["POST"])
@login_required
@require_permission(Permission.MODIFY_CONFIG)
def api_update_schedule(task_id):
    """API endpoint to update task schedule"""
    try:
        data = request.json
        cron = data.get('cron')
        
        if not cron:
            return jsonify({'success': False, 'error': 'Cron expression is required'}), 400
        
        # Validate cron format (basic check)
        parts = cron.split()
        if len(parts) != 5:
            return jsonify({'success': False, 'error': 'Invalid cron format. Expected: minute hour day month weekday'}), 400
        
        # Get the current job (may not exist for XML generation)
        job = task_scheduler.get_job(task_id)
        
        # Parse cron expression
        minute, hour, day, month, day_of_week = parts
        
        # Map task IDs to functions
        task_functions = {
            'cache_warmer': run_cache_warmer,
            'dhcp_cache': run_dhcp_cache,
            'xml_generation': run_xml_generation
        }
        
        if task_id not in task_functions:
            return jsonify({'success': False, 'error': 'Invalid task ID'}), 400
        
        task_names = {
            'cache_warmer': 'Cache Warmer',
            'dhcp_cache': 'DHCP Cache Refresh',
            'xml_generation': 'XML Generation & Upload'
        }
        
        if job:
            # Update existing job
            task_scheduler.reschedule_job(
                task_id,
                trigger=CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                )
            )
        else:
            # Add new job
            task_scheduler.add_job(
                func=task_functions[task_id],
                trigger=CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                ),
                id=task_id,
                name=task_names[task_id],
                replace_existing=True
            )
        
        # Audit log
        audit = get_audit_logger()
        audit.log(
            username=session['user'].get('preferred_username'),
            category=audit.CATEGORY_CONFIG_CHANGE,
            action=f'Updated schedule for task: {task_id}',
            details=f'New cron: {cron}',
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': 'Schedule updated successfully',
            'cron': cron
        })
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/health")
@login_required
def health():
    """System health check page"""
    try:
        health_checks = {}
        
        # Check Netshot connection
        netshot_client = get_netshot_client()
        health_checks['netshot'] = {
            'name': 'Netshot API',
            'status': 'healthy' if netshot_client.test_connection() else 'unhealthy',
            'message': 'Connected' if netshot_client.test_connection() else 'Connection failed'
        }
        
        # Check DHCP database
        dhcp = get_dhcp_integration()
        health_checks['dhcp'] = {
            'name': 'DHCP Database',
            'status': 'healthy' if dhcp.test_connection() else 'unhealthy',
            'message': 'Connected' if dhcp.test_connection() else 'Connection failed'
        }
        
        # Check output directory
        output_dir = Path(os.getenv('OUTPUT_DIR', 'output'))
        health_checks['output_dir'] = {
            'name': 'Output Directory',
            'status': 'healthy' if output_dir.exists() else 'unhealthy',
            'message': f'Writable at {output_dir}' if output_dir.exists() else 'Directory not found'
        }
        
        # Check upload endpoint
        upload_url = os.getenv('UPLOAD_API_BASE_URL', '')
        health_checks['upload'] = {
            'name': 'Upload Endpoint',
            'status': 'configured' if upload_url else 'not_configured',
            'message': f'Configured: {upload_url}' if upload_url else 'Not configured'
        }
        
        # Overall status
        overall_status = 'healthy' if all(
            h['status'] == 'healthy' for h in health_checks.values() 
            if h['status'] in ['healthy', 'unhealthy']
        ) else 'degraded'
        
        return render_template("health.html",
                             user=session.get("user"),
                             health_checks=health_checks,
                             overall_status=overall_status,
                             app_title=APP_TITLE)
                             
    except Exception as e:
        logger.error(f"Error performing health checks: {e}")
        flash(f"Error performing health checks: {str(e)}", "danger")
        return render_template("health.html",
                             user=session.get("user"),
                             health_checks={},
                             overall_status='error',
                             app_title=APP_TITLE)


# ============================================================================
# API Routes
# ============================================================================

@app.route("/api/generate-xml", methods=["POST"])
@login_required
def api_generate_xml():
    """API endpoint to generate XML files"""
    try:
        # Check system status first
        netshot_client = get_netshot_client()
        netshot_available = netshot_client.test_connection()
        
        mysql_available = False
        try:
            from app_cache import AppCache
            cache = AppCache()
            mysql_available = cache.connect()
            if mysql_available:
                cache.disconnect()
        except Exception:
            mysql_available = False
        
        # Block if system is critical
        if not netshot_available or not mysql_available:
            issues = []
            if not netshot_available:
                issues.append("Netshot API unavailable")
            if not mysql_available:
                issues.append("MySQL cache unavailable")
            
            return jsonify({
                'success': False,
                'error': 'XML generation disabled due to critical system issues: ' + ', '.join(issues)
            }), 503
        
        mode = request.json.get('mode', 'both')  # vfz, pe, or both
        username = session['user'].get('preferred_username')
        
        logger.info(f"User {username} initiated XML generation: {mode}")
        
        # Generate XML
        generator = EVEXMLGeneratorV2()
        
        results = {}
        if mode in ['vfz', 'both']:
            vfz_result = generator.process_vfz_devices()
            results['vfz'] = vfz_result
        
        if mode in ['pe', 'both']:
            pe_result = generator.process_pe_devices()
            results['pe'] = pe_result
        
        # Audit log
        audit = get_audit_logger()
        device_count = sum(r.get('device_count', 0) for r in results.values())
        audit.log(
            username=username,
            category=audit.CATEGORY_XML_GENERATE,
            action=f'Generated XML files ({mode})',
            details=f'Processed {device_count} devices',
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': 'XML generation completed',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error generating XML: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route("/api/upload-xml", methods=["POST"])
@login_required
def api_upload_xml():
    """API endpoint to upload XML file"""
    try:
        # Check system status first
        netshot_client = get_netshot_client()
        netshot_available = netshot_client.test_connection()
        
        mysql_available = False
        try:
            from app_cache import AppCache
            cache = AppCache()
            mysql_available = cache.connect()
            if mysql_available:
                cache.disconnect()
        except Exception:
            mysql_available = False
        
        # Block if system is critical
        if not netshot_available or not mysql_available:
            issues = []
            if not netshot_available:
                issues.append("Netshot API unavailable")
            if not mysql_available:
                issues.append("MySQL cache unavailable")
            
            return jsonify({
                'success': False,
                'error': 'XML upload disabled due to critical system issues: ' + ', '.join(issues)
            }), 503
        
        filename = request.json.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'message': 'No filename provided'}), 400
        
        logger.info(f"User {session['user'].get('preferred_username')} initiated XML upload: {filename}")
        
        output_dir = Path(os.getenv('OUTPUT_DIR', 'output'))
        xml_file = output_dir / filename
        
        if not xml_file.exists():
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        # Upload XML
        generator = EVEXMLGeneratorV2()
        success, message = generator.upload_xml_file(str(xml_file))
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error uploading XML: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route("/api/devices")
@login_required
def api_devices():
    """API endpoint to get device list"""
    
    try:
        device_type = request.args.get('type', 'all')
        
        netshot_client = get_netshot_client()
        
        devices = []
        if device_type in ['all', 'cmts']:
            all_cmts = netshot_client.get_cmts_devices()
            # Show all CMTS devices
            cmts_devices = all_cmts
            for device in cmts_devices:
                device['type'] = 'CMTS'
                devices.append(device)
        
        if device_type in ['all', 'pe']:
            # No PE devices in pilot
            pass
        
        return jsonify({
            'success': True,
            'devices': devices,
            'count': len(devices)
        })
        
    except Exception as e:
        logger.error(f"Error fetching devices: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route("/api/health")
def api_health():
    """API health check endpoint (no auth required)"""
    return jsonify({
        'status': 'ok',
        'version': APP_VERSION,
        'timestamp': datetime.now().isoformat()
    })


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", 
                         error_code=404,
                         error_message="Page not found",
                         user=session.get("user"),
                         app_title=APP_TITLE), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html",
                         error_code=500,
                         error_message="Internal server error",
                         user=session.get("user"),
                         app_title=APP_TITLE), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Create necessary directories
    Path('logs').mkdir(exist_ok=True)
    Path('output').mkdir(exist_ok=True)
    
    # Initialize configuration manager and settings table
    config_mgr = get_config_manager()
    config_mgr.initialize_settings_table()
    logger.info("Settings table initialized")
    
    # Create default admin user if users table is empty
    try:
        rbac_mgr = get_rbac_manager()
        # Check if any users exist
        users = rbac_mgr.get_all_users()
        
        if not users or len(users) == 0:
            # Create default admin user: admin/admin
            default_password = "admin"
            if rbac_mgr.create_user('admin', 'admin@localhost', default_password, 'admin'):
                logger.info("Default admin user created (username: admin, password: admin)")
                logger.warning("SECURITY: Please change the default admin password immediately!")
            else:
                logger.error("Failed to create default admin user")
    except Exception as e:
        logger.error(f"Error checking/creating default admin user: {e}")
    
    # Get configuration
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    
    logger.info(f"Starting {APP_TITLE} v{APP_VERSION}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Listening on {host}:{port}")
    
    try:
        app.run(host=host, port=port, debug=debug)
    finally:
        if task_scheduler.running:
            task_scheduler.shutdown()
            logger.info("Scheduler stopped")
