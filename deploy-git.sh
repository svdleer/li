#!/bin/bash
# Deploy EVE LI Web App via Git Pull on Remote Server
# ====================================================
# Pulls latest code from git and rebuilds container on appdb-sh.oss.local
#
# Usage: ./deploy-git.sh [deploy|restart|stop|logs|status|shell]

# ============================================================================
# Configuration
# ============================================================================
JUMP_SERVER="svdleer@script3a.oss.local"
TARGET_SERVER="appdb-sh.oss.local"
SSH_KEY="${HOME}/.ssh/id_rsa"
REMOTE_DEPLOY_DIR="/opt/eve-li-web"
REMOTE_USER="root"
GIT_REPO="https://github.com/svdleer/li.git"  # Your git repository
GIT_BRANCH="main"

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

case "$1" in
  init)
    echo_info "Initializing deployment on ${TARGET_SERVER}..."
    echo "================================"
    
    # Create remote directory
    echo_info "Creating remote directory..."
    ssh_remote "mkdir -p ${REMOTE_DEPLOY_DIR}"
    
    # Clone repository
    echo_info "Cloning git repository..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR}/.. && rm -rf $(basename ${REMOTE_DEPLOY_DIR}) && git clone ${GIT_REPO} $(basename ${REMOTE_DEPLOY_DIR})" || {
        echo_error "Failed to clone repository!"
        exit 1
    }
    
    # Checkout branch
    echo_info "Checking out branch: ${GIT_BRANCH}..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && git checkout ${GIT_BRANCH}"
    
    echo "================================"
    echo_success "Repository initialized!"
    echo_info "Next: ./deploy-git.sh deploy"
    ;;
    
  deploy)
    echo_info "Deploying latest code to ${TARGET_SERVER}..."
    echo "================================"
    
    # Check if directory exists
    ssh_remote "test -d ${REMOTE_DEPLOY_DIR}/.git" || {
        echo_error "Repository not initialized! Run './deploy-git.sh init' first"
        exit 1
    }
    
    # Pull latest code
    echo_info "Pulling latest code from git..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && git fetch origin && git reset --hard origin/${GIT_BRANCH}" || {
        echo_error "Failed to pull latest code!"
        exit 1
    }
    
    # Show what changed
    echo_info "Latest commit:"
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && git log -1 --oneline"
    
    # Stop existing containers
    echo_info "Stopping existing containers..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose down" 2>/dev/null
    
    # Build new image
    echo_info "Building Docker image..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose build" || {
        echo_error "Docker build failed!"
        exit 1
    }
    
    # Start containers
    echo_info "Starting containers..."
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose up -d" || {
        echo_error "Failed to start containers!"
        exit 1
    }
    
    # Wait a moment for startup
    echo_info "Waiting for container to start..."
    sleep 5
    
    echo "================================"
    echo_success "Deployment complete!"
    echo ""
    echo_info "Container status:"
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose ps"
    echo ""
    echo_info "Access web app: http://localhost:8080 (via tunnel)"
    echo_info "View logs: ./deploy-git.sh logs"
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
    echo "================================"
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose logs --tail=50 -f"
    ;;
    
  status)
    echo_info "Checking status on ${TARGET_SERVER}..."
    echo "================================"
    echo_info "Container status:"
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && docker-compose ps"
    echo ""
    echo_info "Current git commit:"
    ssh_remote "cd ${REMOTE_DEPLOY_DIR} && git log -1 --oneline"
    echo "================================"
    ;;
    
  shell)
    echo_info "Opening shell on ${TARGET_SERVER}..."
    ssh_remote
    ;;
    
  update)
    echo_info "Committing and pushing local changes..."
    
    # Check if there are changes
    if [ -z "$(git status --porcelain)" ]; then
        echo_warn "No local changes to commit"
    else
        # Commit changes
        git add -A
        read -p "Enter commit message: " COMMIT_MSG
        if [ -z "$COMMIT_MSG" ]; then
            COMMIT_MSG="Update: $(date '+%Y-%m-%d %H:%M:%S')"
        fi
        git commit -m "$COMMIT_MSG"
    fi
    
    # Push to remote
    echo_info "Pushing to git..."
    git push || {
        echo_error "Failed to push to git!"
        exit 1
    }
    
    echo_success "Changes pushed to git!"
    echo_info "Now run: ./deploy-git.sh deploy"
    ;;
    
  *)
    echo -e "${RED}Error: Unknown command '$1'${NC}\n"
    echo "Usage: $0 {init|deploy|update|restart|stop|logs|status|shell}"
    echo ""
    echo "Commands:"
    echo "  init     - Initialize git repository on remote server (first time only)"
    echo "  deploy   - Pull latest code from git and rebuild/restart containers"
    echo "  update   - Commit and push local changes to git"
    echo "  restart  - Restart containers on remote server"
    echo "  stop     - Stop containers on remote server"
    echo "  logs     - View container logs (streaming)"
    echo "  status   - Check container status and git commit"
    echo "  shell    - Open SSH shell on remote server"
    echo ""
    echo "Typical workflow:"
    echo "  # First time setup:"
    echo "  1. ./deploy-git.sh init"
    echo ""
    echo "  # Regular deployment:"
    echo "  1. Make your code changes"
    echo "  2. ./deploy-git.sh update    # Commit and push to git"
    echo "  3. ./deploy-git.sh deploy    # Pull and rebuild on server"
    echo ""
    echo "  # Quick deploy (if already pushed):"
    echo "  ./deploy-git.sh deploy"
    exit 1
    ;;
esac
