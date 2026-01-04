#!/bin/bash
# Cache Refresh Script
# Refreshes cache WITHOUT clearing it first (zero downtime)

cd "$(dirname "$0")"

echo "Starting cache refresh (seamless update, no downtime)..."
echo "Started at: $(date)"

# Run cache_warmer - it will update cache entries seamlessly
nohup ./venv/bin/python cache_warmer.py > logs/cache_refresh_$(date +%Y%m%d_%H%M%S).log 2>&1 &
PID=$!

echo "Cache warmer started (PID: $PID)"
echo "Monitor progress: tail -f logs/cache_refresh_*.log"
echo ""
echo "Old cache data remains available during refresh - no downtime!"
echo "Once complete, new data will seamlessly replace old cache entries."
