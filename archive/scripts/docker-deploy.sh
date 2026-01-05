#!/bin/bash
"""
Docker Deployment Script with Git Integration
=============================================

This script handles Docker-based deployment with git commit integration.
It ensures all changes are committed before deployment.
"""

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

echo_info "Docker Deployment with Git Integration"
echo_info "======================================"
echo

# Step 1: Pre-deployment git commit
echo_info "Step 1: Committing pending changes..."
if [ -f "./pre_deploy_commit.sh" ]; then
    ./pre_deploy_commit.sh
    if [ $? -ne 0 ]; then
        echo_error "Pre-deployment commit failed!"
        exit 1
    fi
else
    echo_warn "pre_deploy_commit.sh not found, checking git status..."
    if [ -n "$(git status --porcelain)" ]; then
        echo_error "Uncommitted changes found! Please commit them before deployment."
        git status --short
        exit 1
    fi
fi

echo

# Step 2: Create deployment tag
echo_info "Step 2: Creating deployment tag..."
TIMESTAMP=$(date '+%Y%m%d-%H%M%S')
DEPLOY_TAG="deploy-${TIMESTAMP}"
CURRENT_BRANCH=$(git branch --show-current)

echo_info "Current branch: $CURRENT_BRANCH"
echo_info "Creating tag: $DEPLOY_TAG"

git tag -a "$DEPLOY_TAG" -m "Deployment at $TIMESTAMP"
echo_success "Tag created: $DEPLOY_TAG"
echo

# Step 3: Build Docker image
echo_info "Step 3: Building Docker image..."
DOCKER_IMAGE="eve-li-xml-generator"
DOCKER_TAG="${DEPLOY_TAG}"

if docker-compose build; then
    echo_success "Docker image built successfully!"
else
    echo_error "Docker build failed!"
    exit 1
fi

echo

# Step 4: Stop existing containers
echo_info "Step 4: Stopping existing containers..."
if docker-compose down; then
    echo_success "Existing containers stopped."
else
    echo_warn "No existing containers to stop."
fi

echo

# Step 5: Start new containers
echo_info "Step 5: Starting new containers..."
if docker-compose up -d; then
    echo_success "New containers started successfully!"
else
    echo_error "Failed to start containers!"
    echo_info "Rolling back..."
    docker-compose down
    exit 1
fi

echo

# Step 6: Verify deployment
echo_info "Step 6: Verifying deployment..."
sleep 5  # Wait for containers to fully start

if docker-compose ps | grep -q "Up"; then
    echo_success "Deployment verified - containers are running!"
    docker-compose ps
else
    echo_error "Deployment verification failed!"
    echo_info "Container logs:"
    docker-compose logs --tail=50
    exit 1
fi

echo

# Step 7: Push tags to remote (optional)
echo_info "Step 7: Push deployment tag to remote? (y/n)"
read -p "Push tag '$DEPLOY_TAG' to remote? " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if git remote | grep -q "origin"; then
        echo_info "Pushing tag to remote..."
        if git push origin "$DEPLOY_TAG"; then
            echo_success "Tag pushed to remote!"
        else
            echo_warn "Failed to push tag to remote."
        fi
    else
        echo_warn "No remote 'origin' configured."
    fi
fi

echo

# Summary
echo_success "=================================="
echo_success "Deployment completed successfully!"
echo_success "=================================="
echo
echo_info "Deployment details:"
echo_info "  Branch: $CURRENT_BRANCH"
echo_info "  Tag: $DEPLOY_TAG"
echo_info "  Timestamp: $TIMESTAMP"
echo
echo_info "To view logs: docker-compose logs -f"
echo_info "To stop: docker-compose down"
echo

# Save deployment info
cat > deployment_info.txt << EOF
Deployment Information
=====================
Date: $(date)
Branch: $CURRENT_BRANCH
Tag: $DEPLOY_TAG
Commit: $(git rev-parse HEAD)
User: $(whoami)
Host: $(hostname)

Deployed Containers:
$(docker-compose ps)
EOF

echo_info "Deployment information saved to deployment_info.txt"
echo
echo_success "Done!"
