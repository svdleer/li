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

# Import our modules
from netshot_api import get_netshot_client
from dhcp_integration import get_dhcp_integration
from eve_li_xml_generator_v2 import EVEXMLGeneratorV2
from audit_logger import get_audit_logger

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


def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Bypass authentication in debug mode for local testing
        if app.debug:
            if not session.get("user"):
                # Create a fake user session for local testing
                session["user"] = {
                    "name": "Local Dev User",
                    "preferred_username": "dev@localhost",
                    "email": "dev@localhost"
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
    """Initiate OAuth login flow or local dev login"""
    # For local development, automatically log in
    if app.debug:
        session["user"] = {
            "name": "Local Admin",
            "preferred_username": "admin@localhost",
            "email": "admin@localhost"
        }
        logger.info("Debug mode: Auto-login as local admin")
        flash("Logged in as Local Admin (Debug Mode)", "info")
        return redirect(url_for("index"))
    
    # Production: Use O365 authentication
    session["state"] = str(uuid.uuid4())
    auth_url = _build_auth_url(scopes=SCOPE, state=session["state"])
    return render_template("login.html", auth_url=auth_url, app_title=APP_TITLE)


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
    Check if current user has permission (stub for local dev)
    In production, this would check actual user roles/permissions
    """
    # For local dev, admin has all permissions
    if app.debug:
        return True
    
    # Production: implement actual permission checking
    # For now, return True for all permissions
    return True


# Make check_permission available in all templates
@app.context_processor
def inject_permissions():
    """Inject permission checker into all templates"""
    return dict(check_permission=check_permission)


# ============================================================================
# Main Application Routes
# ============================================================================

@app.route("/")
def index():
    """Home page / Dashboard"""
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
                             logs=logs,
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
                             logs=[],
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


@app.route("/user-management")
@login_required
def user_management():
    """User management page"""
    # TODO: Implement actual user management functionality
    return render_template("user_management.html",
                         user=session.get("user"),
                         app_title=APP_TITLE,
                         users=[])


@app.route("/search")
@login_required
def search_page():
    """Search page"""
    # TODO: Implement actual search functionality
    query = request.args.get('q', '')
    return render_template("search.html",
                         user=session.get("user"),
                         app_title=APP_TITLE,
                         query=query,
                         results=[])


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
        from netshot_diagnostic import is_public_ipv4, is_public_ipv6
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
        if output_dir.exists():
            xml_files = sorted(output_dir.glob('*.xml.gz'), key=lambda p: p.stat().st_mtime, reverse=True)
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
            'recent_files': recent_files
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
                    from netshot_diagnostic import is_public_ipv4, is_public_ipv6
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
                from app_cache import AppCache
                cache = AppCache()
                if cache.connect():
                    # Fetch all device validations in one query instead of 460+ individual queries
                    with cache.connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT cache_key, data FROM cache WHERE cache_type = 'device_validation' AND expires_at > NOW()"
                        )
                        validation_cache = {row['cache_key']: json.loads(row['data']) if isinstance(row['data'], str) else row['data'] 
                                          for row in cursor.fetchall()}
                    
                    # Apply cached validation data to devices
                    from netshot_diagnostic import is_public_ipv4, is_public_ipv6
                    for device in cmts_devices:
                        device_name = device.get('name')
                        cache_key = f'device_validation:{device_name}'
                        cached_data = validation_cache.get(cache_key)
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
                else:
                    flash("⚠ MySQL cache is not available. DHCP validation data will not be displayed.", "warning")
                    logger.error("MySQL cache connection failed")
            except Exception as cache_err:
                flash(f"⚠ MySQL cache connection error. DHCP validation unavailable.", "warning")
                logger.error(f"DHCP cache lookup failed: {cache_err}")
        
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
                from app_cache import AppCache
                cache = AppCache()
                if cache.connect():
                    # Fetch all device validations in one query
                    with cache.connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT cache_key, data FROM cache WHERE cache_type = 'device_validation' AND expires_at > NOW()"
                        )
                        validation_cache = {row['cache_key']: json.loads(row['data']) if isinstance(row['data'], str) else row['data'] 
                                          for row in cursor.fetchall()}
                    
                    # Apply cached validation data to devices
                    from netshot_diagnostic import is_public_ipv4, is_public_ipv6
                    for device in cmts_devices:
                        device_name = device.get('name')
                        cache_key = f'device_validation:{device_name}'
                        cached_data = validation_cache.get(cache_key)
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
    
    # Get configuration
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    
    logger.info(f"Starting {APP_TITLE} v{APP_VERSION}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Listening on {host}:{port}")
    
    app.run(host=host, port=port, debug=debug)
