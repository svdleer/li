# Feature Improvements & Suggestions
**EVE LI XML Generator v2.0**  
Date: January 10, 2026

---

## Current State Analysis

### Email Notifications - ✅ IMPLEMENTED
**Status:** Already working!

Your application has email notification functionality built in via `email_notifier.py`.

**What's implemented:**
- HTML-formatted email notifications
- Password reset emails (working)
- Upload status emails (ready to use)
- SMTP configuration via environment variables

**Configuration (.env file):**
```bash
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@vodafoneziggo.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
EMAIL_FROM=noreply@vodafoneziggo.com
EMAIL_FROM_NAME=EVE LI XML Generator
EMAIL_TO=team@vodafoneziggo.com,admin@vodafoneziggo.com
WEB_URL=http://your-server:8080
```

**What's missing:**
- Email notifications are NOT currently triggered on XML generation success/failure
- No email alerts when Netshot or DHCP database goes down
- No scheduled daily summary reports

**Quick fix to enable:**
Add to `eve_li_xml_generator_v2.py` after XML generation:
```python
from email_notifier import send_upload_status_email

# After successful generation
send_upload_status_email(
    success=True,
    files_uploaded=['EVE_NL_Infra_CMTS-20260110.xml'],
    stats={'cmts_count': 157, 'pe_count': 0}
)

# On failure
send_upload_status_email(
    success=False,
    error_message=str(exception)
)
```

---

## Microsoft Teams Notifications - ❌ NOT IMPLEMENTED

### How Teams Webhooks Work

Microsoft Teams uses incoming webhooks to receive messages from external applications.

**Setup Steps:**

1. **Create Webhook in Teams:**
   - Open Teams channel
   - Click "..." next to channel name
   - Choose "Connectors" or "Workflows"
   - Find "Incoming Webhook"
   - Give it a name: "EVE LI Notifications"
   - Copy the webhook URL (looks like: `https://outlook.office.com/webhook/...`)

2. **Add to your .env file:**
   ```bash
   TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/abc123...
   TEAMS_ENABLED=true
   ```

3. **Implementation Code:**

Create new file: `teams_notifier.py`

```python
#!/usr/bin/env python3
"""
Microsoft Teams Notification Service
"""
import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class TeamsNotifier:
    """Send notifications to Microsoft Teams via webhook"""
    
    def __init__(self):
        self.enabled = os.getenv('TEAMS_ENABLED', 'false').lower() == 'true'
        self.webhook_url = os.getenv('TEAMS_WEBHOOK_URL', '')
        self.web_url = os.getenv('WEB_URL', 'http://localhost:8080')
    
    def send_notification(self, title, message, color="0078D4", facts=None):
        """
        Send notification to Teams
        
        Args:
            title: Message title
            message: Main message text
            color: Hex color (green=28a745, red=dc3545, blue=0078D4)
            facts: List of dicts with 'name' and 'value' keys
        """
        if not self.enabled or not self.webhook_url:
            logger.debug("Teams notifications disabled")
            return False
        
        facts = facts or []
        
        # Teams MessageCard format
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": color,
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "activitySubtitle": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "activityImage": "https://img.icons8.com/color/96/000000/xml.png",
                "facts": facts,
                "text": message
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "View Dashboard",
                "targets": [{
                    "os": "default",
                    "uri": f"{self.web_url}/dashboard"
                }]
            }]
        }
        
        try:
            response = requests.post(self.webhook_url, json=card, timeout=10)
            response.raise_for_status()
            logger.info(f"Teams notification sent: {title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return False
    
    def notify_success(self, operation, details=None):
        """Send success notification"""
        facts = details or []
        return self.send_notification(
            title=f"✅ {operation} Successful",
            message=f"{operation} completed successfully",
            color="28a745",
            facts=facts
        )
    
    def notify_failure(self, operation, error_message):
        """Send failure notification"""
        return self.send_notification(
            title=f"❌ {operation} Failed",
            message=f"Error: {error_message}",
            color="dc3545",
            facts=[
                {"name": "Operation", "value": operation},
                {"name": "Error", "value": error_message}
            ]
        )
    
    def notify_warning(self, title, message, details=None):
        """Send warning notification"""
        facts = details or []
        return self.send_notification(
            title=f"⚠️ {title}",
            message=message,
            color="ffc107",
            facts=facts
        )


def notify_xml_generation(success, cmts_count=0, pe_count=0, error=None):
    """Helper function to notify about XML generation"""
    notifier = TeamsNotifier()
    
    if success:
        facts = [
            {"name": "CMTS Devices", "value": str(cmts_count)},
            {"name": "PE Devices", "value": str(pe_count)},
            {"name": "Total", "value": str(cmts_count + pe_count)}
        ]
        notifier.notify_success("XML Generation", facts)
    else:
        notifier.notify_failure("XML Generation", error or "Unknown error")


def notify_system_health(netshot_ok, dhcp_ok):
    """Helper function to notify about system health issues"""
    notifier = TeamsNotifier()
    
    if not netshot_ok or not dhcp_ok:
        issues = []
        if not netshot_ok:
            issues.append("Netshot API unreachable")
        if not dhcp_ok:
            issues.append("DHCP database unreachable")
        
        notifier.notify_warning(
            "System Health Warning",
            "Critical system components are unavailable",
            [{"name": "Issues", "value": ", ".join(issues)}]
        )
```

