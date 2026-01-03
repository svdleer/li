#!/usr/bin/env python3
"""
EVE LI Web Application - Demo Mode
===================================

Flask-based web interface with DEMO MODE support.
Uses mock data instead of real Netshot/DHCP/Azure AD connections.

Run this for a quick demo without any external dependencies!

Author: Silvester van der Leer
Version: 2.0 Demo
"""

import os
import sys
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from functools import wraps
import uuid

from flask import Flask, render_template, redirect, url_for, session, request, jsonify, flash, send_file
from flask_session import Session
from dotenv import load_dotenv

# Import demo data generator
from demo_data import get_demo_generator
from subnet_utils import is_public_subnet, filter_public_subnets, categorize_subnets
from subnet_validator import create_subnet_validator
from subnet_lookup import create_subnet_lookup
from audit_log import get_audit_logger
from rbac import get_rbac_manager, require_permission, Permission, Role, check_permission

# Load environment variables
load_dotenv('.env.demo')  # Load demo environment

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
logger = logging.getLogger('eve_li_demo')

# Get demo data generator
demo_generator = get_demo_generator()

# Initialize subnet validator
subnet_validator = create_subnet_validator(demo_mode=True)

# Initialize audit logger
audit_logger = get_audit_logger(demo_mode=True)

# Initialize RBAC manager
rbac_manager = get_rbac_manager(demo_mode=True)

# Application configuration
DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() == 'true'
APP_TITLE = os.getenv('APP_TITLE', 'VFZ EVE LI XML Management (DEMO)')
APP_VERSION = "2.0 Demo"

# Make check_permission available to templates
app.jinja_env.globals.update(check_permission=check_permission)


def login_required(f):
    """Decorator to require authentication (simplified for demo)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# Authentication Routes (Demo Mode)
# ============================================================================

@app.route("/login")
def login():
    """Demo login - no real Office 365"""
    if DEMO_MODE:
        # Allow selection of demo user type
        user_type = request.args.get('as', 'operator')
        
        if user_type == 'admin':
            user = demo_generator.generate_demo_admin()
        elif user_type == 'viewer':
            user = demo_generator.generate_demo_viewer()
        else:
            user = demo_generator.generate_demo_user()
        
        # Add role from RBAC system
        user['role'] = rbac_manager.get_user_role(user.get('email', user.get('preferred_username', '')))
        
        session["user"] = user
        
        # Log login
        audit_logger.log_login(user.get('email', user.get('preferred_username', '')), 
                              request.remote_addr, success=True)
        
        flash(f"Welcome to Demo Mode! Logged in as {user['name']} ({user.get('role', 'operator').upper()})", "success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("login.html", 
                             auth_url="#", 
                             app_title=APP_TITLE,
                             demo_mode=True)


@app.route("/logout")
def logout():
    """Logout user"""
    user = session.get("user", {})
    username = user.get("name", "Demo User")
    user_email = user.get("email", user.get("preferred_username", ""))
    
    # Log logout
    if user_email:
        audit_logger.log_logout(user_email, request.remote_addr)
    
    # Clear session completely
    session.pop("user", None)
    session.clear()
    
    logger.info(f"User logged out: {username}")
    flash("You have been logged out. Select a role to login again.", "info")
    return redirect("/")


# ============================================================================
# Main Application Routes
# ============================================================================

@app.route("/")
def index():
    """Home page / Dashboard"""
    # In demo mode, show role selection page instead of auto-login
    user = session.get("user")
    
    # If user is logged in, go to dashboard
    if user and user.get("email"):
        return redirect(url_for("dashboard"))
    
    # Show role selection page
    return render_template("index.html", 
                         user=None,
                         app_title=APP_TITLE,
                         app_version=APP_VERSION,
                         demo_mode=DEMO_MODE)


@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard with overview statistics"""
    try:
        # Get demo data
        cmts_devices = demo_generator.generate_cmts_devices()
        pe_devices = demo_generator.generate_pe_devices()
        
        # Run subnet validation for dashboard stats
        validation_results = subnet_validator.validate_all_devices(cmts_devices, pe_devices)
        
        # Count subnets for stats (all public now)
        total_subnets = 0
        for device in cmts_devices + pe_devices:
            total_subnets += len(device['subnets'])
        
        # Demo: Last XML update info
        from datetime import datetime, timedelta
        last_xml_update = (datetime.now() - timedelta(minutes=random.randint(5, 60))).strftime('%Y-%m-%d %H:%M:%S')
        last_upload_status = random.choice(['success', 'success', 'success', 'failed', 'pending'])
        
        stats = {
            'netshot_status': 'connected' if DEMO_MODE else 'disconnected',
            'dhcp_status': 'connected' if DEMO_MODE else 'disconnected',
            'cmts_count': len(cmts_devices),
            'pe_count': len(pe_devices),
            'total_devices': len(cmts_devices) + len(pe_devices),
            'public_subnets': total_subnets,
            'last_xml_update': last_xml_update,
            'last_upload_status': last_upload_status,
            'demo_mode': DEMO_MODE,
            'validation': validation_results
        }
        
        return render_template("dashboard.html",
                             user=session.get("user"),
                             stats=stats,
                             app_title=APP_TITLE,
                             demo_mode=DEMO_MODE)
                             
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return render_template("dashboard.html",
                             user=session.get("user"),
                             stats={},
                             app_title=APP_TITLE,
                             demo_mode=DEMO_MODE)


