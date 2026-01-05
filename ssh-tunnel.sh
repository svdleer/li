#!/bin/bash
# SSH Tunnels for EVE LI Local Testing with ControlMaster
# ========================================================
# This script uses SSH ControlMaster for efficient connection multiplexing
# All tunnels share a single SSH connection that persists for 10 minutes
#
# Usage: ./ssh-tunnel.sh start|stop|status|restart|test

# ============================================================================
# Configuration - UPDATE THESE VALUES
# ============================================================================
JUMP_SERVER="svdleer@script3a.oss.local"
SSH_KEY="${HOME}/.ssh/id_rsa"
CONTROL_PATH="${HOME}/.ssh/cm-%r@%h:%p"
CONTROL_PERSIST="10m"

# Target servers (internal hosts accessible from bastion)
NETSHOT_HOST="netshot.oss.local"
NETSHOT_PORT="443"

DB_HOST="appdb.oss.local"
DB_PORT="3306"

DHCP_DB_HOST="appdb.oss.local"
DHCP_DB_PORT="3306"

# NOTE: Upload API tunnel is NOT needed when using mock_upload_server.py locally
# The mock server runs directly on localhost:2305
# Uncomment below if you need to tunnel to a real test server
# UPLOAD_API_HOST="172.17.130.71"
# UPLOAD_API_PORT="2305"

# Local ports
LOCAL_NETSHOT_PORT="8443"
LOCAL_DB_PORT="3306"
LOCAL_DHCP_PORT="3307"
# LOCAL_UPLOAD_PORT="2305"  # Not needed with mock server

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# Functions
# ============================================================================

check_control_master() {
    # Check if control master connection exists
    ssh -O check -S "$CONTROL_PATH" "$JUMP_SERVER" 2>/dev/null
    return $?
}

start_control_master() {
    echo -e "${YELLOW}Starting SSH ControlMaster connection...${NC}"
    
    # Start master connection in background
    ssh -f -N -M \
        -S "$CONTROL_PATH" \
        -o ControlPersist="$CONTROL_PERSIST" \
        -i "$SSH_KEY" \
        "$JUMP_SERVER"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ ControlMaster connection established${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to establish ControlMaster connection${NC}"
        return 1
    fi
}

stop_control_master() {
    if check_control_master; then
        echo -e "${YELLOW}Stopping SSH ControlMaster connection...${NC}"
        ssh -O exit -S "$CONTROL_PATH" "$JUMP_SERVER" 2>/dev/null
        echo -e "${GREEN}✓ ControlMaster connection stopped${NC}"
    fi
}

start_tunnel() {
    local name=$1
    local local_port=$2
    local remote_host=$3
    local remote_port=$4
    
    # Check if port is already in use
    if lsof -Pi :$local_port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Port $local_port already in use, skipping $name${NC}"
        return 1
    fi
    
    # Start tunnel using existing control master
    ssh -f -N \
        -S "$CONTROL_PATH" \
        -L "${local_port}:${remote_host}:${remote_port}" \
        "$JUMP_SERVER" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $name tunnel: localhost:$local_port -> $remote_host:$remote_port${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to start $name tunnel${NC}"
        return 1
    fi
}

case "$1" in
  start)
    echo -e "\n${YELLOW}Starting SSH tunnels...${NC}"
    echo "================================"
    
    # Ensure control master is running
    if ! check_control_master; then
        start_control_master || exit 1
        sleep 1
    fi
    
    # Start individual tunnels (all use the same connection)
    start_tunnel "Netshot API" "$LOCAL_NETSHOT_PORT" "$NETSHOT_HOST" "$NETSHOT_PORT"
    start_tunnel "MySQL Database" "$LOCAL_DB_PORT" "$DB_HOST" "$DB_PORT"
    start_tunnel "DHCP Database" "$LOCAL_DHCP_PORT" "$DHCP_DB_HOST" "$DHCP_DB_PORT"
    # Upload tunnel not needed - use mock_upload_server.py instead
    
    echo "================================"
    echo -e "${GREEN}All tunnels started!${NC}\n"
    
    echo -e "${YELLOW}Add these to your .env file:${NC}"
    echo "NETSHOT_API_URL=https://localhost:${LOCAL_NETSHOT_PORT}/api"
    echo "DB_HOST=localhost"
    echo "DB_PORT=${LOCAL_DB_PORT}"
    echo "DHCP_DB_HOST=localhost"
    echo "DHCP_DB_PORT=${LOCAL_DHCP_PORT}"
    echo ""
    echo "# For testing uploads, run: python mock_upload_server.py"
    echo "UPLOAD_API_BASE_URL=http://localhost:2305"
    echo "UPLOAD_VERIFICATION_MODE=false  # Set to false to actually upload to mock server"
    echo ""
    ;;
    
  stop)
    echo -e "\n${YELLOW}Stopping SSH tunnels...${NC}"
    echo "================================"
    
    # Kill all SSH processes using our control socket
    pkill -f "ssh.*$CONTROL_PATH" 2>/dev/null
    
    # Stop control master
    stop_control_master
    
    # Clean up control socket if it exists
    rm -f "${CONTROL_PATH//\%*/}"* 2>/dev/null
    
    echo "================================"
    echo -e "${GREEN}All tunnels stopped!${NC}\n"
    ;;
    
  status)
    echo -e "\n${YELLOW}SSH Tunnel Status${NC}"
    echo "================================"
    
    # Check control master
    if check_control_master; then
        echo -e "${GREEN}✓ ControlMaster: Active${NC}"
        ssh -O check -S "$CONTROL_PATH" "$JUMP_SERVER" 2>&1 | head -n 1
    else
        echo -e "${RED}✗ ControlMaster: Not active${NC}"
    fi
    
    echo ""
    
    # Check individual ports
    for port_name in "Netshot API:$LOCAL_NETSHOT_PORT" "MySQL:$LOCAL_DB_PORT" "DHCP:$LOCAL_DHCP_PORT"; do
        name="${port_name%%:*}"
        port="${port_name##*:}"
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${GREEN}✓ $name: localhost:$port${NC}"
        else
            echo -e "${RED}✗ $name: Not listening${NC}"
        fi
    done
    
    echo "================================"
    echo ""
    ;;
    
  restart)
    $0 stop
    sleep 2
    $0 start
    ;;
    
  test)
    echo -e "\n${YELLOW}Testing Connections...${NC}"
    echo "================================"
    
    echo -n "Netshot API... "
    if curl -k -s --connect-timeout 5 "https://localhost:${LOCAL_NETSHOT_PORT}/" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
    fi
    
    echo -n "MySQL... "
    if nc -z localhost "$LOCAL_DB_PORT" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
    fi
    
    echo -n "DHCP MySQL... "
    if nc -z localhost "$LOCAL_DHCP_PORT" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
    fi
    
    echo -n "Mock Upload Server (localhost:2305)... "
    if curl -s --connect-timeout 2 "http://localhost:2305/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${YELLOW}⚠ Not running (start with: python mock_upload_server.py)${NC}"
    fi
    
    echo "================================"
    echo ""
    ;;
    
  *)
    echo -e "${RED}Error: Unknown command '$1'${NC}\n"
    echo "Usage: $0 {start|stop|restart|status|test}"
    echo ""
    echo "Commands:"
    echo "  start    - Start all SSH tunnels using ControlMaster"
    echo "  stop     - Stop all SSH tunnels and ControlMaster"
    echo "  restart  - Restart all tunnels"
    echo "  status   - Show tunnel status"
    echo "  test     - Test connections through tunnels"
    exit 1
    ;;
esac
