# Cache Refresh Crontab Configuration
# ====================================
#
# This file shows how to configure cron to automatically refresh
# the Netshot API cache daily before XML generation.
#
# Installation:
#   1. Copy this file or add entries to your crontab
#   2. Edit paths to match your installation
#   3. Run: crontab -e
#   4. Paste the entries below
#
# For Docker deployments, use the cache-refresh service in docker-compose.yml instead.

# ============================================================================
# Daily Cache Refresh and XML Generation
# ============================================================================

# Step 1: Refresh cache at 1:00 AM daily
# This pre-populates the cache with Netshot data
0 1 * * * cd /path/to/eve-li && /path/to/venv/bin/python refresh_cache.py >> logs/cache_refresh.log 2>&1

# Step 2: Generate and upload XML at 2:00 AM daily  
# This uses the cached data for fast processing
0 2 * * * cd /path/to/eve-li && /path/to/venv/bin/python eve_li_xml_generator_v2.py >> logs/xml_generation.log 2>&1

# Optional: Cleanup old cache entries at 3:00 AM weekly
0 3 * * 0 cd /path/to/eve-li && /path/to/venv/bin/python -c "from cache_manager import get_cache_manager; get_cache_manager().cleanup_expired()" >> logs/cache_cleanup.log 2>&1

# Optional: Cleanup old logs at 4:00 AM weekly
0 4 * * 0 find /path/to/eve-li/logs -name "*.log" -mtime +30 -delete

# ============================================================================
# Alternative: Manual cache refresh before XML generation
# ============================================================================
# If you want to ensure cache is always fresh, refresh and generate in one cron job:
# 0 2 * * * cd /path/to/eve-li && /path/to/venv/bin/python refresh_cache.py --force && /path/to/venv/bin/python eve_li_xml_generator_v2.py >> logs/daily_run.log 2>&1

# ============================================================================
# Docker-based scheduling (systemd timer example)
# ============================================================================
# For Docker deployments, you can use systemd timers instead of cron:
#
# /etc/systemd/system/eve-li-cache-refresh.service
# [Unit]
# Description=EVE LI Cache Refresh
#
# [Service]
# Type=oneshot
# WorkingDirectory=/path/to/eve-li
# ExecStart=/usr/bin/docker-compose exec -T eve-li-web python refresh_cache.py
#
# /etc/systemd/system/eve-li-cache-refresh.timer
# [Unit]
# Description=EVE LI Cache Refresh Timer
#
# [Timer]
# OnCalendar=daily
# OnCalendar=01:00:00
# Persistent=true
#
# [Install]
# WantedBy=timers.target
#
# Enable with: systemctl enable --now eve-li-cache-refresh.timer

# ============================================================================
# Environment Variables
# ============================================================================
# Make sure these environment variables are set in your environment:
# - NETSHOT_API_URL
# - NETSHOT_USERNAME
# - NETSHOT_PASSWORD
# - CACHE_DIR (default: .cache)
# - CACHE_TTL (default: 86400 seconds = 24 hours)
# - CACHE_ENABLED (default: true)
#
# You can set them in:
# - .env file
# - /etc/environment
# - User's .bashrc or .profile
# - Cron environment (add to top of crontab)

# ============================================================================
# Monitoring and Alerting
# ============================================================================
# Add monitoring to ensure cache refresh succeeds:
# 5 1 * * * /path/to/check_cache_refresh_success.sh

# ============================================================================
# Testing
# ============================================================================
# Test your cron setup manually:
# cd /path/to/eve-li && source venv/bin/activate && python refresh_cache.py --verbose
