# Quick Start Guide - EVE LI XML Generator v2.0

## 🚀 5-Minute Setup

### Prerequisites
- Docker & Docker Compose installed
- Azure AD app registration (for Office 365 auth)
- Netshot server access
- DHCP database access

### Step 1: Clone and Configure

```bash
# Navigate to project directory
cd /path/to/li

# Copy environment template
cp .env.template .env

# Edit configuration
nano .env
```

### Step 2: Configure Azure AD

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**:
   - Name: `EVE LI XML Generator`
   - Redirect URI: `http://your-domain:5000/auth/callback`
4. After creation, note the:
   - **Application (client) ID** → `AZURE_CLIENT_ID`
   - **Directory (tenant) ID**
5. Create a **Client Secret**:
   - Certificates & secrets > New client secret
   - Copy value → `AZURE_CLIENT_SECRET`
6. API Permissions:
   - Add **User.Read** permission (should be default)

### Step 3: Minimum Required .env Settings

```bash
# Flask
FLASK_SECRET_KEY=$(openssl rand -hex 32)

# Azure AD
AZURE_CLIENT_ID=your-app-id-here
AZURE_CLIENT_SECRET=your-secret-here

# Netshot
NETSHOT_API_URL=https://netshot.yourdomain.com/api
NETSHOT_USERNAME=admin
NETSHOT_PASSWORD=your-netshot-password

# Database
DB_HOST=your-db-host
DB_DATABASE=your-database
DB_USER=your-user
DB_PASSWORD=your-password

# EVE LI Upload
UPLOAD_API_BASE_URL=https://eve-server:2305
UPLOAD_API_USERNAME=xml_import
UPLOAD_API_PASSWORD=your-upload-password
```

### Step 4: Launch Application

```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f eve-li-web
```

### Step 5: Access Web Interface

1. Open browser: `http://localhost:5000`
2. Click **Sign in with Office 365**
3. Authenticate with your Microsoft account
4. Access dashboard

## 🎯 First Run Checklist

- [ ] Azure AD app registered
- [ ] `.env` file configured
- [ ] Docker services running
- [ ] Office 365 login successful
- [ ] Health checks passing (`/health` page)
- [ ] Netshot connection verified
- [ ] DHCP database connected

## 🔧 Common First-Run Tasks

### Generate First XML
1. Go to **Dashboard**
2. Click **Generate All XML**
3. Wait for completion
4. Check **XML Status** page

### View Devices
1. Navigate to **Devices** page
2. Select **All Devices** tab
3. Verify CMTS and PE devices appear

### Check System Health
1. Go to **Health** page
2. Verify all components show green ✅
3. Address any red ❌ items

## 🐛 Quick Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs eve-li-web

# Verify environment
docker-compose config

# Restart fresh
docker-compose down
docker-compose up -d
```

### Can't Login
- Verify `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET`
- Check redirect URI matches in Azure: `http://your-host:5000/auth/callback`
- Try incognito/private window

### No Devices Showing
- Check Netshot credentials in `.env`
- Test Netshot API: `curl -u user:pass https://netshot-url/api/devices`
- Review logs: `docker-compose logs eve-li-web`

## 📚 Next Steps

- Read [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md) for detailed architecture
- Review [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Check [README.md](README.md) for API documentation

## 🆘 Getting Help

1. Check health status: `http://localhost:5000/health`
2. Review logs: `docker-compose logs`
3. Enable debug mode: Set `FLASK_DEBUG=true` in `.env`
4. Test individual components:
   ```bash
   docker-compose exec eve-li-web python netshot_api.py
   docker-compose exec eve-li-web python dhcp_integration.py
   ```

## 🔒 Security Notes

- Change `FLASK_SECRET_KEY` to a random value
- Use HTTPS in production (enable nginx profile)
- Restrict database access
- Keep Azure secrets confidential
- Regular security updates: `docker-compose pull`