4. **Usage Example:**

Add to your XML generation script:
```python
from teams_notifier import notify_xml_generation, notify_system_health

try:
    # Generate XML
    result = generator.process_vfz_devices()
    
    # Notify success
    notify_xml_generation(
        success=True,
        cmts_count=157,
        pe_count=0
    )
except Exception as e:
    # Notify failure
    notify_xml_generation(
        success=False,
        error=str(e)
    )
```

Add health monitoring:
```python
# In web_app.py scheduled task
netshot_ok = netshot_client.test_connection()
dhcp_ok = dhcp_db.test_connection()

if not netshot_ok or not dhcp_ok:
    notify_system_health(netshot_ok, dhcp_ok)
```

---

## Slack Notifications (Alternative)

If you prefer Slack over Teams:

**Setup:**
1. Create Slack App: https://api.slack.com/apps
2. Enable Incoming Webhooks
3. Add webhook to channel
4. Copy webhook URL

**Code (simpler than Teams):**
```python
def send_slack_notification(message, color="good"):
    webhook = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook:
        return
    
    payload = {
        "attachments": [{
            "color": color,  # good, warning, danger
            "text": message,
            "footer": "EVE LI XML Generator",
            "ts": int(datetime.now().timestamp())
        }]
    }
    
    requests.post(webhook, json=payload)
```

---

## Complete Feature Suggestions

### 1. Monitoring & Alerting (PRIORITY: HIGH)

#### A. Real-time Health Monitoring
**Missing:** Proactive health checks

**Implementation:**
```python
# Add to web_app.py
from apscheduler.schedulers.background import BackgroundScheduler

def scheduled_health_check():
    """Run every 5 minutes"""
    netshot_ok = get_netshot_client().test_connection()
    dhcp_ok = get_dhcp_integration().test_connection()
    
    if not netshot_ok or not dhcp_ok:
        # Send alerts
        send_alert_email("System Health Warning", issues)
        notify_system_health(netshot_ok, dhcp_ok)  # Teams
        
        # Log to audit
        audit.log(
            username='system',
            category='SYSTEM',
            action='Health check failed',
            details=f'Netshot: {netshot_ok}, DHCP: {dhcp_ok}'
        )

# Schedule it
scheduler.add_job(
    scheduled_health_check,
    'interval',
    minutes=5,
    id='health_check'
)
```

#### B. Alert Thresholds
**Missing:** Anomaly detection

