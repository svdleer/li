#!/bin/bash
"""
Linux Setup Script for EVE LI XML Generator
===========================================

This script sets up the EVE LI XML Generator on Linux with virtual environment support.
"""

set -e  # Exit on any error

echo "EVE LI XML Generator - Linux Setup"
echo "=================================="

# Configuration
VENV_PATH="/home/svdleer/python/venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VERSION="3.8"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo_error "Virtual environment not found at $VENV_PATH"
    echo "Please create it first with:"
    echo "  python3 -m venv $VENV_PATH"
    exit 1
fi

echo_info "Using virtual environment: $VENV_PATH"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Check Python version
PYTHON_VER=$(python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo_info "Python version: $PYTHON_VER"

if [ "$(printf '%s\n' "$PYTHON_VERSION" "$PYTHON_VER" | sort -V | head -n1)" != "$PYTHON_VERSION" ]; then
    echo_warn "Python version $PYTHON_VER is older than recommended $PYTHON_VERSION"
fi

# Install/upgrade pip
echo_info "Upgrading pip..."
pip install --upgrade pip

# Install required packages
echo_info "Installing required packages..."
pip install -r requirements.txt

# Create necessary directories
echo_info "Creating directories..."
mkdir -p "$SCRIPT_DIR/output"
mkdir -p "$SCRIPT_DIR/logs"

# Set permissions
chmod 755 "$SCRIPT_DIR/eve_li_xml_generator.py"

# Create .env file if it doesn't exist
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo_info "Creating .env file from template..."
    cp "$SCRIPT_DIR/.env.template" "$SCRIPT_DIR/.env"
    echo_warn "IMPORTANT: Please edit .env with your actual credentials!"
    echo_warn "The .env file contains sensitive information and should not be committed to git"
else
    echo_info "✓ .env file already exists"
fi

# Check if .env is in .gitignore
if [ ! -f "$SCRIPT_DIR/.gitignore" ] || ! grep -q "^\.env$" "$SCRIPT_DIR/.gitignore"; then
    echo_info "Adding .env to .gitignore for security..."
    echo ".env" >> "$SCRIPT_DIR/.gitignore"
fi

# Test basic functionality
echo_info "Testing basic functionality..."
python "$SCRIPT_DIR/eve_li_xml_generator.py" --mode test || {
    echo_warn "Basic test failed - this is expected if database/API is not configured yet"
}

# Show crontab example
echo ""
echo_info "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your database and API credentials"
echo "2. Test the configuration:"
echo "   source $VENV_PATH/bin/activate"
echo "   python $SCRIPT_DIR/eve_li_xml_generator.py --mode test"
echo ""
echo "3. Add to crontab for automated runs:"
echo "   crontab -e"
echo ""
echo "   Add this line for weekday 9:00 AM runs:"
echo "   0 9 * * 1-5 source $VENV_PATH/bin/activate && python $SCRIPT_DIR/eve_li_xml_generator.py --mode cron"
echo ""
echo "   Or for frequent manual trigger checks:"
echo "   */15 8-18 * * 1-5 source $VENV_PATH/bin/activate && python $SCRIPT_DIR/eve_li_xml_generator.py --mode cron"
echo ""
echo "4. Setup PHP status page by editing database credentials in status.php"
echo "   (or better: modify status.php to also use .env file)"
echo ""
echo_warn "SECURITY: Remember to keep .env file secure and never commit it to git!"
echo ""
echo_info "Installation complete!"
