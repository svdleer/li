#!/bin/bash
"""
Initial Cleanup and Commit Script
=================================

This script helps clean up and commit all current uncommitted changes.
Run this once to get your repository in a clean state.
"""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
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

echo_info "Initial Repository Cleanup"
echo_info "=========================="
echo

# Step 1: Clean up .flask_session
echo_info "Step 1: Cleaning up .flask_session directory..."
if [ -d ".flask_session" ]; then
    rm -rf .flask_session/
    echo_success ".flask_session directory removed"
else
    echo_info ".flask_session directory not found (already clean)"
fi

echo

# Step 2: Check git status
echo_info "Step 2: Current git status:"
git status --short
echo

# Step 3: Stage all changes
echo_info "Step 3: Staging changes..."
git add -A
echo_success "All changes staged"

echo

# Step 4: Show what will be committed
echo_info "Step 4: Files to be committed:"
git diff --cached --stat
echo

# Step 5: Commit
echo_info "Step 5: Creating commit..."
read -p "Enter commit message (or press Enter for default): " COMMIT_MSG

if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Initial commit: Add git workflow integration and clean up repository"
fi

if git commit -m "$COMMIT_MSG"; then
    echo_success "Changes committed successfully!"
    echo
    git log -1 --stat
else
    echo_warn "Commit failed or nothing to commit"
fi

echo

# Step 6: Optional push
echo_info "Step 6: Push to remote?"
echo_warn "Note: Only do this if you have a remote repository configured"
read -p "Push to remote? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    if git remote | grep -q "origin"; then
        echo_info "Pushing to remote..."
        if git push; then
            echo_success "Pushed to remote successfully!"
        else
            echo_warn "Push failed. You may need to set upstream:"
            echo_info "Run: git push --set-upstream origin $(git branch --show-current)"
        fi
    else
        echo_warn "No remote 'origin' found. To add one:"
        echo_info "git remote add origin <your-repo-url>"
    fi
fi

echo
echo_success "Repository cleanup complete!"
echo
echo_info "Next steps:"
echo_info "1. Review the changes: git log"
echo_info "2. Use ./git_commit.sh for future commits"
echo_info "3. Read GIT_WORKFLOW.md for workflow documentation"
echo
