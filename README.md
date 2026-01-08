# EVE LI XML Generator

**Version 2.0** - Modern web-based application for generating and managing EVE LI (Lawful Interception) XML files for VodafoneZiggo network infrastructure.

## Overview

This application automatically generates EVE LI XML files from network device data retrieved from Netshot, validates subnet assignments against DHCP databases, and provides a comprehensive web interface for monitoring and management.

### Key Features

- 🌐 **Modern Web Interface** - Flask-based dashboard with role-based access control
- 🔐 **Office 365 Authentication** - Secure SSO integration (can be bypassed in development)
- 📊 **Real-time Monitoring** - Device status, XML generation, and system health
- 🤖 **Automated Scheduling** - Configurable XML generation and upload tasks
- 💾 **Smart Caching** - Optimized performance with MySQL-backed cache
- ✅ **Validation** - IP address, subnet, and DHCP cross-reference validation
- 📝 **Audit Logging** - Complete audit trail of all operations
- 🎨 **Responsive UI** - Bootstrap-based interface with dark mode support
- ⚙️ **Web-based Configuration** - Manage settings without editing files

## Architecture

```
┌─────────────────┐
│   Web Browser   │ ← Users access via web UI
└────────┬────────┘
         │ HTTPS
┌────────▼────────┐
│  Flask Web App  │ ← Python web application
│  (web_app.py)   │
└────────┬────────┘
         │
    ┌────┼────┬────────────┬─────────────┐
    │    │    │            │             │
┌───▼─┐ ┌▼──┐ ┌▼──────┐ ┌─▼──────┐ ┌───▼────┐
│MySQL│ │XML│ │Netshot │ │  DHCP  │ │ Cache  │
│Users│ │Gen│ │  API   │ │   DB   │ │  DB    │
└─────┘ └───┘ └────────┘ └────────┘ └────────┘
```

### Components

- **web_app.py** - Main Flask application with UI and REST API
- **eve_li_xml_generator_v2.py** - XML generation engine
- **netshot_api.py** - Netshot REST API client with caching
- **dhcp_integration.py** - DHCP database integration
- **cache_manager.py** - Performance caching layer
- **config_manager.py** - Database-backed configuration
- **rbac.py** - Role-based access control
- **audit_logger.py** - Audit trail logging

## Installation

### Prerequisites

- **Python 3.10+**
- **MySQL/MariaDB** database server
- **Docker** (recommended) or direct Python environment
- **SSH Tunnel** access to Netshot and MySQL servers (for remote deployment)

### Quick Start (Docker - Recommended)

1. **Clone the repository**:
```bash
git clone https://github.com/svdleer/li.git
cd li
```

2. **Configure environment variables**:
```bash
cp .env.local .env
# Edit .env with your settings
```

3. **Initialize the database**:
```bash
# Run the SQL scripts on your MySQL server
mysql -u root -p < sql/users.sql
mysql -u root -p < sql/settings.sql
mysql -u root -p < sql/dhcp_validation_cache.sql
```

4. **Deploy with Docker**:
```bash
./deploy-git.sh deploy
```

5. **Access the application**:
   - Local: http://localhost:8502
   - Via SSH tunnel: http://localhost:8080

### Manual Installation (Development)

1. **Create virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure settings**:
```bash
cp .env.local .env
# Edit .env with your database and API credentials
```

4. **Initialize database tables**:
```bash
# Import SQL files into your MySQL database
```

5. **Run the application**:
```bash
python web_app.py
```

## Configuration

### Initial Setup Wizard

On first launch, the application will:
1. Create a default admin user (`admin` / `admin`)
2. Redirect to the setup wizard at `/setup`
3. Initialize the settings table

**⚠️ IMPORTANT**: Change the default admin password immediately after first login!

### Settings Management

Admins can configure the application via the web UI at **Settings** menu:

#### MySQL Database
- **Host**: Database server hostname
- **Port**: Database server port (default: 3306)
- **Username**: Database user
- **Password**: Database password
- **Database**: Database name

#### Netshot API
- **URL**: Netshot API endpoint (e.g., `https://netshot.oss.local/api`)
- **API Key**: Netshot authentication key
- **CMTS Group**: Netshot device group ID for CMTS devices (default: 207)
- **PE Group**: Netshot device group ID for PE devices (default: 205)

### Environment Variables

Key environment variables in `.env`:

```ini
# Flask Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=8502
FLASK_DEBUG=False

# Session & Security
SECRET_KEY=your-secret-key-here
SESSION_TYPE=filesystem

# Bootstrap Database (for settings table access)
BOOTSTRAP_MYSQL_HOST=localhost
BOOTSTRAP_MYSQL_USER=access
BOOTSTRAP_MYSQL_PASSWORD=your-password
BOOTSTRAP_MYSQL_DATABASE=li_xml

# Azure AD OAuth (Optional)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# Caching
CACHE_ENABLED=true
CACHE_TTL=86400
CACHE_DIR=.cache
```

## Usage

### Web Interface

1. **Login**: Navigate to the web interface and login
   - Default: `admin` / `admin` (change this!)
   - Or use Office 365 SSO

2. **Dashboard**: View system overview
   - Device counts
   - XML generation status
   - Recent uploads
   - System health

