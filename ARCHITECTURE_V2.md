# EVE LI XML Generator v2.0 - Architecture Overview

## 🎯 Complete Transformation

The project has been completely refactored to integrate with **Netshot** for network device management and includes a modern **Flask-based web interface** with **Office 365 authentication**.

## 📋 New Architecture

### Data Sources
- **Netshot API**: Primary source for all device data
  - Device inventory with "IN PRODUCTION" status
  - Loopback interface addresses
  - Interface configurations and IP subnets
  
- **DHCP Database**: Cross-referencing for CMTS devices
  - DHCP scope management
  - Interface-to-scope mapping
  - Subnet validation

### Application Components

```
┌─────────────────────────────────────────────────┐
│          Flask Web Application                  │
│  (Office 365 Authentication)                    │
│                                                  │
│  - Dashboard                                     │
│  - Device Management                             │
│  - XML Status & History                          │
│  - Health Monitoring                             │
│  - Manual XML Push                               │
└──────────────┬──────────────────────────────────┘
               │
               ├──────────────┬──────────────────┐
               │              │                   │
       ┌───────▼───────┐  ┌──▼────────────┐  ┌─▼────────────┐
       │  Netshot API  │  │ DHCP Database │  │ EVE LI API   │
       │   Integration │  │  Integration  │  │   Upload     │
       └───────────────┘  └───────────────┘  └──────────────┘
               │              │
               │              │
       ┌───────▼──────────────▼───────────┐
       │  XML Generator (Core Engine)     │
       │  - VFZ/CMTS Processing           │
       │  - PE Device Processing          │
       │  - IP Validation (IPv4/IPv6)     │
       │  - Gzip Compression              │
       └──────────────────────────────────┘
```

## 🆕 New Features

### 1. Netshot Integration (`netshot_api.py`)
- ✅ Get devices with "IN PRODUCTION" status
- ✅ Automatic device family filtering (CMTS vs PE)
- ✅ Loopback interface extraction
- ✅ Subnet discovery from device interfaces
- ✅ Comprehensive error handling and logging

### 2. DHCP Cross-Referencing (`dhcp_integration.py`)
- ✅ CMTS interface matching with DHCP scopes
- ✅ Subnet enrichment from DHCP database
- ✅ Statistics and reporting
- ✅ Netmask to CIDR conversion

### 3. Web Interface (`web_app.py`)
- ✅ **Office 365 Authentication** with MSAL
- ✅ **Dashboard**: Real-time statistics and quick actions
- ✅ **Device Management**: View CMTS and PE devices
- ✅ **XML Status**: History, download, and upload
- ✅ **Health Monitoring**: System component status checks
- ✅ **API Endpoints**: RESTful API for automation
- ✅ **Responsive Design**: Bootstrap 5 UI

### 4. Docker Support
- ✅ **Dockerfile**: Production-ready container
- ✅ **Docker Compose**: Full stack deployment
- ✅ **Nginx**: Reverse proxy with SSL/TLS
- ✅ **Health Checks**: Automated monitoring
- ✅ **Volume Management**: Persistent data storage

## 🔧 Module Overview

### Core Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `netshot_api.py` | Netshot REST API client | `get_production_devices()`, `get_loopback_interface()`, `get_device_subnets()` |
| `dhcp_integration.py` | DHCP database integration | `get_dhcp_scopes()`, `cross_reference_cmts_interfaces()`, `enrich_cmts_device()` |
| `eve_li_xml_generator_v2.py` | XML generation engine | `process_vfz_devices()`, `process_pe_devices()`, `upload_xml_file()` |
| `web_app.py` | Flask web application | Dashboard, devices, XML status, health routes |

### Web Application Structure

```
web_app.py              # Flask application
├── templates/          # HTML templates
│   ├── base.html       # Base template with navigation
│   ├── index.html      # Landing page
│   ├── login.html      # Office 365 login
│   ├── dashboard.html  # Main dashboard
│   ├── devices.html    # Device list
│   ├── xml_status.html # XML file management
│   ├── health.html     # Health checks
│   └── error.html      # Error pages
├── static/
│   ├── css/
│   │   └── style.css   # Custom styles
│   └── js/
│       └── app.js      # JavaScript utilities
```

## 🚀 Deployment Options

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your settings

# Run web application
python web_app.py
```

### Docker (Recommended)
```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production with Nginx
```bash
# Start with production profile
docker-compose --profile production up -d

# This includes:
# - Flask application
# - Nginx reverse proxy
# - SSL/TLS termination
```

## 🔒 Security Features

1. **Authentication**:
   - Office 365 SSO integration
   - Session management with secure cookies
   - CSRF protection

2. **Network Security**:
   - Nginx reverse proxy
   - SSL/TLS encryption
   - Rate limiting
   - Security headers

3. **Data Protection**:
   - Environment variable configuration
   - No hardcoded credentials
   - Git-ignored sensitive files

## 📊 API Endpoints

### Public Endpoints
- `GET /api/health` - Health check (no auth)

### Authenticated Endpoints
- `POST /api/generate-xml` - Generate XML files
- `POST /api/upload-xml` - Upload XML to EVE LI
- `GET /api/devices` - Get device list

## 🔄 Migration from v1.0

### Breaking Changes
1. **Data Source**: Changed from custom API + database to Netshot API
2. **Configuration**: All settings now via environment variables
3. **Deployment**: Docker-first approach
4. **Authentication**: Added Office 365 requirement for web access

### Compatibility
- ✅ XML format remains unchanged
- ✅ Upload API integration preserved
- ✅ Logging structure compatible
- ✅ File naming conventions maintained

## 📝 Database Schema Requirements

### DHCP Database Tables

```sql
-- DHCP Scopes table (example)
CREATE TABLE dhcp_scopes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    network VARCHAR(45) NOT NULL,
    netmask VARCHAR(45) NOT NULL,
    gateway VARCHAR(45),
    cmts_hostname VARCHAR(255),
    cmts_interface VARCHAR(100),
    vlan_id INT,
    description TEXT,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_cmts ON dhcp_scopes(cmts_hostname, cmts_interface);
CREATE INDEX idx_active ON dhcp_scopes(active);
```

## 🧪 Testing

### Test Individual Components
```bash
# Test Netshot API
python netshot_api.py

# Test DHCP Integration
python dhcp_integration.py

# Test Web App
FLASK_DEBUG=true python web_app.py
```

### Health Checks
1. Visit `/health` page in web interface
2. Check `/api/health` endpoint
3. Review Docker container health status

## 📚 Additional Resources

- [Azure App Registration Guide](https://docs.microsoft.com/azure/active-directory/develop/quickstart-register-app)
- [Netshot API Documentation](https://www.netshot.info)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🆘 Troubleshooting

### Common Issues

1. **Office 365 Login Fails**
   - Verify `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET`
   - Check redirect URI in Azure App Registration
   - Ensure callback URL matches: `http://your-domain/auth/callback`

2. **Netshot Connection Failed**
   - Verify `NETSHOT_API_URL`, `NETSHOT_USERNAME`, `NETSHOT_PASSWORD`
   - Check network connectivity
   - Verify SSL certificate (or disable verification in code)

3. **DHCP Database Errors**
   - Verify database credentials
   - Check table schema matches requirements
   - Review database connectivity

4. **Docker Container Won't Start**
   - Check `.env` file exists and is properly configured
   - Review logs: `docker-compose logs eve-li-web`
   - Verify port 5000 is available

## 📧 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review health status at `/health`
3. Enable debug mode: `FLASK_DEBUG=true`
