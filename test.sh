#!/bin/bash
"""
EVE LI XML Generator - Test Script
=================================

Quick test script to verify installation and configuration.
"""

# Configuration
VENV_PATH="/home/svdleer/python/venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo "EVE LI XML Generator - Test Suite"
echo "================================="

# Test 1: Virtual environment
echo_info "Testing virtual environment..."
if [ -d "$VENV_PATH" ]; then
    echo_info "✓ Virtual environment found at $VENV_PATH"
    source "$VENV_PATH/bin/activate"
    echo_info "✓ Virtual environment activated"
    
    # Check Python
    PYTHON_VER=$(python --version 2>&1)
    echo_info "✓ Python: $PYTHON_VER"
else
    echo_error "✗ Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Test 2: Required packages
echo_info "Testing required packages..."
PACKAGES=("requests" "mysql-connector-python" "lxml" "schedule")
for package in "${PACKAGES[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        echo_info "✓ Package $package is installed"
    else
        echo_error "✗ Package $package is missing"
    fi
done

# Test 3: Configuration files
echo_info "Testing configuration..."
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo_info "✓ .env file exists"
    
    # Check if .env has real credentials (not template values)
    if grep -q "your_database" "$SCRIPT_DIR/.env"; then
        echo_warn "⚠ .env file contains template values - please update with real credentials"
    else
        echo_info "✓ .env file appears to be configured"
    fi
else
    echo_warn "⚠ .env file missing - copying from template"
    cp "$SCRIPT_DIR/.env.template" "$SCRIPT_DIR/.env"
    echo_warn "⚠ Please edit .env with your actual credentials"
fi

# Test 4: Directories
echo_info "Testing directories..."
for dir in "output" "logs"; do
    if [ -d "$SCRIPT_DIR/$dir" ]; then
        echo_info "✓ Directory $dir exists"
    else
        echo_info "Creating directory $dir"
        mkdir -p "$SCRIPT_DIR/$dir"
    fi
done

# Test 5: Permissions
echo_info "Testing permissions..."
if [ -x "$SCRIPT_DIR/eve_li_xml_generator.py" ]; then
    echo_info "✓ Main script is executable"
else
    echo_info "Making main script executable"
    chmod +x "$SCRIPT_DIR/eve_li_xml_generator.py"
fi

# Test 6: Basic script functionality
echo_info "Testing basic script functionality..."
if python "$SCRIPT_DIR/eve_li_xml_generator.py" --help >/dev/null 2>&1; then
    echo_info "✓ Script loads successfully"
else
    echo_error "✗ Script failed to load"
fi

# Test 7: API/Database test (if configured)
echo_info "Testing API/Database connections..."
python "$SCRIPT_DIR/eve_li_xml_generator.py" --mode test 2>/dev/null && {
    echo_info "✓ API/Database test passed"
} || {
    echo_warn "⚠ API/Database test failed (expected if not configured)"
}

# Test 8: IPv6 validation
echo_info "Testing IPv6 validation..."
if [ -f "$SCRIPT_DIR/test_ipv6.py" ]; then
    python "$SCRIPT_DIR/test_ipv6.py" >/dev/null 2>&1 && {
        echo_info "✓ IPv6 validation test passed"
    } || {
        echo_warn "⚠ IPv6 validation test had issues"
    }
else
    echo_warn "⚠ IPv6 test script not found"
fi

echo ""
echo_info "Test Summary:"
echo "============="
echo "1. Edit .env file with your credentials"
echo "2. Test with: ./run.sh --mode test"
echo "3. Manual run: ./run.sh --mode vfz"
echo "4. Setup crontab with the provided examples"
echo "5. Configure status.php for web monitoring"

echo ""
echo_info "Crontab Example:"
echo "# EVE LI XML Generator"
echo "0 9 * * 1-5 $SCRIPT_DIR/run.sh --mode cron"

deactivate