**Implementation:**
```python
def check_device_count_anomaly():
    """Alert if device count drops significantly"""
    today_count = len(get_netshot_client().get_cmts_devices())
    
    # Get yesterday's count from audit log
    yesterday_count = get_historical_device_count(days_ago=1)
    
    if yesterday_count and today_count < (yesterday_count * 0.9):
        # 10% drop - something's wrong
        send_alert(
            f"⚠️ Device count dropped from {yesterday_count} to {today_count}",
            severity="warning"
        )
```

#### C. Daily Summary Reports
**Missing:** Scheduled email reports

**Implementation:**
```python
def send_daily_summary():
    """Send at 8 AM every day"""
    summary = {
        'generations_today': count_todays_generations(),
        'success_rate': calculate_success_rate(days=7),
        'device_count': get_current_device_count(),
        'issues': get_recent_issues()
    }
    
    send_summary_email(summary)
    notify_teams_summary(summary)

scheduler.add_job(
    send_daily_summary,
    CronTrigger(hour=8, minute=0),
    id='daily_summary'
)
```

---

### 2. Data Validation & Quality (PRIORITY: HIGH)

#### A. XML Schema Validation
**Missing:** Validate before upload

**Implementation:**
```python
import xmlschema

def validate_xml_against_schema(xml_file):
    """Validate XML against EVE schema"""
    schema_file = 'schemas/EVE_IAP_Import.xsd'
    
    try:
        schema = xmlschema.XMLSchema(schema_file)
        schema.validate(xml_file)
        return True, "Valid"
    except xmlschema.XMLSchemaException as e:
        return False, str(e)

# Use before upload
valid, message = validate_xml_against_schema('output/file.xml')
if not valid:
    notify_failure("XML Validation Failed", message)
    return  # Don't upload
```

#### B. Change Detection
**Missing:** Compare today vs yesterday

**Implementation:**
```python
def compare_device_lists():
    """Compare today's devices with yesterday's"""
    today = set(get_current_device_names())
    yesterday = set(get_historical_device_names(days_ago=1))
    
    new_devices = today - yesterday
    removed_devices = yesterday - today
    
    if new_devices or removed_devices:
        report = {
            'new': list(new_devices),
            'removed': list(removed_devices),
            'total_today': len(today),
            'total_yesterday': len(yesterday)
        }
        
        # Send notification
        if removed_devices:
            notify_warning(
                "Devices Removed",
                f"{len(removed_devices)} devices are missing",
                [{"name": "Missing", "value": ", ".join(list(removed_devices)[:10])}]
            )
        
        return report
    
    return None
```

#### C. Subnet Overlap Detection
**Missing:** Find conflicting subnets

**Implementation:**
```python
import ipaddress

def detect_subnet_overlaps(devices):
    """Find overlapping subnets"""
    subnets = {}
    overlaps = []
    
    for device in devices:
        for subnet_str in device.get('subnets', []):
            subnet = ipaddress.ip_network(subnet_str, strict=False)
            
            # Check against existing subnets
            for existing_device, existing_subnet in subnets.items():
                if subnet.overlaps(existing_subnet):
                    overlaps.append({
                        'device1': existing_device,
                        'subnet1': str(existing_subnet),
                        'device2': device['name'],
                        'subnet2': subnet_str
                    })
            
            subnets[device['name']] = subnet
    
    return overlaps
```

---

### 3. Backup & Recovery (PRIORITY: MEDIUM)

#### A. Automated XML Backups
**Missing:** Keep historical copies

**Implementation:**
```python
import shutil
from datetime import datetime

def backup_xml_files():
    """Backup XML files to dated folder"""
    backup_dir = Path('backups') / datetime.now().strftime('%Y-%m')
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    for xml_file in Path('output').glob('*.xml'):
        backup_file = backup_dir / xml_file.name
        shutil.copy2(xml_file, backup_file)
        logger.info(f"Backed up {xml_file.name}")
    
    # Cleanup old backups (keep 6 months)
    cleanup_old_backups(months=6)

# Run after each generation
scheduler.add_job(
    backup_xml_files,
    'cron',
    hour=5,
    minute=0
)
```