3. **Devices**: Browse network devices
   - Filter by type (CMTS/PE)
   - View device details
   - Check loopback interfaces
   - Validate subnets

4. **XML Status**: Monitor XML generation
   - View generated files
   - Check upload status
   - Download XML files
   - Manual generation

   

5. **Settings** (Admin only):
   - Configure database connections
   - Update Netshot API settings
   - Modify device groups

6. **Users** (Admin only):
   - Manage user accounts
   - Assign roles
   - View user activity

### User Roles

- **Admin**: Full access - manage users, configure system, generate/upload XML
- **Operator**: Generate XML, run validations (cannot upload or configure)
- **Viewer**: Read-only access to dashboard and device information

### Manual XML Generation

Via Web UI:
1. Go to **XML Status**
2. Click **Generate XML Now**
3. Monitor progress in the dashboard

Via Command Line:
```bash
# Inside the Docker container or venv
python eve_li_xml_generator_v2.py
```

### Scheduled Tasks

Configure automated XML generation in the web UI:
1. Navigate to **Scheduled Tasks**
2. Enable/disable tasks
3. Set cron schedule
4. Monitor execution history

## Deployment

### Production Deployment (Docker)

1. **Setup SSH Tunnel** (for remote databases):
```bash
./ssh-tunnel.sh
```

2. **Deploy**:
```bash
./deploy-git.sh deploy
```

3. **Monitor**:
```bash
./deploy-git.sh logs
./deploy-git.sh status
```

4. **Stop**:
```bash
./deploy-git.sh stop
```

### Docker Compose

The application uses `docker-compose.yml` for container orchestration:

```yaml
services:
  eve-li-web:
    build: .
    ports:
      - "8502:8502"
    volumes:
      - ./output:/app/output
      - ./logs:/app/logs
      - ./.cache:/app/.cache
    env_file:
      - .env
```

### Health Checks

The application exposes a health check endpoint:
- URL: `/health`
- Returns: JSON with system status
- Used by Docker healthcheck

## API Endpoints

### REST API

The application provides REST APIs for integration:

- `GET /api/devices` - List all devices
- `GET /api/xml-status` - XML generation status
- `POST /api/generate-xml` - Trigger XML generation
- `GET /api/health` - System health check

Authentication required for all API calls.

## Troubleshooting

### Common Issues

1. **Container Restarting**
   - Check logs: `docker logs eve-li-web`
   - Verify database connection
   - Check environment variables

2. **Database Connection Failed**
   - Verify SSH tunnel is running
   - Check MySQL credentials in Settings
   - Ensure bootstrap credentials in .env are correct

3. **Netshot API Errors**
   - Verify API URL in Settings
   - Check API key is valid
   - Ensure SSL certificates are trusted

4. **Empty Settings Page**
   - Check browser console for errors
   - Verify settings table exists in database
   - Check logs for configuration manager errors

### Debug Mode

Enable debug logging:
```bash
# In .env
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
```

View logs:
```bash
tail -f logs/web_app.log
docker logs -f eve-li-web  # For Docker
```

## Development

### Project Structure

```
li/
├── web_app.py                 # Main Flask application
├── eve_li_xml_generator_v2.py # XML generation engine
├── netshot_api.py            # Netshot API client
├── dhcp_integration.py       # DHCP validation
├── config_manager.py         # Configuration management
├── rbac.py                   # Access control
├── audit_logger.py           # Audit logging
├── cache_manager.py          # Caching layer
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker image definition
├── docker-compose.yml       # Docker compose config
├── deploy-git.sh            # Deployment script
├── ssh-tunnel.sh            # SSH tunnel script
├── templates/               # Jinja2 templates
│   ├── base.html
│   ├── dashboard.html
│   ├── devices.html
│   ├── settings.html
│   └── ...
├── static/                  # Static assets
│   ├── css/
│   ├── js/
│   └── img/
├── sql/                     # Database schemas
│   ├── users.sql
│   ├── settings.sql
│   └── dhcp_validation_cache.sql
├── logs/                    # Application logs
├── output/                  # Generated XML files
└── archive/                 # Archived code/docs
```

### Running Tests

```bash
# Run connection tests
python test_netshot_connection.py

# Run diagnostic tests
python netshot_diagnostic.py
```

### Git Workflow

```bash
# Make changes
git add .
git commit -m "Description of changes"
git push

# Deploy automatically
./deploy-git.sh deploy
```

## Active Scripts

- **deploy-git.sh** - Main deployment script (pulls code, builds Docker, starts container)
- **ssh-tunnel.sh** - Creates SSH tunnel to remote MySQL/Netshot servers
- **refresh_cache.sh** - Manually refresh device cache

## License

Internal VodafoneZiggo tool - All rights reserved

## Support

For issues or questions:
- Check the logs in `logs/` directory
- Review Docker logs: `docker logs eve-li-web`
- Contact: Silvester van der Leer

## Version History

### v2.0 (Current)
- Modern web interface with Flask
- Database-backed configuration
- Role-based access control
- Office 365 SSO integration
- Improved caching and performance
- Comprehensive audit logging
- Setup wizard for easy deployment

### v1.0
- Original Perl-based scripts
- Command-line operation
- File-based configuration
