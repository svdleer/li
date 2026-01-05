#!/bin/bash
"""
Pre-Deployment Commit Script
============================

This script commits all changes before deployment to ensure version control.
It should be run before any deployment or major operation.
"""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
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

echo_success() {
    echo -e "${BLUE}[SUCCESS]${NC} $1"
}

echo_info "Pre-Deployment Git Commit"
echo_info "========================"
echo

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo_info "Current branch: $CURRENT_BRANCH"

# Check if there are uncommitted changes
if [ -z "$(git status --porcelain)" ]; then
    echo_success "No uncommitted changes. Working directory is clean."
    exit 0
fi

# Show what will be committed
echo
echo_info "Uncommitted changes found:"
git status --short
echo

# Create commit message with timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
COMMIT_MSG="Pre-deployment commit - $TIMESTAMP"

# Execute git commit helper
if [ -f "./git_commit.sh" ]; then
    ./git_commit.sh "$COMMIT_MSG"
else
    echo_warn "git_commit.sh not found, performing manual commit..."
    git add -A
    git commit -m "$COMMIT_MSG"
    echo_success "Changes committed successfully!"
fi

echo
echo_success "Repository is ready for deployment!"