#### B. Database Backups
**Missing:** Backup user/config/audit data

**Implementation:**
```bash
#!/bin/bash
# backup_database.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/database"
mkdir -p $BACKUP_DIR

# Backup MySQL database
mysqldump -h localhost -u root li_xml > "$BACKUP_DIR/li_xml_$DATE.sql"

# Compress
gzip "$BACKUP_DIR/li_xml_$DATE.sql"

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Database backed up: li_xml_$DATE.sql.gz"
```

Add to crontab:
```
0 2 * * * /path/to/backup_database.sh
```

#### C. Configuration Export/Import
**Missing:** Backup settings

**Implementation:**
```python
def export_configuration():
    """Export all settings to JSON"""
    config_mgr = get_config_manager()
    settings = config_mgr.get_all_settings()
    
    export_file = f"config_backup_{datetime.now().strftime('%Y%m%d')}.json"
    with open(export_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    return export_file

def import_configuration(import_file):
    """Import settings from JSON"""
    with open(import_file) as f:
        settings = json.load(f)
    
    config_mgr = get_config_manager()
    for key, value in settings.items():
        config_mgr.set_setting(key, value)
```

---

### 4. Performance & Scalability (PRIORITY: MEDIUM)

#### A. Async XML Generation
**Missing:** Non-blocking generation

**Implementation:**
```python
from threading import Thread
import uuid

# Global task storage
active_tasks = {}

def generate_xml_background(task_id, mode, username):
    """Run in background thread"""
    try:
        active_tasks[task_id] = {'status': 'running', 'progress': 0}
        
        generator = EVEXMLGeneratorV2()
        
        if mode in ['vfz', 'both']:
            active_tasks[task_id]['progress'] = 25
            vfz_result = generator.process_vfz_devices()
        
        if mode in ['pe', 'both']:
            active_tasks[task_id]['progress'] = 75
            pe_result = generator.process_pe_devices()
        
        active_tasks[task_id] = {
            'status': 'completed',
            'progress': 100,
            'result': 'success'
        }
        
    except Exception as e:
        active_tasks[task_id] = {
            'status': 'failed',
            'error': str(e)
        }

@app.route("/api/generate-xml-async", methods=["POST"])
@login_required
def api_generate_xml_async():
    """Start async generation"""
    task_id = str(uuid.uuid4())
    mode = request.json.get('mode', 'both')
    username = session['user'].get('preferred_username')
    
    # Start background thread
    thread = Thread(
        target=generate_xml_background,
        args=(task_id, mode, username)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': 'Generation started'
    })

@app.route("/api/task-status/<task_id>")
@login_required
def api_task_status(task_id):
    """Check task status"""
    task = active_tasks.get(task_id, {'status': 'not_found'})
    return jsonify(task)
```

#### B. Pagination on Devices Page
**Missing:** Handle large device lists

**Implementation:**
```python
@app.route("/api/devices")
@login_required
def api_devices():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    all_devices = get_all_devices()
    total = len(all_devices)
    
    start = (page - 1) * per_page
    end = start + per_page
    devices = all_devices[start:end]
    
    return jsonify({
        'devices': devices,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': (total + per_page - 1) // per_page
    })
```

#### C. API Rate Limiting
**Missing:** Prevent abuse

**Implementation:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Apply to specific routes
@app.route("/api/generate-xml", methods=["POST"])
@limiter.limit("10 per hour")
@login_required
def api_generate_xml():
    # ... existing code
```

---

### 5. Security Enhancements (PRIORITY: HIGH)

#### A. Password Complexity
**Missing:** Enforce strong passwords

**Implementation:**
```python
import re

