# 🎭 EVE LI XML Generator - Demo Mode

## Quick Demo - No Setup Required!

Experience the full EVE LI XML Generator web interface with realistic mock data. **No Azure AD, Netshot, or database configuration needed!**

---

## 🚀 Launch Demo in 30 Seconds

### Option 1: Quick Launch (Recommended)

```bash
./run_demo.sh
```

Then open your browser to **http://localhost:5000**

### Option 2: Manual Launch

```bash
# Install dependencies (if needed)
pip install flask flask-session python-dotenv

# Run demo
python3 web_app_demo.py
```

---

## 🎬 What You'll See

### ✨ Features Available in Demo

- ✅ **Dashboard** with real-time statistics
  - 9 CMTS devices
  - 8 PE devices
  - System health status
  - Quick action buttons

- ✅ **Device Management**
  - CMTS devices with loopback IPs and subnets
  - DHCP scope information
  - PE devices with network configurations
  - Filter by device type

- ✅ **XML Status Page**
  - 20 mock XML files (10 days history)
  - File sizes and timestamps
  - Upload simulation
  - Log file viewer

- ✅ **Health Monitoring**
  - All systems showing "healthy" status
  - Component status cards
  - Real-time health checks

- ✅ **API Endpoints**
  - `/api/health` - System health
  - `/api/devices` - Device list
  - `/api/generate-xml` - XML generation
  - `/api/upload-xml` - XML upload

### 🔐 Authentication

**No Office 365 login required!** The demo automatically logs you in as "Demo User".

---

## 📊 Demo Data

### CMTS Devices (9 devices)
- Amsterdam, Rotterdam, Utrecht, Eindhoven, and more
- Realistic loopback IPs (10.100.x.x)
- Cable modem subnets (172.x.x.x/22)
- DHCP scope cross-referencing
- Management networks

### PE Devices (8 devices)
- Core, edge, border, and aggregation routers
- Business customer subnets
- Point-to-point links
- IPv6 networks
- Cisco IOS XR platform

### DHCP Scopes
- 8 scopes per CMTS device
- Cable interface mappings
- VLAN assignments
- Gateway configurations

### XML Files
- 20 compressed XML files (.xml.gz)
- 10 days of history
- CMTS and PE files
- Realistic file sizes (50-150 KB)

---

## 🎯 What Works in Demo Mode

| Feature | Status | Notes |
|---------|--------|-------|
| Dashboard | ✅ | Full statistics and charts |
| Device List | ✅ | All CMTS & PE devices |
| DHCP Integration | ✅ | Mock cross-referencing |
| XML Generation | ⚙️ | Simulated (1 sec delay) |
| XML Upload | ⚙️ | Simulated (1 sec delay) |
| Health Checks | ✅ | All systems healthy |
| API Endpoints | ✅ | Full REST API |
| Authentication | ⚙️ | Auto-login (no O365) |

**Legend:**
- ✅ Fully functional with mock data
- ⚙️ Simulated (no real action)

---

## 🎮 Try These Features

### 1. View Devices
1. Click **Devices** in navigation
2. See all CMTS devices with DHCP data
3. Switch to **PE** tab
4. Notice loopback IPs and subnets

### 2. Generate XML
1. Go to **Dashboard**
2. Click **Generate All XML**
3. Watch the loading indicator
4. See success message

### 3. Check Health
1. Click **Health** in navigation
2. See all systems healthy
3. Notice "Demo mode" indicators

### 4. Browse XML Files
1. Go to **XML Status**
2. See 20 XML files
3. Click **Upload** to simulate upload
4. View log files

### 5. Use API
```bash
# Health check
curl http://localhost:5000/api/health

# Get devices
curl http://localhost:5000/api/devices?type=cmts

# Generate XML (requires session)
curl -X POST http://localhost:5000/api/generate-xml \
  -H "Content-Type: application/json" \
  -d '{"mode":"both"}'
```

---

## 🛠️ Demo Architecture

```
web_app_demo.py
      ↓
demo_data.py (Mock Data Generator)
      ↓
Flask Templates (Same as production)
      ↓
Your Browser (http://localhost:5000)
```

**No external dependencies!**
- ❌ No Netshot API
- ❌ No DHCP Database
- ❌ No Azure AD
- ❌ No Docker required
- ✅ Just Python + Flask

---

## 📝 Demo Files

| File | Purpose |
|------|---------|
| `run_demo.sh` | Quick launcher script |
| `web_app_demo.py` | Demo web application |
| `demo_data.py` | Mock data generator |
| `.env.demo` | Demo environment config |

---

## 🔧 Customizing Demo Data

Edit `demo_data.py` to customize:

```python
# Change device counts
self.cmts_names = ["cmts-1", "cmts-2", ...]  # Add more

# Change locations
self.locations = ["London", "Paris", ...]

# Modify subnet ranges
def _generate_cmts_subnets(self, device_index: int):
    # Your custom subnets here
```

---

## 🚦 Starting/Stopping

### Start Demo
```bash
./run_demo.sh
```

### Stop Demo
Press `Ctrl+C` in the terminal

### Background Mode
```bash
python3 web_app_demo.py &
```

---

## 🎓 Learning Path

Use this demo to:

1. **Explore the UI** - Navigate all pages and features
2. **Understand data flow** - See how devices relate to subnets
3. **Test API** - Try the REST endpoints
4. **Review architecture** - Understand component interaction
5. **Plan deployment** - Decide on production configuration

---

## ⚡ Quick Comparison

| Feature | Demo Mode | Production Mode |
|---------|-----------|-----------------|
| Setup Time | 30 seconds | 30 minutes |
| Dependencies | Flask only | Netshot, DB, Azure |
| Data Source | Mock/Fake | Real devices |
| Authentication | Auto-login | Office 365 SSO |
| XML Generation | Simulated | Real files |
| Upload | Simulated | Real EVE LI API |

---

## 🎉 Next Steps

After trying the demo:

1. **Like it?** Follow the [QUICKSTART.md](QUICKSTART.md) for production setup
2. **Need changes?** Check [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md)
3. **Ready to deploy?** See [DEPLOYMENT.md](DEPLOYMENT.md)
4. **Questions?** Review the health page and logs

---

## 📞 Demo Support

### Common Issues

**Port 5000 already in use:**
```bash
# Change port in run_demo.sh
export FLASK_PORT=5001
python3 web_app_demo.py
```

**Flask not installed:**
```bash
pip3 install flask flask-session python-dotenv
```

**Permission denied:**
```bash
chmod +x run_demo.sh
```

---

## 🌟 Demo Highlights

```
┌─────────────────────────────────────────┐
│  🎭 DEMO MODE BENEFITS                  │
├─────────────────────────────────────────┤
│  ⚡ Instant startup - no config         │
│  🔒 No credentials needed               │
│  📊 Realistic data - 17 devices         │
│  🌐 Full web interface                  │
│  🎯 All features visible                │
│  🧪 Perfect for testing                 │
│  📚 Learning and training               │
│  🚀 Demo to stakeholders                │
└─────────────────────────────────────────┘
```

---

**🎬 Ready? Just run:** `./run_demo.sh`

**Then visit:** http://localhost:5000

**Enjoy the demo!** 🎉
