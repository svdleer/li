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
        
        logger.info(f"User logged in: {session['user'].get('preferred_username')}")
        flash(f"Welcome, {session['user'].get('name')}!", "success")
    
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    """Logout user"""
    username = session.get("user", {}).get("preferred_username", "Unknown")
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
    # TODO: Implement actual audit log functionality
    stats = {
        'total_events': 0,
        'by_category': {},
        'by_level': {}
    }
    return render_template("audit_log.html",
                         user=session.get("user"),
                         app_title=APP_TITLE,
                         logs=[],
                         total_logs=0,
                         stats=stats)


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
        # Just show basic status - don't fetch all devices
        netshot_client = get_netshot_client()
        
        # Test connections only
        netshot_status = netshot_client.test_connection()
        
        # Get cached device count (fast)
        cmts_count = 0
        pe_count = 0
        
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
            'netshot_status': 'connected' if netshot_status else 'disconnected',
            'dhcp_status': 'unknown',
            'cmts_count': cmts_count,
            'pe_count': pe_count,
            'total_devices': cmts_count + pe_count,
            'recent_files': recent_files
        }
        
        return render_template("dashboard.html",
                             user=session.get("user"),
                             stats=stats,
                             app_title=APP_TITLE)
                             
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return render_template("dashboard.html",
                             user=session.get("user"),
                             stats={},
                             app_title=APP_TITLE)


@app.route("/devices/refresh/<device_name>", methods=['POST'])
@login_required
def refresh_device(device_name):
    """Refresh device data by clearing cache"""
    try:
        # Clear all cache files related to this device
        import os
        import glob
        cache_dir = '.cache'
        if os.path.exists(cache_dir):
            for cache_file in glob.glob(f'{cache_dir}/*{device_name}*.json'):
                os.remove(cache_file)
                logger.info(f"Cleared cache file: {cache_file}")
        
        return jsonify({'success': True, 'message': f'Cache cleared for {device_name}'})
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
        
        cmts_devices = []
        pe_devices = []
        
        if device_type in ['all', 'cmts']:
            import concurrent.futures
            from dhcp_database import DHCPDatabase
            
            # Fetch CMTS devices from Netshot
            all_cmts = netshot_client.get_cmts_devices(force_refresh)
            
            # Sort by hostname (use OSS10 name if available)
            cmts_devices = sorted(all_cmts, key=lambda d: (d.get('oss10_hostname') or d.get('name', '')).lower())
            
            # Add DHCP validation from MySQL cache
            try:
                from app_cache import AppCache
                cache = AppCache()
                if cache.connect():
                    for device in cmts_devices:
                        device_name = device.get('name')
                        cached_data = cache.get(f'device_validation:{device_name}', 'device_validation')
                        if cached_data:
                            device['dhcp_validation'] = cached_data
                            device['dhcp_hostname'] = cached_data.get('dhcp_hostname')
                    cache.disconnect()
            except Exception as cache_err:
                logger.warning(f"DHCP cache lookup failed: {cache_err}")
        
        if device_type in ['all', 'pe']:
            all_pe = netshot_client.get_pe_devices(force_refresh)
            pe_devices = sorted(all_pe, key=lambda d: (d.get('oss10_hostname') or d.get('name', '')).lower())
        
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
            
            # Show all CMTS devices and sort by hostname (use OSS10 name if available)
            cmts_devices = sorted(all_cmts, key=lambda d: (d.get('oss10_hostname') or d.get('name', '')).lower())
            
            # Close DHCP connection (not needed here)
            if dhcp_connected:
                dhcp_db.disconnect()
            
            # Add DHCP validation from MySQL cache (background job keeps it fresh)
            try:
                from app_cache import AppCache
                cache = AppCache()
                if cache.connect():
                    for device in cmts_devices:
                        device_name = device.get('name')
                        # Get cached validation from MySQL
                        cached_data = cache.get(f'device_validation:{device_name}', 'device_validation')
                        if cached_data:
                            device['dhcp_validation'] = cached_data
                            device['dhcp_hostname'] = cached_data.get('dhcp_hostname')
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
                             app_title=APP_TITLE)
                             
    except Exception as e:
        logger.error(f"Error loading XML status: {e}")
        flash(f"Error loading XML status: {str(e)}", "danger")
        return render_template("xml_status.html",
                             user=session.get("user"),
                             xml_files=[],
                             recent_logs=[],
                             app_title=APP_TITLE)


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
        mode = request.json.get('mode', 'both')  # vfz, pe, or both
        
        logger.info(f"User {session['user'].get('preferred_username')} initiated XML generation: {mode}")
        
        # Generate XML
        generator = EVEXMLGeneratorV2()
        
        results = {}
        if mode in ['vfz', 'both']:
            vfz_result = generator.process_vfz_devices()
            results['vfz'] = vfz_result
        
        if mode in ['pe', 'both']:
            pe_result = generator.process_pe_devices()
            results['pe'] = pe_result
        
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