def validate_password_strength(password):
    """Enforce password rules"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain a number"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain special character"
    
    return True, "Password is strong"

# Use in user creation
valid, message = validate_password_strength(new_password)
if not valid:
    return jsonify({'error': message}), 400
```

#### B. Brute Force Protection
**Missing:** Login attempt limiting

**Implementation:**
```python
from datetime import datetime, timedelta

# Store failed attempts
login_attempts = {}

def check_brute_force(username):
    """Check if user is locked out"""
    if username not in login_attempts:
        return True
    
    attempts = login_attempts[username]
    
    # Remove old attempts (older than 15 minutes)
    cutoff = datetime.now() - timedelta(minutes=15)
    attempts = [a for a in attempts if a > cutoff]
    login_attempts[username] = attempts
    
    if len(attempts) >= 5:
        return False  # Locked out
    
    return True

def record_failed_login(username):
    """Record failed login attempt"""
    if username not in login_attempts:
        login_attempts[username] = []
    login_attempts[username].append(datetime.now())

# Use in login route
if not check_brute_force(username):
    return jsonify({
        'error': 'Too many failed attempts. Try again in 15 minutes.'
    }), 429
```

#### C. Security Headers
**Missing:** HTTP security headers

**Implementation:**
```python
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net"
    return response
```

---

### 6. Reporting & Analytics (PRIORITY: MEDIUM)

#### A. Dashboard Charts
**Missing:** Visual data representation

**Implementation using Chart.js:**

```html
<!-- In dashboard.html -->
<div class="card">
    <div class="card-body">
        <h5>Device Count Trend (Last 30 Days)</h5>
        <canvas id="deviceTrendChart"></canvas>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
// Fetch data from API
fetch('/api/device-trend')
    .then(r => r.json())
    .then(data => {
        new Chart(document.getElementById('deviceTrendChart'), {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'CMTS Devices',
                    data: data.cmts_counts,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }, {
                    label: 'PE Devices',
                    data: data.pe_counts,
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    });
</script>
```

**Backend API:**
```python
@app.route("/api/device-trend")
@login_required
def api_device_trend():
    """Get device count history"""
    # Query from audit log or new stats table
    stats = get_device_statistics(days=30)
    return jsonify(stats)
```

#### B. Success Rate Tracking
**Missing:** Track generation success

**Implementation:**
```python
# Add to database schema
"""
CREATE TABLE generation_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    mode VARCHAR(10),  -- vfz, pe, both
    success BOOLEAN,
    device_count INT,
    generation_time_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Track each generation:**
```python
def record_generation_stats(mode, success, device_count, elapsed_time, error=None):
    """Record generation statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO generation_stats 
        (date, mode, success, device_count, generation_time_seconds, error_message)
        VALUES (CURDATE(), %s, %s, %s, %s, %s)
    """, (mode, success, device_count, elapsed_time, error))
    
    conn.commit()
    cursor.close()
```

**Display success rate:**
```python
@app.route("/api/success-rate")
@login_required
def api_success_rate():
    """Calculate success rate for last 30 days"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
            AVG(generation_time_seconds) as avg_time
        FROM generation_stats
        WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    """)
    
    stats = cursor.fetchone()
    cursor.close()
    
    success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    return jsonify({
        'success_rate': round(success_rate, 2),
        'total_runs': stats['total'],
        'successful_runs': stats['successful'],
        'avg_time_seconds': round(stats['avg_time'], 2)
    })
```

---

### 7. Device Management (PRIORITY: LOW)

#### A. Device Maintenance Mode
**Missing:** Temporarily exclude devices

**Implementation:**
```python
# Add to database
"""
CREATE TABLE device_maintenance (
    device_name VARCHAR(255) PRIMARY KEY,
    reason TEXT,
    start_date DATETIME,
    end_date DATETIME,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**UI and API:**
```python
@app.route("/api/devices/<device_name>/maintenance", methods=["POST"])
@login_required
@require_permission(Permission.MODIFY_CONFIG)
def set_device_maintenance(device_name):
    """Put device in maintenance mode"""
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO device_maintenance 
        (device_name, reason, start_date, end_date, created_by)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        device_name,
        data.get('reason'),
        data.get('start_date'),
        data.get('end_date'),
        session['user'].get('preferred_username')
    ))
    
    conn.commit()
    return jsonify({'success': True})

