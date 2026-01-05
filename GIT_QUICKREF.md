# Git Workflow Quick Reference

## 🚀 Quick Start

### First Time Setup (Do this once)
```bash
# Clean up and commit current changes
./initial_cleanup.sh

# Configure git if not done
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

## 📝 Daily Development Workflow

### Making Changes and Committing

```bash
# Option 1: Quick commit with custom message
./git_commit.sh "Add new feature X"

# Option 2: Quick commit with auto-generated message
./git_commit.sh

# Option 3: Commit and push in one step
./git_commit.sh "Fix bug Y" --push
```

### Before Deployment

```bash
# Always commit before deploying
./pre_deploy_commit.sh

# Then deploy
./docker-deploy.sh
```

## 🛠️ Common Commands

### Check Status
```bash
git status
git status --short  # Compact view
```

### View History
```bash
git log              # Full log
git log --oneline    # Compact log
git log -5           # Last 5 commits
```

### Branch Management
```bash
# See all branches
git branch

# Create new branch
git checkout -b feature/new-feature

# Switch branches
git checkout main
```

### Undo Changes
```bash
# Discard changes in file
git checkout -- filename.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1
```

## 🏷️ Deployment Tags

Your deployment script automatically creates tags like:
- `deploy-20260105-143000`

View tags:
```bash
git tag
git show deploy-20260105-143000
```

## 🔄 Remote Repository

### First Time Push
```bash
# Add remote
git remote add origin https://github.com/username/repo.git

# Push main branch
git push -u origin main
```

### Regular Push
```bash
# Push current branch
git push

# Or use the commit script
./git_commit.sh "message" --push
```

## 🆘 Emergency Recovery

### Restore Deleted File
```bash
git checkout HEAD -- filename.py
```

### Rollback to Previous Deployment
```bash
# Find the tag
git tag

# Checkout the tag
git checkout deploy-20260105-120000

# Or reset to it
git reset --hard deploy-20260105-120000
```

## 📊 Useful Aliases (Optional)

Add to `~/.gitconfig`:
```ini
[alias]
    st = status --short
    ci = commit
    co = checkout
    br = branch
    lg = log --oneline --graph --all
    last = log -1 HEAD
```

Then use:
```bash
git st    # instead of git status
git lg    # pretty log graph
```

## 📁 Files Organization

**Scripts:**
- `git_commit.sh` - Main commit script
- `pre_deploy_commit.sh` - Pre-deployment commit
- `docker-deploy.sh` - Deployment with git integration
- `initial_cleanup.sh` - One-time cleanup

**Documentation:**
- `GIT_WORKFLOW.md` - Full documentation
- `GIT_QUICKREF.md` - This file

**Git Files:**
- `.gitignore` - Files to exclude from git
- `.git/` - Git repository data (auto-generated)

## ✅ Best Practices Checklist

- [ ] Commit after each feature or fix
- [ ] Write descriptive commit messages
- [ ] Commit before taking breaks
- [ ] Always commit before deployment
- [ ] Review changes before committing (`git status`, `git diff`)
- [ ] Keep commits focused (one feature/fix per commit)
- [ ] Push regularly to remote backup

## 🎯 Commit Message Examples

**Good:**
```
Add email notification for XML generation
Fix DHCP cache validation error
Update user management with role-based access
Refactor subnet validation logic
```

**Bad:**
```
Update
Fix
Changes
Test
```

## 🔍 Troubleshooting

**Problem:** "fatal: not a git repository"
```bash
git init
```

**Problem:** "Your branch is ahead of 'origin/main'"
```bash
git push
```

**Problem:** "Changes not staged for commit"
```bash
./git_commit.sh
```

**Problem:** "rejected - non-fast-forward"
```bash
git pull --rebase
git push
```

## 📞 Need Help?

1. Read `GIT_WORKFLOW.md` for detailed info
2. Check git documentation: https://git-scm.com/doc
3. Use `git help <command>` for command help

---
**Last Updated:** 2026-01-05
**Version:** 1.0
