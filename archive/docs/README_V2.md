# 🚀 EVE LI XML Generator v2.0

**Modern Network Device Management for EVE LI Compliance**

[![Docker](https://img.shields.io/badge/docker-ready-blue)](docker-compose.yml)
[![Python](https://img.shields.io/badge/python-3.11+-green)](requirements.txt)
[![License](https://img.shields.io/badge/license-GPL%20v2-blue)](LICENSE)

---

## ⚡ What's New in v2.0

This is a **complete transformation** of the EVE LI XML Generator with:

- 🔌 **Netshot Integration** - Get devices directly from Netshot with "IN PRODUCTION" filtering
- 🔄 **DHCP Cross-Referencing** - Automatically match CMTS interfaces with DHCP scopes
- 🌐 **Web Interface** - Modern Flask-based dashboard with real-time monitoring
- 🔐 **Office 365 Authentication** - Secure access with Microsoft SSO
- 🐳 **Docker Ready** - One-command deployment with Docker Compose
- 📊 **Health Monitoring** - Real-time system status checks
- 🎯 **API Endpoints** - RESTful API for automation

---

## 📸 Features Overview

### 🎛️ Dashboard
- Real-time device counts (CMTS & PE)
- System health status
- Recent XML files
- Quick action buttons
- One-click XML generation

### 📡 Device Management
- View all CMTS devices with DHCP enrichment
- View PE/Router devices
- Loopback addresses and subnets
- Filter by device type
- Real-time data from Netshot

### 📄 XML Status
- XML file history
- File size and timestamps
- Upload to EVE LI server
- Download generated files
- Processing logs

### ❤️ Health Monitoring
- Netshot API connectivity
- DHCP database status
- Upload endpoint status
- File system health
- Overall system status

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Docker & Docker Compose
- Azure AD app (for Office 365 auth)
- Netshot server access
- DHCP database access

### Step 1: Configure
```bash
# Copy environment template
cp .env.template .env

# Edit with your credentials
nano .env
```

### Step 2: Deploy
```bash
# Build and start
./docker-run.sh build
./docker-run.sh start

# Or use docker-compose directly
docker-compose up -d
```

### Step 3: Access
Open http://localhost:5000 and sign in with Office 365

**See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.**

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](QUICKSTART.md) | Get started in 5 minutes |
| [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md) | Technical architecture & design |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment guide |
| [FILE_STRUCTURE.md](FILE_STRUCTURE.md) | Complete file reference |
| [TRANSFORMATION_SUMMARY.md](TRANSFORMATION_SUMMARY.md) | What changed in v2.0 |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│     Flask Web Interface (Port 5000)     │
│   - Office 365 Authentication           │
│   - Dashboard & Device Management       │
│   - XML Status & Health Monitoring      │
└────────────┬────────────────────────────┘
             │
     ┌───────┼───────┐
     │       │       │
     ▼       ▼       ▼
┌─────────┐ ┌─────────┐ ┌─────────────┐
│ Netshot │ │  DHCP   │ │  EVE LI     │
│   API   │ │Database │ │ Upload API  │
└─────────┘ └─────────┘ └─────────────┘
     │         │             │
     └─────────┴─────────────┘
             │
     ┌───────▼────────┐
     │ XML Generator  │
     │  - VFZ/CMTS    │
     │  - PE Devices  │
     │  - Validation  │
     └────────────────┘
```

---

## 🔧 Components

### Core Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `netshot_api.py` | Netshot integration | Get devices, loopbacks, subnets |
| `dhcp_integration.py` | DHCP database | Cross-reference CMTS interfaces |
| `eve_li_xml_generator_v2.py` | XML generation | Process VFZ/PE, generate XML |
| `web_app.py` | Web application | Flask routes, authentication |

### Web Interface

- **Templates**: Bootstrap 5 responsive UI
- **Authentication**: Microsoft MSAL (Office 365)
- **API**: RESTful endpoints for automation
- **Monitoring**: Real-time health checks

---

## 🐳 Docker Deployment

### Development
```bash
docker-compose up -d
```

### Production (with Nginx)
```bash
docker-compose --profile production up -d
```

### Management Script
```bash
./docker-run.sh [build|start|stop|logs|status|test|backup]
```

---

## 🔒 Security

- ✅ Office 365 SSO authentication
- ✅ Session-based access control
- ✅ Environment variable configuration
- ✅ SSL/TLS via Nginx
- ✅ Rate limiting
- ✅ Security headers
- ✅ No hardcoded credentials

---

## 🧪 Testing

### Test Individual Components
```bash
# Test Netshot API
python netshot_api.py

# Test DHCP Integration
python dhcp_integration.py

# Test XML Generator
python eve_li_xml_generator_v2.py --mode test

# Test Web App
FLASK_DEBUG=true python web_app.py
```

### Health Check
```bash
curl http://localhost:5000/api/health
```

---

## 📊 API Endpoints

### Public
- `GET /api/health` - Health check (no auth)

### Authenticated
- `POST /api/generate-xml` - Generate XML files
- `POST /api/upload-xml` - Upload XML to EVE LI
- `GET /api/devices` - Get device list

---

## 🔄 Data Flow

1. **Netshot** provides device inventory with "IN PRODUCTION" status
2. **Loopback interfaces** extracted from device configurations
3. **Subnets** discovered from interface IP addresses
4. **DHCP database** cross-references CMTS interfaces with scopes
5. **XML Generator** creates compliant EVE LI XML files
6. **Gzip compression** reduces file size
7. **Upload API** sends to EVE LI server

---

## 📝 Configuration

All configuration via environment variables (`.env` file):

```bash
# Flask
FLASK_SECRET_KEY=your-secret-key
FLASK_PORT=5000

# Azure AD / Office 365
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-secret

# Netshot
NETSHOT_API_URL=https://netshot.domain.com/api
NETSHOT_USERNAME=admin
NETSHOT_PASSWORD=password

# Database
DB_HOST=localhost
DB_DATABASE=database_name
DB_USER=db_user
DB_PASSWORD=db_password

# EVE LI Upload
UPLOAD_API_BASE_URL=https://eve-server:2305
UPLOAD_API_USERNAME=xml_import
UPLOAD_API_PASSWORD=upload_password
```

See [.env.template](.env.template) for complete configuration options.

---

## 🆘 Troubleshooting

### Container Won't Start
```bash
docker-compose logs eve-li-web
docker-compose config  # Validate configuration
```

### Login Issues
- Verify Azure AD credentials
- Check redirect URI: `http://your-host:5000/auth/callback`
- Try incognito/private browser window

### No Devices Showing
- Test Netshot connection: `python netshot_api.py`
- Check credentials in `.env`
- Review logs: `docker-compose logs`

### Health Check Failing
Visit http://localhost:5000/health to see detailed status of each component.

---

## 🎯 Use Cases

### Network Operations
- Monitor active network devices
- View device configurations
- Track IP address allocations
- Generate compliance reports

### Compliance Teams
- Automated EVE LI XML generation
- Real-time device inventory
- Audit trails and logging
- Scheduled processing

### System Administrators
- Health monitoring dashboard
- Error tracking and alerts
- Performance metrics
- Backup and recovery

---

## 🛠️ Development

### Setup Development Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
nano .env

# Run development server
FLASK_DEBUG=true python web_app.py
```

### Project Structure
```
li/
├── Core Application
│   ├── netshot_api.py
│   ├── dhcp_integration.py
│   ├── eve_li_xml_generator_v2.py
│   └── web_app.py
├── Web Interface
│   ├── templates/
│   └── static/
├── Docker
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
└── Documentation
    ├── QUICKSTART.md
    ├── ARCHITECTURE_V2.md
    └── DEPLOYMENT.md
```

---

## 📜 License

GPL v2 - See LICENSE file for details

---

## 🤝 Contributing

This is an internal project. For questions or issues:
1. Check health status at `/health`
2. Review logs in `logs/` directory
3. Consult documentation in `docs/`
4. Contact system administrator

---

## 🎉 Credits

**Version 2.0 Transformation:**
- Netshot integration
- DHCP cross-referencing
- Web interface with Office 365 auth
- Docker deployment
- Comprehensive documentation

**Author:** Silvester van der Leer

---

## 📞 Support

- **Health Check**: http://localhost:5000/health
- **API Health**: http://localhost:5000/api/health
- **Logs**: `docker-compose logs -f`
- **Documentation**: See `QUICKSTART.md`

---

**🚀 Ready to deploy! Start with `./docker-run.sh build && ./docker-run.sh start`**