# Filter out maintenance devices during generation
def get_active_devices():
    """Get devices not in maintenance"""
    all_devices = netshot_client.get_cmts_devices()
    
    # Check maintenance table
    maintenance_devices = get_maintenance_device_names()
    
    active = [d for d in all_devices 
              if d['name'] not in maintenance_devices]
    
    return active
```

---

### 8. Testing & Validation (PRIORITY: MEDIUM)

#### A. Dry-Run Mode
**Missing:** Test without uploading

**Implementation:**
```python
@app.route("/api/generate-xml", methods=["POST"])
@login_required
def api_generate_xml():
    dry_run = request.json.get('dry_run', False)
    
    if dry_run:
        logger.info("Running in DRY-RUN mode (no upload)")
    
    generator = EVEXMLGeneratorV2(dry_run=dry_run)
    result = generator.process_vfz_devices()
    
    if dry_run:
        return jsonify({
            'success': True,
            'message': 'DRY-RUN: XML generated but not uploaded',
            'file_path': result.get('file_path'),
            'device_count': result.get('device_count')
        })
```

#### B. XML Diff Tool
**Missing:** Compare two XML files

**Implementation:**
```python
import difflib
from lxml import etree

def compare_xml_files(file1, file2):
    """Generate diff between two XML files"""
    tree1 = etree.parse(file1)
    tree2 = etree.parse(file2)
    
    xml1 = etree.tostring(tree1, pretty_print=True).decode()
    xml2 = etree.tostring(tree2, pretty_print=True).decode()
    
    diff = list(difflib.unified_diff(
        xml1.splitlines(),
        xml2.splitlines(),
        fromfile=file1,
        tofile=file2,
        lineterm=''
    ))
    
    return '\n'.join(diff)

@app.route("/api/xml/compare")
@login_required
def api_compare_xml():
    """Compare two XML files"""
    file1 = request.args.get('file1')
    file2 = request.args.get('file2')
    
    diff = compare_xml_files(
        f'output/{file1}',
        f'output/{file2}'
    )
    
    return jsonify({
        'diff': diff,
        'has_changes': len(diff) > 0
    })
```

---

### 9. Operational Features (PRIORITY: LOW)

#### A. Maintenance Window Scheduling
**Missing:** Schedule downtime

**Implementation:**
```python
# Add to config_manager
def is_maintenance_window():
    """Check if current time is in maintenance window"""
    config = get_config_manager()
    
    maint_start = config.get_setting('maintenance_window_start')  # e.g., "02:00"
    maint_end = config.get_setting('maintenance_window_end')      # e.g., "04:00"
    
    if not maint_start or not maint_end:
        return False
    
    now = datetime.now().time()
    start = datetime.strptime(maint_start, "%H:%M").time()
    end = datetime.strptime(maint_end, "%H:%M").time()
    
    if start <= end:
        return start <= now <= end
    else:  # Crosses midnight
        return now >= start or now <= end

# Use in routes
@app.before_request
def check_maintenance():
    """Block requests during maintenance"""
    if is_maintenance_window():
        if request.path not in ['/api/health', '/login', '/logout']:
            return jsonify({
                'error': 'System is in maintenance mode',
                'retry_after': 'Check back after maintenance window'
            }), 503
