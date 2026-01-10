# EVE LI XML Generator - User Manual

**Version 2.0**  
Last updated: January 2026

---

## Table of Contents

1. [What This Application Does](#what-this-application-does)
2. [Main Python Scripts](#main-python-scripts)
3. [How the Web Interface Works](#how-the-web-interface-works)
4. [Understanding Flask Templates](#understanding-flask-templates)
5. [Daily Operations](#daily-operations)
6. [Common Tasks](#common-tasks)
7. [Troubleshooting](#troubleshooting)

---

## What This Application Does

This application automaticaly generates XML files for the EVE LI (Lawful Interception) system. It pulls network device information from Netshot, validates it against the DHCP database, and creates properly formatted XML files that get uploaded to the EVE system.

Think of it as a bridge between your network monitoring tools (Netshot) and the lawful interception platform (EVE). Instead of manually creating XML files with hundreds of devices, this does it all automaticly every day.

**Main functions:**
- Fetch CMTS and PE router data from Netshot
- Cross-check IP addresses with DHCP database
- Generate XML files in EVE format
- Upload files to EVE LI system
- Provide a web interface for monitoring and manual operations

---

## Main Python Scripts

Here's what each script does in plain english:

### web_app.py (Main Application)
**What it does:** This is the heart of the application - the web server that runs everything.

**Key features:**
- Provides the web interface you access in your browser
- Handles user login with Office 365 authentication
- Shows dashboard with device statistics
- Lets you generate XML files manually
- Manages scheduled tasks (automatic daily generation)
- Controls user permissions and access

**How to run it:**
```bash
python web_app.py
```

Then open your browser and go to the server address (usually port 5000).

### eve_li_xml_generator_v2.py (XML Generator)
**What it does:** The actual XML generation engine. Takes device data and creates EVE-formatted XML files.

**Process:**
1. Connects to Netshot API
2. Gets all CMTS and PE devices
3. Extracts loopback addresses and subnets
4. Validates subnets against DHCP database
5. Builds XML structure according to EVE schema
6. Saves files to output folder

Can be run standalone for testing:
```bash
python eve_li_xml_generator_v2.py --mode both
```

Options:
- `--mode vfz` - Only CMTS devices
- `--mode pe` - Only PE routers
- `--mode both` - Everything (default)

### netshot_api.py (Netshot Integration)
**What it does:** Talks to the Netshot server and gets device information.

**Features:**
- Fetches device lists from specific groups
- Gets interface configurations
- Extracts loopback addresses
- Runs diagnostics on Nokia devices
- Caches results to improve performance

This script doesn't run by itself - other scripts import and use it.

### dhcp_integration.py (DHCP Database)
**What it does:** Connects to the DHCP database to validate device subnets.

**Why we need this:** The EVE system needs to know which IP ranges (subnets) belong to which devices. The DHCP database has this information, so we cross-reference it to make sure everything matches up correctly.

### cache_manager.py (Performance Cache)
**What it does:** Stores frequently accessed data in memory (Redis) or database to speed things up.

**Why it helps:** Instead of querying Netshot every time someone loads a page, we cache the results for a few hours. This makes the web interface much faster and reduces load on Netshot.

Supports two backends:
- Redis (faster, recomended)
- MySQL (fallback if Redis isn't available)

### refresh_cache.py (Cache Pre-loader)
**What it does:** Runs before daily XML generation to pre-load all device data into cache.

**Purpose:** Makes XML generation faster by having all data ready beforehand. Usually runs as a cron job around 3:00 AM.

```bash
python refresh_cache.py --verbose
```

### config_manager.py (Settings Manager)
**What it does:** Manages application settings stored in MySQL database.

Instead of editing configuration files, settings are stored in the database and can be changed through the web interface (Settings page). Things like:
- Netshot connection details
- DHCP database credentials
- Scheduled task times
- Email notification settings

### audit_logger.py (Activity Logging)
**What it does:** Keeps track of who did what and when.

Every important action gets logged:
- User logins
- XML file generation
- Configuration changes
- Manual uploads

Useful for compliance and troubleshooting.

### rbac.py (Access Control)
**What it does:** Manages user roles and permisions.

**Roles available:**
- **Admin** - Full access to everything
- **Operator** - Can generate XML and view most things
- **Viewer** - Read-only access to dashboards and logs

### subnet_utils.py (IP Utilities)
**What it does:** Helper functions for working with IP addresses and subnets.

Contains functions like:
- Check if IP is public or private
- Extract subnet from CIDR notation
- Validate IP address format

### email_notifier.py (Notifications)
**What it does:** Sends email alerts when something goes wrong or when daily generation completes.

Configured in the Settings page - needs SMTP server details.

---

## How the Web Interface Works

The web interface is built with Flask (Python web framework) and uses Bootstrap for styling.

### Basic Architecture

```
User's Browser  →  Flask Web Server  →  Python Scripts  →  External Systems
     ↓                    ↓                    ↓                 ↓
  Dashboard           web_app.py        eve_generator.py      Netshot
  XML Status          (routes)          netshot_api.py        DHCP DB
  Settings                               dhcp_integration.py   EVE API
```

### How Requests Work

1. **User clicks something** (eg. "Generate XML" button)
2. **Browser sends request** to Flask server (eg. POST /api/generate-xml)
3. **web_app.py receives it** and finds the matching route function
4. **Python scripts do the work** (fetch data, generate XML, etc)
5. **Response sent back** to browser (success/error message)
6. **Page updates** to show results

### URL Routes (Endpoints)

Here are the main pages and what they do:

**Public routes:**
- `/` - Login page
- `/login` - Handle Office 365 authentication
- `/api/health` - Health check (no login needed)

**Protected routes (need login):**
- `/dashboard` - Main overview page
- `/devices` - List of all devices
- `/xml-status` - Recent XML files and generation status
- `/settings` - Application configuration
- `/audit-log` - Activity history
- `/user-management` - Manage users (admin only)

**API endpoints:**
- `/api/generate-xml` - Trigger manual XML generation
- `/api/devices` - Get device data as JSON
- `/api/upload-xml` - Upload XML file to EVE

---

## Understanding Flask Templates

Templates are HTML files that Flask uses to generate web pages. They're located in the `templates/` folder.

### Template Structure

#### base.html (Master Template)
This is the main layout that all other pages extend. Contains:

**Header section:**
- Bootstrap CSS and JavaScript links
- Custom CSS file (`style.css`)
- Navigation bar with logo and menu

**Navigation bar:**
```html
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <a class="navbar-brand" href="/">
        <img src="logo.png"> EVE LI XML Generator
    </a>
    <ul class="navbar-nav">
        <li><a href="/dashboard">Dashboard</a></li>
        <li><a href="/devices">Devices</a></li>
        <li><a href="/xml-status">XML Status</a></li>
        ...
    </ul>
</nav>
```

**Content area:**
```html
{% block content %}
    <!-- Other templates put their content here -->
{% endblock %}
```

**Footer:**
- Copyright notice
- Version info
- Logged in user name

#### dashboard.html (Dashboard Page)
Extends base.html and shows system overview.

**Main sections:**
1. **Status cards** - Show device counts
2. **Health indicators** - Netshot and database status
3. **Recent activity** - Last XML generations
4. **Quick actions** - Buttons for common tasks

**How it gets data:**
```python
# In web_app.py
@app.route("/dashboard")
def dashboard():
    stats = {
        'cmts_count': get_cmts_count(),
        'pe_count': get_pe_count(),
        'netshot_status': check_netshot()
    }
    return render_template('dashboard.html', stats=stats)
```

The template then uses these variables:
```html
<h2>CMTS Devices: {{ stats.cmts_count }}</h2>
<div class="badge bg-{{ 'success' if stats.netshot_status == 'connected' else 'danger' }}">
    {{ stats.netshot_status }}
</div>
```

#### devices.html (Device List)
Shows table of all devices with details.

**Features:**
- Search box (filters in real-time with JavaScript)
- Sort columns by clicking headers
- Color coding (green = OK, red = has issues)
- Click row to see device details

**Table structure:**
```html
<table class="table">
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Loopback</th>
            <th>Subnets</th>
            <th>DHCP Status</th>
        </tr>
    </thead>
    <tbody>
        {% for device in devices %}
        <tr class="{{ 'table-danger' if device.has_error else '' }}">
            <td>{{ device.name }}</td>
            <td>{{ device.type }}</td>
            <td>{{ device.loopback }}</td>
            <td>{{ device.subnet_count }}</td>
            <td>
                {% if device.dhcp_valid %}
                <span class="badge bg-success">OK</span>
                {% else %}
                <span class="badge bg-warning">Issues</span>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

#### xml_status.html (XML Generation Status)
Shows history of XML file generations.

**Information displayed:**
- File name and date
- Number of devices included
- File size
- Generation time (how long it took)
- Upload status
- Download link

#### settings.html (Configuration Page)
Form for changing application settings.

**Settings organized in tabs:**
1. **Netshot Connection** - API URL, credentials
2. **DHCP Database** - MySQL connection details
3. **Cache Settings** - Redis or MySQL cache
4. **Scheduled Tasks** - When to run daily generation
5. **Email Notifications** - SMTP server setup

Form uses Bootstrap styling and has validation.

### How Templates Communicate with Python

Flask uses Jinja2 templating engine. Variables from Python are passed to templates:

**Python side (web_app.py):**
```python
@app.route("/devices")
def devices():
    device_list = get_all_devices()  # Returns list of dicts
    return render_template('devices.html', 
                         devices=device_list,
                         page_title="Device List")
```

**Template side (devices.html):**
```html
<h1>{{ page_title }}</h1>

{% for device in devices %}
    <p>Device: {{ device.name }}</p>
{% endfor %}
```

**Template features:**
- `{{ variable }}` - Print variable value
- `{% if condition %}` - Conditional logic
- `{% for item in list %}` - Loop through lists
- `{% block name %}` - Define reusable sections
- `{% extends 'base.html' %}` - Inherit from another template

### Static Files (CSS, JavaScript, Images)

Located in `static/` folder:

**static/css/style.css** - Custom styling:
- Color scheme (VodafoneZiggo red)
- Card layouts
- Button styles
- Responsive design rules

**static/js/** - JavaScript files:
- Real-time search/filter
- AJAX requests for dynamic updates
- Form validation
- Chart/graph rendering

**static/img/** - Images:
- Company logo
- Icons
- Placeholder images

Templates reference these like:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
<img src="{{ url_for('static', filename='img/logo.png') }}">
```

---

## Daily Operations

### Automatic Daily XML Generation

The system is configured to automatically generate and upload XML files every day.

**Schedule (typical):**
1. **03:00** - Cache refresh starts (`refresh_cache.py`)
2. **04:00** - XML generation begins
3. **04:30** - Files uploaded to EVE
4. **05:00** - Email notification sent with results

**Where to check:**
- Dashboard shows last generation time
- XML Status page lists all generated files
- Audit Log has detailed generation history

### What Gets Generated

Two XML files per day:
- `EVE_NL_Infra_CMTS-YYYYMMDD.xml` - CMTS devices
- `EVE_NL_SOHO-YYYYMMDD.xml` - PE routers

Both saved to `output/` folder.

---

## Common Tasks

### Generate XML Manually

Sometimes you need to generate XML outside the scheduled time.

**Via Web Interface:**
1. Login to web interface
2. Go to Dashboard
3. Click "Generate XML Now" button
4. Select type (CMTS, PE, or Both)
5. Click "Start Generation"
6. Wait for completion (progress bar shows status)
7. Files appear in XML Status page

**Via Command Line:**
```bash
# Generate both
python eve_li_xml_generator_v2.py --mode both

# Only CMTS
python eve_li_xml_generator_v2.py --mode vfz

# Only PE
python eve_li_xml_generator_v2.py --mode pe
```

### Check Device Status

**Web Interface:**
1. Go to Devices page
2. Use search box to find specific device
3. Click device name for detailed view
4. Check DHCP validation status
5. View all subnets and loopbacks

**Important indicators:**
- Green badge = Everything OK
- Yellow badge = Minor issues (maybe missing DHCP entry)
- Red badge = Critical problem (needs attention)

### Update Settings

**Via Web Interface (recommended):**
1. Login as Admin user
2. Go to Settings page
3. Click tab for setting you want to change
4. Edit value
5. Click "Save Changes"
6. Settings take effect immediately

**Important:** Some settings (like Netshot URL) require restarting the application to fully apply.

### View Logs

**Audit Log (web interface):**
- Shows user actions
- Can filter by user, action type, date
- Export to CSV for further analysis

**Server Logs (files):**
- Located in `logs/` folder
- Separate files for different components:
  - `web_app.log` - Web server activity
  - `xml_generation.log` - XML generation details
  - `cache_refresh.log` - Cache operations
  - `error.log` - Errors only

**View logs:**
```bash
# Last 100 lines
tail -100 logs/web_app.log

# Follow live
tail -f logs/web_app.log

# Search for errors
grep ERROR logs/*.log
```

### Add New User

Only admins can add users.

1. Go to User Management page
2. Click "Add New User"
3. Enter email address
4. Select role (Admin, Operator, or Viewer)
5. Click "Create User"
6. User gets email with login instructions

### Change Scheduled Time

1. Go to Settings
2. Click "Scheduled Tasks" tab
3. Find "Daily XML Generation"
4. Change time (use 24-hour format, eg: 04:00)
5. Save changes
6. New schedule takes effect next day

---

## Troubleshooting

### Problem: Web Interface Won't Load

**Possible causes:**
- Application not running
- Port already in use
- Python environment not activated

**Solutions:**
```bash
# Check if running
ps aux | grep web_app

# Restart application
python web_app.py

# Check port (default 5000)
lsof -i :5000

# Use different port
export FLASK_PORT=8080
python web_app.py
```

### Problem: "Cannot Connect to Netshot"

**Check:**
1. Is Netshot server running?
2. Is URL correct in Settings?
3. Is API token valid?
4. Network connectivity OK?

**Test connection:**
```python
python -c "from netshot_api import get_netshot_client; \
    client = get_netshot_client(); \
    print('Connected!' if client.test_connection() else 'Failed')"
```

**Fix:**
- Verify Netshot URL in Settings
- Generate new API token in Netshot
- Check firewall rules

### Problem: XML Generation Fails

**Common causes:**
- No devices found in Netshot
- DHCP database unreachable
- Invalid data (missing loopbacks)

**Check:**
1. Dashboard health indicators (should be green)
2. Device count (should be > 0)
3. Recent errors in Audit Log

**Debug:**
```bash
# Test with verbose output
python eve_li_xml_generator_v2.py --mode test

# Check individual components
python -c "from netshot_api import get_netshot_client; \
    c = get_netshot_client(); \
    devices = c.get_cmts_devices(); \
    print(f'Found {len(devices)} CMTS devices')"
```

### Problem: Slow Performance

**Likely causes:**
- Cache not working (check Redis)
- Too many devices (> 500)
- Network latency to Netshot

**Improve performance:**
1. Enable Redis cache (faster than MySQL)
2. Run cache refresh before busy hours
3. Increase cache TTL in Settings

**Check cache status:**
```bash
# Redis
redis-cli ping

# MySQL cache
mysql -u access -p li_xml -e "SELECT COUNT(*) FROM cache;"
```

### Problem: Users Can't Login

**Office 365 authentication issues:**
1. Check Azure AD configuration
2. Verify redirect URI matches application URL
3. Ensure user email matches Azure AD

**Bypass for testing:**
```bash
# Set environment variable
export AUTH_BYPASS=true
python web_app.py
```

**Warning:** Only use AUTH_BYPASS in development!

### Problem: DHCP Validation Shows Errors

**Why it happens:**
- Device subnets not in DHCP database
- Hostname mismatch between Netshot and DHCP
- Private subnets being flagged

**Usually not critical** - XML will still generate with available data.

**To investigate:**
```bash
# Run diagnostic script
python archive/diagnostic_scripts/check_device_dhcp.py device-name
```

### Getting Help

**Error Messages:**
- Check `logs/error.log` for detailed stack traces
- Copy full error message for troubleshooting

**Support:**
- Review this manual first
- Check Audit Log for recent changes
- Export logs and send to support team

**Useful commands for support:**
```bash
# System info
python --version
pip list | grep -i flask

# Recent errors
tail -50 logs/error.log

# Configuration check
python -c "from config_manager import get_config_manager; \
    c = get_config_manager(); \
    print('Config DB:', c.test_connection())"
```

---

## Quick Reference

### File Locations

| Item | Path |
|------|------|
| Main app | `web_app.py` |
| XML output | `output/` |
| Logs | `logs/` |
| Templates | `templates/` |
| Config | `.env` file or database |
| Cache | `.cache/` or Redis |

### Important URLs

| Page | URL |
|------|-----|
| Dashboard | `/dashboard` |
| Devices | `/devices` |
| XML Status | `/xml-status` |
| Settings | `/settings` |
| API Health | `/api/health` |

### Scheduled Tasks

| Task | Time | Script |
|------|------|--------|
| Cache Refresh | 03:00 | `refresh_cache.py` |
| XML Generation | 04:00 | `eve_li_xml_generator_v2.py` |
| Upload to EVE | 04:30 | via `web_app.py` scheduler |

### User Roles

| Role | Can Do |
|------|--------|
| Admin | Everything including user management and settings |
| Operator | Generate XML, view devices, check status |
| Viewer | Read-only access to dashboards and reports |

---

**End of Manual**

For questions or issues, contact your system administrator.
