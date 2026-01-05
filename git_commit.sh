#!/bin/bash
"""
Git Commit Helper Script
========================

This script helps automate git commits during development workflow.
Usage: ./git_commit.sh [commit_message] [--push]
"""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

echo_success() {
    echo -e "${BLUE}[SUCCESS]${NC} $1"
}

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo_error "Not a git repository. Run 'git init' first."
    exit 1
fi

# Get commit message from argument or generate default
COMMIT_MSG="${1:-Auto-commit: Development changes $(date '+%Y-%m-%d %H:%M:%S')}"
SHOULD_PUSH=false

# Check if --push flag is provided
if [[ "$2" == "--push" ]] || [[ "$1" == "--push" ]]; then
    SHOULD_PUSH=true
    if [[ "$1" == "--push" ]]; then
        COMMIT_MSG="Auto-commit: Development changes $(date '+%Y-%m-%d %H:%M:%S')"
    fi
fi

echo_info "Git Commit Helper"
echo_info "================="
echo

# Show current status
echo_info "Current git status:"
git status --short
echo

# Check if there are any changes to commit
if [ -z "$(git status --porcelain)" ]; then
    echo_warn "No changes to commit."
    exit 0
fi

# Ask for confirmation
echo_info "Commit message: ${COMMIT_MSG}"
if [ "$SHOULD_PUSH" = true ]; then
    echo_info "Will push to remote after commit"
fi
echo
read -p "Proceed with commit? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo_warn "Commit cancelled."
    exit 0
fi

# Add all changes (excluding .flask_session if exists)
echo_info "Adding changes to staging area..."

# Check if .gitignore exists, if not create it
if [ ! -f ".gitignore" ]; then
    echo_warn ".gitignore not found, creating one..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Flask
instance/
.flask_session/
.webassets-cache

# Logs
*.log
logs/*.log

# Database
*.db
*.sqlite

# Environment variables
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project specific
output/*.xml
output/*.xml.gz
EOF
fi

# Clean up .flask_session files first
if [ -d ".flask_session" ]; then
    echo_info "Cleaning up .flask_session directory..."
    rm -rf .flask_session/
fi

# Add all changes
git add -A

# Show what will be committed
echo
echo_info "Changes to be committed:"
git status --short
echo

# Commit
echo_info "Committing changes..."
if git commit -m "$COMMIT_MSG"; then
    echo_success "Changes committed successfully!"
    
    # Show the commit
    git log -1 --stat
    
    # Push if requested
    if [ "$SHOULD_PUSH" = true ]; then
        echo
        echo_info "Pushing to remote..."
        
        # Check if remote exists
        if git remote | grep -q "origin"; then
            if git push; then
                echo_success "Changes pushed successfully!"
            else
                echo_error "Failed to push changes. You may need to set up the remote branch."
                echo_info "Try: git push --set-upstream origin $(git branch --show-current)"
                exit 1
            fi
        else
            echo_warn "No remote 'origin' configured. Skipping push."
            echo_info "To add a remote: git remote add origin <repository-url>"
        fi
    fi
else
    echo_error "Commit failed!"
    exit 1
fi

echo
echo_success "Done!"