```

#### B. Log Archival
**Missing:** Cleanup old logs

**Implementation:**
```python
def archive_old_logs():
    """Compress and archive logs older than 30 days"""
    import gzip
    import shutil
    
    log_dir = Path('logs')
    archive_dir = Path('logs/archive')
    archive_dir.mkdir(exist_ok=True)
    
    cutoff_date = datetime.now() - timedelta(days=30)
    
    for log_file in log_dir.glob('*.log'):
        if log_file.stat().st_mtime < cutoff_date.timestamp():
            # Compress
            gz_file = archive_dir / f"{log_file.name}.gz"
            with open(log_file, 'rb') as f_in:
                with gzip.open(gz_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove original
            log_file.unlink()
            logger.info(f"Archived {log_file.name}")

# Run monthly
scheduler.add_job(
    archive_old_logs,
    'cron',
    day=1,
    hour=3
)
```

---

## Implementation Priority Matrix

| Feature | Priority | Effort | Impact | Quick Win |
|---------|----------|--------|--------|-----------|
| Email alerts on generation | HIGH | Low | High | ✅ YES |
| Teams notifications | HIGH | Medium | High | ✅ YES |
| Async XML generation | HIGH | Medium | High | ✅ YES |
| Health monitoring | HIGH | Low | High | ✅ YES |
| Password complexity | HIGH | Low | Medium | ✅ YES |
| Dashboard charts | MEDIUM | Medium | Medium | ⚠️ Maybe |
| XML validation | HIGH | Low | High | ✅ YES |
| Device maintenance mode | LOW | Medium | Low | ❌ No |
| Backup automation | MEDIUM | Low | High | ✅ YES |
| Change detection | MEDIUM | Medium | Medium | ⚠️ Maybe |

---

## Quick Start Implementation Plan

### Week 1: Critical Alerts
1. Add Teams notification (1 day)
2. Enable email alerts on generation (1 day)
3. Add health check monitoring (1 day)
4. Implement anomaly detection (1 day)

### Week 2: Validation & Quality
1. XML schema validation (1 day)
2. Change detection report (1 day)
3. Success rate tracking (1 day)
4. Dashboard charts (2 days)

### Week 3: Performance
1. Async XML generation (2 days)
2. Progress indicators (1 day)
3. Pagination on devices (1 day)

### Week 4: Security & Backup
1. Password complexity (1 day)
2. Brute force protection (1 day)
3. Automated backups (1 day)
4. Security headers (1 day)

---

## Configuration Summary

### Environment Variables to Add

```bash
# Email Notifications (Already Configured)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@vodafoneziggo.com
SMTP_PASSWORD=your-password
EMAIL_TO=team@vodafoneziggo.com,admin@vodafoneziggo.com

# Teams Notifications (NEW)
TEAMS_ENABLED=true
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/YOUR_WEBHOOK_URL

# Slack Notifications (ALTERNATIVE)
SLACK_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Monitoring (NEW)
HEALTH_CHECK_INTERVAL=5  # minutes
ANOMALY_DETECTION_THRESHOLD=0.1  # 10% change
ALERT_ON_DEVICE_DROP=true

# Security (NEW)
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_SPECIAL=true
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15

# Backup (NEW)
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=90
AUTO_BACKUP_HOUR=2
```

---

## Dependencies to Add

```bash
# requirements.txt additions

# Teams/Slack notifications
requests>=2.28.0

# Charts and visualization
matplotlib>=3.5.0
plotly>=5.0.0

# XML validation
xmlschema>=2.0.0
lxml>=4.9.0

# Rate limiting
Flask-Limiter>=3.3.0

# Better logging
python-json-logger>=2.0.0
```

---

## Next Steps

1. **Review this document** - Which features do you want most?
2. **Set up Teams webhook** - Get the URL from your Teams admin
3. **Configure email** - Make sure SMTP settings are correct
4. **Start with alerts** - Implement Teams/email notifications first
5. **Add health monitoring** - Set up the 5-minute check
6. **Implement gradually** - Don't try to do everything at once

Would you like me to implement any of these features right now? I'd recommend starting with:
1. Teams notifications (immediate value)
2. Email alerts on generation (catches failures)
3. Health monitoring (proactive)

Let me know which ones you'd like to tackle first!
