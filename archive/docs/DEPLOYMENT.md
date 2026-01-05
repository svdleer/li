# Production Deployment Guide

## 🏭 Production Deployment Options

### Option 1: Docker with Nginx (Recommended)

#### Prerequisites
- Docker & Docker Compose
- SSL certificates
- Domain name with DNS configured
- Firewall rules configured

#### Step 1: Prepare SSL Certificates

```bash
# Create SSL directory
mkdir -p ssl

# Option A: Use your own certificates
cp /path/to/your/server.crt ssl/
cp /path/to/your/server.key ssl/

# Option B: Generate self-signed (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/server.key \
  -out ssl/server.crt \
  -subj "/C=NL/ST=State/L=City/O=Organization/CN=eve-li.yourdomain.com"

# Set permissions
chmod 600 ssl/server.key
chmod 644 ssl/server.crt
```

#### Step 2: Configure Production Environment

```bash
# Copy and edit environment
cp .env.template .env
nano .env

# Set production values
FLASK_DEBUG=false
UPLOAD_VERIFICATION_MODE=false  # Enable real uploads
```

#### Step 3: Deploy with Nginx

```bash
# Start production stack
docker-compose --profile production up -d

# Verify services
docker-compose ps

# Check logs
docker-compose logs -f
```

#### Step 4: Configure Firewall

```bash
# Allow HTTPS
sudo ufw allow 443/tcp

# Allow HTTP (for redirect)
sudo ufw allow 80/tcp

# Verify
sudo ufw status
```

### Option 2: Standalone with Gunicorn

#### Step 1: Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv libmariadb-dev gcc

# RHEL/CentOS
sudo yum install python3 python3-pip gcc mariadb-devel
```

#### Step 2: Setup Application

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
nano .env
```

#### Step 3: Run with Gunicorn

```bash
# Production run
gunicorn --bind 0.0.0.0:5000 \
         --workers 4 \
         --timeout 120 \
         --access-logfile logs/gunicorn-access.log \
         --error-logfile logs/gunicorn-error.log \
         web_app:app
```

#### Step 4: Setup Systemd Service

Create `/etc/systemd/system/eve-li.service`:

```ini
[Unit]
Description=EVE LI XML Generator Web Application
After=network.target

[Service]
Type=notify
User=eve-li
Group=eve-li
WorkingDirectory=/opt/eve-li
Environment="PATH=/opt/eve-li/venv/bin"
ExecStart=/opt/eve-li/venv/bin/gunicorn \
          --bind 0.0.0.0:5000 \
          --workers 4 \
          --timeout 120 \
          web_app:app
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable eve-li
sudo systemctl start eve-li
sudo systemctl status eve-li
```

### Option 3: Kubernetes Deployment

#### Step 1: Create ConfigMap

```bash
kubectl create configmap eve-li-config --from-env-file=.env
```

#### Step 2: Create Secrets

```bash
kubectl create secret generic eve-li-secrets \
  --from-literal=flask-secret-key=$(openssl rand -hex 32) \
  --from-literal=azure-client-secret='your-secret' \
  --from-literal=netshot-password='your-password' \
  --from-literal=db-password='your-db-password'
```

#### Step 3: Deploy Application

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eve-li-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: eve-li-web
  template:
    metadata:
      labels:
        app: eve-li-web
    spec:
      containers:
      - name: eve-li-web
        image: eve-li:latest
        ports:
        - containerPort: 5000
        envFrom:
        - configMapRef:
            name: eve-li-config
        - secretRef:
            name: eve-li-secrets
        volumeMounts:
        - name: logs
          mountPath: /app/logs
        - name: output
          mountPath: /app/output
        livenessProbe:
          httpGet:
            path: /api/health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: logs
        persistentVolumeClaim:
          claimName: eve-li-logs
      - name: output
        persistentVolumeClaim:
          claimName: eve-li-output
---
apiVersion: v1
kind: Service
metadata:
  name: eve-li-service
spec:
  selector:
    app: eve-li-web
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
  type: LoadBalancer
