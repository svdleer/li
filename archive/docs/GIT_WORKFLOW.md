# Git Workflow Integration

This document describes the git workflow integration for the EVE LI XML Generator project.

## Overview

The project now includes automated git commit scripts to ensure all development changes are properly tracked in version control.

## Scripts

### 1. git_commit.sh
Main script for committing changes during development.

**Usage:**
```bash
# Interactive commit with custom message
./git_commit.sh "Your commit message"

# Auto-generated commit message
./git_commit.sh

# Commit and push to remote
./git_commit.sh "Your message" --push

# Quick commit and push
./git_commit.sh --push
```

**Features:**
- Interactive confirmation before commit
- Automatic .gitignore creation if missing
- Cleans up .flask_session directory automatically
- Shows what will be committed before proceeding
- Optional push to remote repository
- Color-coded output for better readability

### 2. pre_deploy_commit.sh
Commits all changes before deployment to ensure version control.

**Usage:**
```bash
./pre_deploy_commit.sh
```

**Features:**
- Automatically commits all changes with timestamp
- Should be run before any deployment
- Uses git_commit.sh internally
- Ensures working directory is clean before deployment

### 3. docker-deploy.sh (New)
Enhanced deployment script with git commit integration.

**Usage:**
```bash
./docker-deploy.sh
```

**Features:**
- Commits changes before deployment
- Builds and deploys Docker containers
- Provides rollback capability
- Logs all deployment actions

## Workflow Integration

### Development Workflow

1. **Make your changes** to the code
2. **Test your changes** locally
3. **Commit your changes**:
   ```bash
   ./git_commit.sh "Description of changes"
   ```
4. **Push to remote** (optional):
   ```bash
   ./git_commit.sh "Description of changes" --push
   ```

### Deployment Workflow

1. **Commit all pending changes**:
   ```bash
   ./pre_deploy_commit.sh
   ```

2. **Deploy to production**:
   ```bash
   ./docker-deploy.sh
   ```

### Quick Development Commits

For rapid development, use auto-generated commit messages:
```bash
./git_commit.sh
```

This will create a commit with timestamp: "Auto-commit: Development changes 2026-01-05 15:30:00"

## Best Practices

### Commit Messages

**Good commit messages:**
- "Add email notification feature for XML generation"
- "Fix: Resolve DHCP cache validation error"
- "Update: Enhance user management RBAC rules"
- "Refactor: Improve subnet validation logic"

**Avoid:**
- "Fix bug"
- "Update code"
- "Changes"

### Commit Frequency

- **Commit after each feature**: When you complete a new feature or fix
- **Commit before breaks**: Before taking a break or ending your work session
- **Commit before deployment**: Always commit before deploying to production
- **Commit after major refactors**: When restructuring code significantly

### Branch Management

```bash
# Create a new feature branch
git checkout -b feature/new-feature-name

# Work on your changes
# ... make changes ...

# Commit your changes
./git_commit.sh "Implement new feature"

# Push the branch
git push --set-upstream origin feature/new-feature-name

# Merge to main (after review)
git checkout main
git merge feature/new-feature-name
./git_commit.sh "Merge feature: new-feature-name" --push
```

## Configuration

### Setting up Remote Repository

If you haven't set up a remote repository yet:

```bash
# Initialize git if not already done
git init

# Add your remote repository
git remote add origin https://github.com/yourusername/your-repo.git

# Or for SSH
git remote add origin git@github.com:yourusername/your-repo.git

# Verify remote
git remote -v
```

### First Time Setup

```bash
# Configure git user
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Optional: Set default branch name
git config --global init.defaultBranch main
```

## .gitignore

The project includes a comprehensive .gitignore file that excludes:
- Python cache files (`__pycache__`, `*.pyc`)
- Virtual environment (`venv/`)
- Flask session files (`.flask_session/`)
- Log files (`logs/*.log`)
- Generated XML files (`output/*.xml`, `output/*.xml.gz`)
- Environment variables (`.env`)
- IDE files (`.vscode/`, `.idea/`)
- OS files (`.DS_Store`, `Thumbs.db`)

## Troubleshooting

### Problem: "No changes to commit"
**Solution**: You have no uncommitted changes. Everything is already committed.

### Problem: "Failed to push changes"
**Solution**: Set up the upstream branch:
```bash
git push --set-upstream origin $(git branch --show-current)
```

### Problem: "Not a git repository"
**Solution**: Initialize git:
```bash
git init
```

### Problem: Too many untracked files
**Solution**: Clean up and commit:
```bash
# Remove flask session files
rm -rf .flask_session/

# Stage and commit
./git_commit.sh "Clean up temporary files"
```

## Integration with CI/CD

These scripts can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
name: Deploy
on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Pre-deployment commit check
        run: |
          if [ -n "$(git status --porcelain)" ]; then
            echo "Error: Uncommitted changes found"
            exit 1
          fi
      - name: Deploy
        run: ./docker-deploy.sh
```

## Support

For issues or questions about the git workflow:
1. Check this README
2. Review the script comments
3. Check git documentation: https://git-scm.com/doc

## Version History

- **v1.0** (2026-01-05): Initial git workflow integration
  - Added git_commit.sh
  - Added pre_deploy_commit.sh
  - Enhanced .gitignore
  - Documentation created
