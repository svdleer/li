#!/bin/bash
# Deploy EVE LI Web App to Remote Server
# ========================================
# Deploys Docker container to appdb-sh.oss.local via script3a.oss.local
#
# Usage: ./deploy-remote.sh [build|deploy|restart|stop|logs|status]

# ============================================================================
# Configuration
# ============================================================================
JUMP_SERVER="svdleer@script3a.oss.local"
TARGET_SERVER="appdb-sh.oss.local"
SSH_KEY="${HOME}/.ssh/id_rsa"
REMOTE_DEPLOY_DIR="/opt/eve-li-web"
REMOTE_USER="root"  # Adjust if needed

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# Functions
# ============================================================================

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo_success() {
    echo -e "${BLUE}[SUCCESS]${NC} $1"
}

# SSH via jump server
ssh_remote() {
    ssh -J "$JUMP_SERVER" -i "$SSH_KEY" "${REMOTE_USER}@${TARGET_SERVER}" "$@"
}

# SCP via jump server
scp_remote() {
    scp -o "ProxyJump $JUMP_SERVER" -i "$SSH_KEY" "$@"
}

case "$1" in
  build)
    echo_info "Building Docker image locally..."
    docker build -t eve-li-web:latest . || {
        echo_error "Docker build failed!"
        exit 1
    }
    
    echo_info "Saving Docker image to tar..."
    docker save eve-li-web:latest | gzip > /tmp/eve-li-web.tar.gz || {
        echo_error "Failed to save Docker image!"
        exit 1
    }
    
    echo_success "Docker image built and saved!"
    echo_info "Image size: $(ls -lh /tmp/eve-li-web.tar.gz | awk '{print $5}')"
    echo ""
    echo_info "Next step: ./deploy-remote.sh deploy"
    ;;
    
  deploy)
    if [ ! -f /tmp/eve-li-web.tar.gz ]; then
        echo_error "Docker image not found! Run './deploy-remote.sh build' first"
        exit 1
    fi
    
    echo_info "Deploying to ${TARGET_SERVER}..."
    echo "================================"
    
    # Create remote directory
    echo_info "Creating remote directory..."
    ssh_remote "mkdir -p ${REMOTE_DEPLOY_DIR}" || {
        echo_error "Failed to create remote directory!"
        exit 1
    }
    
    # Copy Docker image
    echo_info "Copying Docker image to remote server..."
    scp_remote /tmp/eve-li-web.tar.gz "${REMOTE_USER}@${TARGET_SERVER}:${REMOTE_DEPLOY_DIR}/" || {
        echo_error "Failed to copy Docker image!"
        exit 1
    }
    
    # Copy docker-compose.yml
    echo_info "Copying docker-compose.yml..."
    scp_remote docker-compose.yml "${REMOTE_USER}@${TARGET_SERVER}:${REMOTE_DEPLOY_DIR}/" || {
        echo_error "Failed to copy docker-compose.yml!"
        exit 1
    }
    
    # Copy .env file
    echo_info "Copying .env file..."
    scp_remote .env "${REMOTE_USER}@${TARGET_SERVER}:${REMOTE_DEPLOY_DIR}/" || {
        echo_error "Failed to copy .env file!"
        exit 1
    }
    
    # Load Docker image on remote
    echo_info "Loading Docker image on remote server..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && gunzip -c eve-li-web.tar.gz | docker load" || {
        echo_error "Failed to load Docker image!"
        exit 1
    }
    
    # Update .env for local database access
    echo_info "Updating .env for local database access..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && sed -i 's/DB_HOST=.*/DB_HOST=localhost/' .env"
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && sed -i 's/DB_PORT=.*/DB_PORT=3306/' .env"
    
    # Start containers
    echo_info "Starting containers..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose down && docker-compose up -d" || {
        echo_error "Failed to start containers!"
        exit 1
    }
    
    echo "================================"
    echo_success "Deployment complete!"
    echo ""
    echo_info "Check status: ./deploy-remote.sh status"
    echo_info "View logs: ./deploy-remote.sh logs"
    ;;
    
  restart)
    echo_info "Restarting containers on ${TARGET_SERVER}..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose restart" || {
        echo_error "Failed to restart containers!"
        exit 1
    }
    echo_success "Containers restarted!"
    ;;
    
  stop)
    echo_info "Stopping containers on ${TARGET_SERVER}..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose down" || {
        echo_error "Failed to stop containers!"
        exit 1
    }
    echo_success "Containers stopped!"
    ;;
    
  logs)
    echo_info "Fetching logs from ${TARGET_SERVER}..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose logs --tail=50 -f"
    ;;
    
  status)
    echo_info "Checking status on ${TARGET_SERVER}..."
    echo "================================"
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose ps"
    echo "================================"
    ;;
    
  shell)
    echo_info "Opening shell on ${TARGET_SERVER}..."
    ssh_remote
    ;;
    
  *)
    echo -e "${RED}Error: Unknown command '$1'${NC}\n"
    echo "Usage: $0 {build|deploy|restart|stop|logs|status|shell}"
    echo ""
    echo "Commands:"
    echo "  build    - Build Docker image locally and prepare for deployment"
    echo "  deploy   - Deploy to remote server (appdb-sh.oss.local)"
    echo "  restart  - Restart containers on remote server"
    echo "  stop     - Stop containers on remote server"
    echo "  logs     - View container logs (streaming)"
    echo "  status   - Check container status"
    echo "  shell    - Open SSH shell on remote server"
    echo ""
    echo "Typical workflow:"
    echo "  1. ./deploy-remote.sh build"
    echo "  2. ./deploy-remote.sh deploy"
    echo "  3. ./deploy-remote.sh status"
    exit 1
    ;;
esac