```

Apply:

```bash
kubectl apply -f k8s-deployment.yaml
```

## 🔒 Production Security Checklist

### Application Security
- [ ] Change `FLASK_SECRET_KEY` to strong random value
- [ ] Set `FLASK_DEBUG=false`
- [ ] Use HTTPS (SSL/TLS) for all traffic
- [ ] Configure proper CORS if needed
- [ ] Enable rate limiting (configured in nginx.conf)
- [ ] Regular security updates

### Network Security
- [ ] Firewall rules configured
- [ ] VPN/private network for database access
- [ ] Separate network for Netshot API
- [ ] DMZ for web application if needed

### Access Control
- [ ] Azure AD properly configured
- [ ] Restrict allowed users/groups
- [ ] Multi-factor authentication enabled
- [ ] Regular access audits

### Data Protection
- [ ] Database encrypted at rest
- [ ] Encrypted backups
- [ ] Secure credential storage (secrets management)
- [ ] Log rotation configured
- [ ] GDPR compliance if applicable

### Monitoring
- [ ] Application logs monitored
- [ ] Error alerting configured
- [ ] Performance monitoring
- [ ] Resource usage tracking
- [ ] Backup verification

## 📊 Monitoring & Logging

### Application Logs

```bash
# Docker
docker-compose logs -f eve-li-web

# Systemd
journalctl -u eve-li -f

# Log files
tail -f logs/eve_xml_$(date +%Y%m%d).log
```

### Health Monitoring

```bash
# Health check endpoint
curl http://localhost:5000/api/health

# Expected response:
{
  "status": "ok",
  "version": "2.0",
  "timestamp": "2025-12-30T12:00:00"
}
```

### Metrics Collection

For Prometheus monitoring, add to `docker-compose.yml`:

```yaml
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
```

## 🔄 Backup & Recovery

### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Daily backup script

DATE=$(date +%Y%m%d)
BACKUP_DIR=/backups/eve-li/$DATE

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup output files
tar -czf $BACKUP_DIR/output.tar.gz output/

# Backup logs
tar -czf $BACKUP_DIR/logs.tar.gz logs/

# Backup configuration (without secrets)
cp .env.template $BACKUP_DIR/

# Backup database (if applicable)
docker-compose exec -T db mysqldump \
  -u $DB_USER -p$DB_PASSWORD $DB_DATABASE \
  > $BACKUP_DIR/database.sql

# Delete old backups (keep 30 days)
find /backups/eve-li -type d -mtime +30 -exec rm -rf {} +
```

Schedule with cron:

```bash
# Run daily at 3 AM
0 3 * * * /opt/eve-li/backup.sh
```

### Recovery Procedure

```bash
# Stop services
docker-compose down

# Restore output files
tar -xzf /backups/eve-li/20251230/output.tar.gz

# Restore logs
tar -xzf /backups/eve-li/20251230/logs.tar.gz

# Restore database
docker-compose up -d db
sleep 10
cat /backups/eve-li/20251230/database.sql | \
  docker-compose exec -T db mysql -u $DB_USER -p$DB_PASSWORD $DB_DATABASE

# Restart services
docker-compose up -d
```

## 🔧 Maintenance

### Updates

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Log Rotation

Add to `/etc/logrotate.d/eve-li`:

```
/opt/eve-li/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 eve-li eve-li
    sharedscripts
    postrotate
        docker-compose -f /opt/eve-li/docker-compose.yml restart eve-li-web
    endscript
}
```

### Database Maintenance

```bash
# Optimize tables
docker-compose exec db mysql -u $DB_USER -p$DB_PASSWORD -e "
  OPTIMIZE TABLE eve_xml_log;
  OPTIMIZE TABLE eve_xml_status;
"

# Clean old logs (keep 90 days)
docker-compose exec db mysql -u $DB_USER -p$DB_PASSWORD -e "
  DELETE FROM eve_xml_log WHERE timestamp < DATE_SUB(NOW(), INTERVAL 90 DAY);
"
```

## 🚨 Troubleshooting Production Issues

### High Memory Usage

```bash
# Check container stats
docker stats eve-li-web

# Increase memory limit in docker-compose.yml
services:
  eve-li-web:
    mem_limit: 2g
    mem_reservation: 1g
```

### Slow Response Times

```bash
# Increase Gunicorn workers
gunicorn --workers 8 web_app:app

# Enable caching (add Redis)
# See caching section in ARCHITECTURE_V2.md
```

### Database Connection Issues

```bash
# Check database connectivity
docker-compose exec eve-li-web python -c "
from dhcp_integration import get_dhcp_integration
dhcp = get_dhcp_integration()
print('Connected!' if dhcp.test_connection() else 'Failed!')
"

# Increase connection timeout
DB_TIMEOUT=30
```

## 📞 Support Escalation

1. Check health endpoint: `/health`
2. Review application logs
3. Check system resources (CPU, memory, disk)
4. Verify external dependencies (Netshot, database)
5. Contact system administrator
6. Review Azure AD audit logs
