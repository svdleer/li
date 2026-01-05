#!/bin/bash
# Quick Demo Launcher for EVE LI XML Generator
# No configuration needed - just run!

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}║         EVE LI XML Generator - DEMO MODE                  ║${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠ Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python 3 found: $(python3 --version)"

# Check/install dependencies
echo ""
echo "Checking dependencies..."

if ! python3 -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Installing Flask...${NC}"
    pip3 install flask flask-session python-dotenv
else
    echo -e "${GREEN}✓${NC} Flask installed"
fi

# Create necessary directories
mkdir -p logs output .flask_session

# Set demo environment
export DEMO_MODE=true
export FLASK_DEBUG=true

# Launch demo
echo ""
echo -e "${GREEN}🚀 Starting Demo Application...${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "  Demo Features:"
echo -e "  ${GREEN}✓${NC} No configuration required"
echo -e "  ${GREEN}✓${NC} Auto-login (no Office 365 needed)"
echo -e "  ${GREEN}✓${NC} 9 CMTS devices with DHCP data"
echo -e "  ${GREEN}✓${NC} 8 PE devices with subnets"
echo -e "  ${GREEN}✓${NC} Realistic mock XML files"
echo -e "  ${GREEN}✓${NC} Simulated health monitoring"
echo ""
echo -e "  Access at: ${GREEN}http://localhost:5000${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Press Ctrl+C to stop the demo"
echo ""

# Run the demo app
python3 web_app_demo.py