@app.route("/devices")
@login_required
def devices():
    """Device list page"""
    device_type = request.args.get('type', 'all')
    
    try:
        cmts_devices = []
        pe_devices = []
        
        if device_type in ['all', 'cmts']:
            cmts_devices = demo_generator.generate_cmts_devices()
        
        if device_type in ['all', 'pe']:
            pe_devices = demo_generator.generate_pe_devices()
        
        return render_template("devices.html",
                             user=session.get("user"),
                             cmts_devices=cmts_devices,
                             pe_devices=pe_devices,
                             device_type=device_type,
                             app_title=APP_TITLE,
                             demo_mode=DEMO_MODE)
                             
    except Exception as e:
        logger.error(f"Error loading devices: {e}")
        flash(f"Error loading devices: {str(e)}", "danger")
        return render_template("devices.html",
                             user=session.get("user"),
                             cmts_devices=[],
                             pe_devices=[],
                             device_type=device_type,
                             app_title=APP_TITLE,
                             demo_mode=DEMO_MODE)


@app.route("/xml-status")
@login_required
def xml_status():
    """XML generation status and history"""
    try:
        xml_files = demo_generator.generate_xml_files()
        recent_logs = demo_generator.generate_log_files()
        
        return render_template("xml_status.html",
                             user=session.get("user"),
                             xml_files=xml_files,
                             recent_logs=recent_logs,
                             app_title=APP_TITLE,
                             demo_mode=DEMO_MODE)
                             
    except Exception as e:
        logger.error(f"Error loading XML status: {e}")
        flash(f"Error loading XML status: {str(e)}", "danger")
        return render_template("xml_status.html",
                             user=session.get("user"),
                             xml_files=[],
                             recent_logs=[],
                             app_title=APP_TITLE,
                             demo_mode=DEMO_MODE)


