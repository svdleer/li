# Docker Deployment Guide

## Overview

This Docker setup provides **two deployment modes**:

### 1. Production Mode (`eve-li-web`)
- ✅ Full O365 authentication
- ✅ Real Netshot API integration
- ✅ MySQL cache & DHCP database (on Docker host)
- ✅ All production features

### 2. Demo Mode (`eve-li-web-demo`)
- ✅ No configuration required
- ✅ Auto-login (no O365)
- ✅ Mock data (9 CMTS + 8 PE devices)
- ✅ No external dependencies
- ✅ Perfect for testing & development

Both modes store data outside the container.

## Quick Start

### Demo Mode (No Configuration Needed)

```bash
# Build and run demo
docker-compose --profile demo up -d eve-li-web-demo

# Access at http://localhost:5000
# Auto-logged in as demo user
```

### Production Mode

```bash
# Configure .env file first (see Configuration section)
vi .env

# Build and run production
docker-compose up -d eve-li-web

# Access at http://localhost:5000
```

## Directory Structure

```
/path/to/app/
├── .env                    # Configuration (mounted read-only)
├── logs/                   # Application logs (mounted read-write)
├── output/                 # Generated XML files (mounted read-write)
├── .cache/                 # File cache (mounted read-write)
├── .flask_session/         # Session data (mounted read-write)
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Container orchestration
└── *.py                    # Application code (copied into image)
```

## Configuration

### 1. Create .env file

```bash
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=false

# Azure AD (if using O365 authentication)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_AUTHORITY=https://login.microsoftonline.com/your-tenant-id

# Netshot API
NETSHOT_API_URL=https://netshot.example.com/api
NETSHOT_USERNAME=your-username
NETSHOT_PASSWORD=your-password

# MySQL Cache (on Docker host)
DB_HOST=localhost
DB_PORT=3307
DB_DATABASE=li_xml_cache
DB_USER=your-user
DB_PASSWORD=your-password

# DHCP Database (on Docker host)
DHCP_DB_HOST=localhost
DHCP_DB_PORT=3306
DHCP_DB_DATABASE=dhcp_database
DHCP_DB_USER=your-user
DHCP_DB_PASSWORD=your-password

# Cache Settings
CACHE_ENABLED=true
CACHE_TTL=86400

# Upload API (optional)
UPLOAD_API_BASE_URL=https://upload.example.com
UPLOAD_API_USERNAME=upload-user
UPLOAD_API_PASSWORD=upload-password
```

### 2. Create required directories

```bash
mkdir -p logs output .cache .flask_session
chmod 755 logs output .cache .flask_session
```

## Build and Deploy

### Build the Docker image

```bash
docker-compose build
```

### Start the application

```bash
docker-compose up -d
```

### Check logs

```bash
docker-compose logs -f eve-li-web
```

### Stop the application

```bash
docker-compose down
```

## Network Configuration

The container uses **host network mode** (`network_mode: "host"`), which means:
- ✅ Container can access `localhost` on the Docker host
- ✅ MySQL on host:3306 and host:3307 is accessible as `localhost`
- ✅ Application listens on host port 5000 directly
- ⚠️ No port mapping needed (container shares host network)

**Alternative**: If you can't use host mode, use `extra_hosts`:
```yaml
services:
  eve-li-web:
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - DB_HOST=host.docker.internal
      - DHCP_DB_HOST=host.docker.internal
```

## Data Persistence

All data is stored OUTSIDE the container:

| Data | Location | Purpose |
|------|----------|---------|
| `.env` | Host | Configuration (read-only) |
| `logs/` | Host | Application logs |
| `output/` | Host | Generated XML files |
| `.cache/` | Host | Netshot/DHCP cache |
| `.flask_session/` | Host | User sessions |

**Benefit**: You can rebuild/restart the container without losing data!

## MySQL Database Setup

### On Docker Host

```bash
# Ensure MySQL is running
sudo systemctl status mysql

# Create databases if needed
mysql -u root -p <<EOF
CREATE DATABASE IF NOT EXISTS li_xml_cache;
CREATE DATABASE IF NOT EXISTS dhcp_database;
GRANT ALL PRIVILEGES ON li_xml_cache.* TO 'your-user'@'localhost';
GRANT ALL PRIVILEGES ON dhcp_database.* TO 'your-user'@'localhost';
FLUSH PRIVILEGES;
EOF

# Initialize cache schema
mysql -u root -p li_xml_cache < sql/dhcp_validation_cache.sql
```

## Health Check

The container includes automatic health checking:

```bash
# Check container health
docker ps

# Manual health check
curl http://localhost:5000/health
```

## Production Deployment

### 1. Enable SSL with Nginx (optional)

Uncomment the nginx service in docker-compose.yml and configure SSL:

```yaml
nginx:
  image: nginx:alpine
  network_mode: "host"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - ./ssl:/etc/nginx/ssl:ro
```

### 2. Run as systemd service

Create `/etc/systemd/system/eve-li-web.service`:

```ini
[Unit]
Description=EVE LI XML Generator
Requires=docker.service mysql.service
After=docker.service mysql.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/eve-li-web
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable eve-li-web
sudo systemctl start eve-li-web
```

## Troubleshooting

### Container can't connect to MySQL

```bash
# Check if MySQL is listening
netstat -tlnp | grep 3306
netstat -tlnp | grep 3307

# Test from within container
docker exec -it eve-li-web bash
curl -v telnet://localhost:3306
```

### Logs not appearing

```bash
# Check volume mounts
docker inspect eve-li-web | grep -A 10 Mounts

# Check permissions
ls -la logs/ output/ .cache/
```

### Application not starting

```bash
# Check logs
docker-compose logs eve-li-web

# Check if .env is loaded
docker exec eve-li-web env | grep DB_HOST
```

## Updating the Application

```bash
# Pull latest code
git pull

# Rebuild image
docker-compose build

# Restart with zero downtime
docker-compose up -d --no-deps --build eve-li-web
```

## Backup

```bash
# Backup data directories
tar -czf eve-li-backup-$(date +%Y%m%d).tar.gz logs/ output/ .cache/ .env

# Backup MySQL databases
mysqldump -u root -p li_xml_cache > backup-cache-$(date +%Y%m%d).sql
mysqldump -u root -p dhcp_database > backup-dhcp-$(date +%Y%m%d).sql
```