@app.route("/health")
@login_required
def health():
    """System health check page"""
    try:
        health_checks = {}
        
        # Demo mode - all systems healthy
        health_checks['netshot'] = {
            'name': 'Netshot API (Demo)',
            'status': 'healthy',
            'message': 'Demo mode - using mock data'
        }
        
        health_checks['dhcp'] = {
            'name': 'DHCP Database (Demo)',
            'status': 'healthy',
            'message': 'Demo mode - using mock data'
        }
        
        health_checks['output_dir'] = {
            'name': 'Output Directory',
            'status': 'healthy',
            'message': 'Demo mode - files simulated'
        }
        
        health_checks['upload'] = {
            'name': 'Upload Endpoint (Demo)',
            'status': 'healthy',
            'message': 'Demo mode - uploads simulated'
        }
        
        overall_status = 'healthy'
        
        return render_template("health.html",
                             user=session.get("user"),
                             health_checks=health_checks,
                             overall_status=overall_status,
                             app_title=APP_TITLE,
                             demo_mode=DEMO_MODE,
                             now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                             
    except Exception as e:
        logger.error(f"Error performing health checks: {e}")
        flash(f"Error performing health checks: {str(e)}", "danger")
        return render_template("health.html",
                             user=session.get("user"),
                             health_checks={},
                             overall_status='error',
                             app_title=APP_TITLE,
                             demo_mode=DEMO_MODE,
                             now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


# ============================================================================
# API Routes
# ============================================================================

@app.route("/api/generate-xml", methods=["POST"])
@login_required
def api_generate_xml():
    """API endpoint to generate XML files (demo mode)"""
    try:
        mode = request.json.get('mode', 'both')
        
        logger.info(f"Demo: User {session['user'].get('preferred_username')} initiated XML generation: {mode}")
        
        # Simulate processing
        import time
        time.sleep(1)  # Simulate work
        
        results = {
            'success': True,
            'message': f'Demo: Generated XML for {mode} (simulated)',
            'device_count': 9 if mode == 'cmts' else 8 if mode == 'pe' else 17,
            'demo_mode': True
        }
        
        return jsonify({
            'success': True,
            'message': 'XML generation completed (demo mode)',
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
    """API endpoint to upload XML file (demo mode)"""
    try:
        filename = request.json.get('filename')
        
        logger.info(f"Demo: User {session['user'].get('preferred_username')} initiated XML upload: {filename}")
        
        # Simulate upload
        import time
        time.sleep(1)
        
        return jsonify({
            'success': True,
            'message': f'Demo: Upload of {filename} completed (simulated)'
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
        
        devices = []
        if device_type in ['all', 'cmts']:
            cmts_devices = demo_generator.generate_cmts_devices()
            for device in cmts_devices:
                device['type'] = 'CMTS'
                devices.append(device)
        
        if device_type in ['all', 'pe']:
            pe_devices = demo_generator.generate_pe_devices()
            for device in pe_devices:
                device['type'] = 'PE'
                devices.append(device)
        
        return jsonify({
            'success': True,
            'devices': devices,
            'count': len(devices),
            'demo_mode': True
        })
        
    except Exception as e:
        logger.error(f"Error fetching devices: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route("/download/<filename>")
@login_required
def download_xml(filename):
    """Download XML file (demo mode - generates sample)"""
    try:
        from io import BytesIO
        import gzip
        
        logger.info(f"Demo: User {session['user'].get('preferred_username')} downloading {filename}")
        
        # Generate sample XML content
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<EVE_LI_Targets xmlns="http://eve.li/schema">
    <Target type="{'CMTS' if 'CMTS' in filename or 'Infra' in filename else 'PE'}">
        <Hostname>demo-device-01</Hostname>
        <LoopbackIP>10.100.1.1</LoopbackIP>
        <Networks>
            <Network>203.80.0.0/22</Network>
            <Network>198.51.100.0/24</Network>
            <Network>2a02:1100::/40</Network>
        </Networks>
    </Target>
    <Target type="{'CMTS' if 'CMTS' in filename or 'Infra' in filename else 'PE'}">
        <Hostname>demo-device-02</Hostname>
        <LoopbackIP>10.100.2.1</LoopbackIP>
        <Networks>
            <Network>203.84.0.0/22</Network>
            <Network>198.51.104.0/24</Network>
            <Network>2a02:1200::/40</Network>
        </Networks>
    </Target>
</EVE_LI_Targets>'''
        
        # Compress the XML
        compressed = BytesIO()
        with gzip.GzipFile(fileobj=compressed, mode='wb') as gz:
            gz.write(xml_content.encode('utf-8'))
        compressed.seek(0)
        
        return send_file(
            compressed,
            mimetype='application/gzip',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error downloading XML: {e}")
        flash(f"Error downloading file: {str(e)}", "danger")
        return redirect(url_for("xml_status"))


@app.route("/api/view-xml/<filename>")
@login_required
def view_xml(filename):
    """View XML file content (demo mode)"""
    try:
        logger.info(f"Demo: User viewing {filename}")
        
        # Generate sample XML content (uncompressed for viewing)
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<EVE_LI_Targets xmlns="http://eve.li/schema">
    <Target type="{'CMTS' if 'CMTS' in filename or 'Infra' in filename else 'PE'}">
        <Hostname>demo-device-01</Hostname>
        <LoopbackIP>10.100.1.1</LoopbackIP>
        <Networks>
            <Network>203.80.0.0/22</Network>
            <Network>198.51.100.0/24</Network>
            <Network>2a02:1100::/40</Network>
        </Networks>
    </Target>
    <Target type="{'CMTS' if 'CMTS' in filename or 'Infra' in filename else 'PE'}">
        <Hostname>demo-device-02</Hostname>
        <LoopbackIP>10.100.2.1</LoopbackIP>
        <Networks>
            <Network>203.84.0.0/22</Network>
            <Network>198.51.104.0/24</Network>
            <Network>2a02:1200::/40</Network>
        </Networks>
    </Target>
    <Target type="{'CMTS' if 'CMTS' in filename or 'Infra' in filename else 'PE'}">
        <Hostname>demo-device-03</Hostname>
        <LoopbackIP>10.100.3.1</LoopbackIP>
        <Networks>
            <Network>203.88.0.0/22</Network>
            <Network>198.51.108.0/24</Network>
            <Network>2a02:1300::/40</Network>
        </Networks>
    </Target>
</EVE_LI_Targets>'''
        
        return xml_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"Error viewing XML: {str(e)}", exc_info=True)
        return f"Error loading XML: {str(e)}", 500


@app.route("/api/health")
def api_health():
    """API health check endpoint"""
    return jsonify({
        'status': 'ok',
        'version': APP_VERSION,
        'demo_mode': DEMO_MODE,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors"""
    return '', 204  # No Content


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
# Subnet Validation API Routes
# ============================================================================

@app.route("/api/validate-subnets/<device_name>")
@login_required
def api_validate_subnets(device_name):
    """Validate subnets for a specific device"""
    try:
        device_type = 'CMTS' if 'cmts' in device_name.lower() else 'PE'
        
        if device_type == 'CMTS':
            result = subnet_validator.validate_cmts_subnets(device_name)
        else:
            result = subnet_validator.get_pe_subnets(device_name)
        
        return jsonify({
            'success': True,
            'device_name': device_name,
            'device_type': device_type,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error validating subnets for {device_name}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/validate-all-subnets")
@login_required
def api_validate_all_subnets():
    """Validate subnets for all CMTS and PE devices"""
    try:
        cmts_devices = demo_generator.generate_cmts_devices()
        pe_devices = demo_generator.generate_pe_devices()
        
        validation_results = subnet_validator.validate_all_devices(cmts_devices, pe_devices)
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'results': validation_results
        })
    except Exception as e:
        logger.error(f"Error validating all subnets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Subnet Search Routes (NEW)
# ============================================================================

@app.route("/search")
@login_required
def search_page():
    """Subnet search results page"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template("search.html",
                             user=session.get("user"),
                             app_title=APP_TITLE,
                             app_version=APP_VERSION,
                             query='',
                             results=None,
                             demo_mode=DEMO_MODE)
    
    try:
        # Get devices and validation results
        cmts_devices = demo_generator.generate_cmts_devices()
        pe_devices = demo_generator.generate_pe_devices()
        validation_results = subnet_validator.validate_all_devices(cmts_devices, pe_devices)
        
        # Create lookup and search
        lookup = create_subnet_lookup(cmts_devices, pe_devices, validation_results)
        search_results = lookup.search(query)
        
        # Log search
        user_email = session['user'].get('email', session['user'].get('preferred_username', ''))
        audit_logger.log_search(user_email, query, search_results['total_matches'], request.remote_addr)
        
        return render_template("search.html",
                             user=session.get("user"),
                             app_title=APP_TITLE,
                             app_version=APP_VERSION,
                             query=query,
                             results=search_results,
                             demo_mode=DEMO_MODE)
    
    except Exception as e:
        logger.error(f"Error during search: {e}")
        flash(f"Search error: {e}", "danger")
        return render_template("search.html",
                             user=session.get("user"),
                             app_title=APP_TITLE,
                             app_version=APP_VERSION,
                             query=query,
                             results={'query_type': 'error', 'results': [], 'total_matches': 0},
                             demo_mode=DEMO_MODE)


@app.route("/api/search")
@login_required
def api_search():
    """API endpoint for subnet search"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'query': '', 'query_type': 'empty', 'results': [], 'total_matches': 0})
    
    try:
        cmts_devices = demo_generator.generate_cmts_devices()
        pe_devices = demo_generator.generate_pe_devices()
        validation_results = subnet_validator.validate_all_devices(cmts_devices, pe_devices)
        
        lookup = create_subnet_lookup(cmts_devices, pe_devices, validation_results)
        search_results = lookup.search(query)
        
        # Log search
        user_email = session['user'].get('email', session['user'].get('preferred_username', ''))
        audit_logger.log_search(user_email, query, search_results['total_matches'], request.remote_addr)
        
        return jsonify(search_results)
    
    except Exception as e:
        logger.error(f"API search error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Audit Log Routes (NEW)
# ============================================================================

@app.route("/audit-log")
@login_required
def audit_log_page():
    """Audit log activity feed"""
    try:
        # Get filter parameters
        limit = int(request.args.get('limit', 100))
        category = request.args.get('category', '')
        user_filter = request.args.get('user', '')
        
        # Get events
        if category or user_filter:
            events = audit_logger.get_recent_events(
                limit=limit,
                category=category if category else None,
                user=user_filter if user_filter else None
            )
        else:
            events = audit_logger.get_recent_events(limit=limit)
        
        # Get statistics
        stats = audit_logger.get_statistics()
        
        return render_template("audit_log.html",
                             user=session.get("user"),
                             app_title=APP_TITLE,
                             app_version=APP_VERSION,
                             events=events,
                             stats=stats,
                             current_category=category,
                             current_user=user_filter,
                             demo_mode=DEMO_MODE)
    
    except Exception as e:
        logger.error(f"Error loading audit log: {e}")
        flash(f"Error: {e}", "danger")
        return redirect(url_for("dashboard"))


@app.route("/api/audit-log/export")
@login_required
@require_permission(Permission.VIEW_AUDIT_LOG)
def api_audit_export():
    """Export audit log as CSV or JSON"""
    format_type = request.args.get('format', 'csv').lower()
    category = request.args.get('category', '')
    user_filter = request.args.get('user', '')
    
    try:
        # Get events
        if category or user_filter:
            events = audit_logger.get_recent_events(
                limit=10000,
                category=category if category else None,
                user=user_filter if user_filter else None
            )
        else:
            events = audit_logger.get_recent_events(limit=10000)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'json':
            # Export as JSON
            from io import BytesIO
            output = BytesIO()
            output.write(json.dumps(events, indent=2).encode('utf-8'))
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/json',
                as_attachment=True,
                download_name=f'audit_log_{timestamp}.json'
            )
        else:
            # Export as CSV
            import csv
            from io import StringIO, BytesIO
            
            si = StringIO()
            writer = csv.DictWriter(si, fieldnames=['timestamp', 'category', 'action', 'user', 'level', 'ip_address', 'details'])
            writer.writeheader()
            
            for event in events:
                row = event.copy()
                row['details'] = json.dumps(row.get('details', {}))
                writer.writerow(row)
            
            output = BytesIO()
            output.write(si.getvalue().encode('utf-8'))
            output.seek(0)
            
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'audit_log_{timestamp}.csv'
            )
    
    except Exception as e:
        logger.error(f"Error exporting audit log: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# User Management Routes (NEW)
# ============================================================================

@app.route("/user-management")
@login_required
@require_permission(Permission.MANAGE_USERS)
def user_management():
    """User management page (admin only)"""
    try:
        # Get all users
        users = rbac_manager.get_all_users()
        
        return render_template("user_management.html",
                             user=session.get("user"),
                             app_title=APP_TITLE,
                             app_version=APP_VERSION,
                             users=users,
                             demo_mode=DEMO_MODE)
    
    except Exception as e:
        logger.error(f"Error loading user management: {e}")
        flash(f"Error: {e}", "danger")
        return redirect(url_for("dashboard"))


@app.route("/api/users/change-role", methods=["POST"])
@login_required
@require_permission(Permission.MANAGE_USERS)
def api_change_user_role():
    """Change a user's role (admin only)"""
    try:
        data = request.get_json()
        email = data.get('email')
        new_role = data.get('new_role')
        
        if not email or not new_role:
            return jsonify({'success': False, 'message': 'Email and new_role are required'}), 400
        
        # Validate role
        if new_role not in Role.ALL_ROLES:
            return jsonify({'success': False, 'message': f'Invalid role: {new_role}'}), 400
        
        # Check if user exists
        if email not in rbac_manager.users:
            return jsonify({'success': False, 'message': f'User not found: {email}'}), 404
        
        # Update role
        old_role = rbac_manager.users[email]['role']
        rbac_manager.users[email]['role'] = new_role
        
        # Log the change
        current_user_email = session['user'].get('email', session['user'].get('preferred_username', ''))
        audit_logger.log_event(
            category='configuration',
            action='user_role_changed',
            user=current_user_email,
            level='info',
            details={
                'target_user': email,
                'old_role': old_role,
                'new_role': new_role
            },
            ip_address=request.remote_addr
        )
        
        logger.info(f"User {email} role changed from {old_role} to {new_role} by {current_user_email}")
        
        return jsonify({
            'success': True,
            'message': f'User {email} role changed to {new_role}',
            'user': rbac_manager.users[email]
        })
    
    except Exception as e:
        logger.error(f"Error changing user role: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Create necessary directories
    Path('logs').mkdir(exist_ok=True)
    Path('output').mkdir(exist_ok=True)
    
    # Get configuration
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    print("\n" + "="*60)
    print(f"🎭 {APP_TITLE}")
    print("="*60)
    print(f"Mode: DEMO (using mock data)")
    print(f"URL: http://{host}:{port}")
    print(f"Debug: {debug}")
    print("\n📝 Demo Features:")
    print("  ✓ No Azure AD required - auto-login")
    print("  ✓ No Netshot connection needed")
    print("  ✓ No DHCP database required")
    print("  ✓ Realistic mock data for 9 CMTS + 8 PE devices")
    print("  ✓ Simulated XML generation and uploads")
    print("\n🚀 Open your browser to http://localhost:5000")
    print("="*60 + "\n")
    
    logger.info(f"Starting {APP_TITLE}")
    logger.info(f"Demo mode: {DEMO_MODE}")
    logger.info(f"Listening on {host}:{port}")
    
    app.run(host=host, port=port, debug=debug)
