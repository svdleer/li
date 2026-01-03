# Netshot API Caching Implementation Guide

## Overview

The EVE LI XML Generator now includes a comprehensive caching system optimized for daily XML generation. This dramatically improves performance by pre-fetching and caching Netshot API data.

## Performance Impact

**Before Caching:**
- XML generation: 5-10 minutes
- 200+ API calls to Netshot per run
- Real-time dependency on Netshot availability

**After Caching:**
- Cache refresh: 5-10 minutes (scheduled at 1 AM)
- XML generation: 30-60 seconds (uses cached data)
- Resilient to temporary Netshot issues

## Architecture

```
┌─────────────────────────────────────────────┐
│     Daily Schedule (Docker/Cron)            │
│                                              │
│  1:00 AM → refresh_cache.py                 │
│            └─ Fetch from Netshot API        │
│            └─ Store in cache volume         │
│                                              │
│  2:00 AM → eve_li_xml_generator_v2.py       │
│            └─ Read from cache (fast!)       │
│            └─ Generate XML                   │
│            └─ Upload to EVE LI              │
└─────────────────────────────────────────────┘
```

## Components

### 1. Cache Manager (`cache_manager.py`)
- File-based JSON caching
- TTL (Time To Live) expiration
- Thread-safe operations
- Docker volume compatible
- Statistics and monitoring

### 2. Enhanced Netshot API (`netshot_api.py`)
- Automatic caching of all API calls
- Force refresh capability
- Cache bypass options
- Per-method cache keys

### 3. Cache Refresh Script (`refresh_cache.py`)
- Standalone script for scheduled execution
- Pre-populates all cache data
- Progress logging
- Error handling and statistics

## Configuration

### Environment Variables

```bash
# Enable/disable caching
CACHE_ENABLED=true

# Cache directory (Docker: /app/cache, Local: .cache)
CACHE_DIR=/app/cache

# Cache TTL in seconds (24 hours = 86400)
CACHE_TTL=86400
```

### Update your `.env` file:

```bash
# Add these lines to your .env
CACHE_ENABLED=true
CACHE_DIR=.cache
CACHE_TTL=86400
```

## Docker Deployment

### 1. Update docker-compose.yml (Already Done)

The `docker-compose.yml` now includes:
- `cache-data` volume for persistent caching
- `cache-refresh` service that runs daily at 1 AM
- Cache environment variables

### 2. Start Services

```bash
# Start with cache refresh service (production)
docker-compose --profile production up -d

# Or start without cache refresh (development)
docker-compose up -d
```

### 3. Manual Cache Refresh

```bash
# Refresh cache manually in Docker
docker-compose exec eve-li-web python refresh_cache.py --verbose

# Force refresh (bypass existing cache)
docker-compose exec eve-li-web python refresh_cache.py --force

# Check cache statistics
docker-compose exec eve-li-web python -c "from cache_manager import get_cache_manager; import json; print(json.dumps(get_cache_manager().get_stats(), indent=2))"
```

## Local/Non-Docker Deployment

### 1. Setup Crontab

Edit your crontab:
```bash
crontab -e
```

Add these entries:
```bash
# Refresh cache at 1:00 AM daily
0 1 * * * cd /path/to/eve-li && /path/to/venv/bin/python refresh_cache.py >> logs/cache_refresh.log 2>&1

# Generate XML at 2:00 AM daily
0 2 * * * cd /path/to/eve-li && /path/to/venv/bin/python eve_li_xml_generator_v2.py >> logs/xml_generation.log 2>&1
```

See [CACHE_CRONTAB.md](CACHE_CRONTAB.md) for more scheduling options.

### 2. Manual Execution

```bash
# Activate virtual environment
source venv/bin/activate

# Refresh cache
python refresh_cache.py --verbose

# Generate XML (uses cached data)
python eve_li_xml_generator_v2.py
```

## Cache Management

### View Cache Statistics

```python
from cache_manager import get_cache_manager

cache = get_cache_manager()
stats = cache.get_stats()

print(f"Total entries: {stats['total_entries']}")
print(f"Valid entries: {stats['valid_entries']}")
print(f"Total size: {stats['total_size_mb']} MB")
```

### Clear Cache

```python
from cache_manager import get_cache_manager

cache = get_cache_manager()
cache.clear()
print("Cache cleared")
```

### Force Refresh Specific Data

```python
from netshot_api import get_netshot_client

netshot = get_netshot_client()

# Force refresh devices
devices = netshot.get_production_devices(force_refresh=True)

# Force refresh specific device details
device_id = 123
interfaces = netshot.get_device_interfaces(device_id, force_refresh=True)
loopback = netshot.get_loopback_interface(device_id, force_refresh=True)
subnets = netshot.get_device_subnets(device_id, force_refresh=True)
```

## Monitoring

### Check Logs

```bash
# Docker
docker-compose logs cache-refresh
docker-compose logs eve-li-web

# Local
tail -f logs/cache_refresh.log
tail -f logs/xml_generation.log
```

### Cache Refresh Status

The refresh script logs:
- Number of devices cached
- Number of interfaces, loopbacks, and subnets cached
- Processing time
- Any errors encountered

Example output:
```
[2026-01-02 01:00:00] STEP 1: Refreshing device list cache
[2026-01-02 01:00:15] ✓ Cached 150 production devices
[2026-01-02 01:00:15] STEP 2: Refreshing device details cache
[2026-01-02 01:05:30] ✓ Device details cache refresh completed
[2026-01-02 01:05:30]   - Devices processed: 150
[2026-01-02 01:05:30]   - Interfaces cached: 1800
[2026-01-02 01:05:30]   - Loopbacks cached: 148
[2026-01-02 01:05:30]   - Subnets cached: 3200
[2026-01-02 01:05:30] Duration: 330.2 seconds (5.5 minutes)
```

## Troubleshooting

### Cache Not Working

1. Check if caching is enabled:
```bash
echo $CACHE_ENABLED
```

2. Verify cache directory exists and is writable:
```bash
ls -la .cache/
```

3. Check cache statistics:
```python
from cache_manager import get_cache_manager
print(get_cache_manager().get_stats())
```

### Stale Data

If you suspect cached data is stale:

```bash
# Force refresh cache
python refresh_cache.py --force

# Or manually clear cache
python -c "from cache_manager import get_cache_manager; get_cache_manager().clear()"
```

### Performance Issues

- Adjust `CACHE_TTL` if data changes more frequently
- Check Netshot API performance during cache refresh
- Monitor cache size with `get_stats()`

## Best Practices

1. **Daily Schedule**: Run cache refresh at 1 AM, XML generation at 2 AM
2. **Monitor Logs**: Check logs regularly for errors
3. **Cache TTL**: Keep at 24 hours for daily generation
4. **Backup Cache**: The cache volume should be backed up with your data
5. **Manual Refresh**: Use force refresh after major network changes

## Integration with Web UI

The web application (`web_app.py`) automatically uses cached data when available. You can add:

- Cache status indicator on dashboard
- Manual refresh button
- Cache statistics display
- Last refresh timestamp

Example dashboard addition:
```python
@app.route('/api/cache/stats')
def cache_stats():
    cache = get_cache_manager()
    stats = cache.get_stats()
    return jsonify(stats)
```

## Migration from Non-Cached Version

1. Update code (already done)
2. Update `.env` file with cache variables
3. Test cache refresh: `python refresh_cache.py --verbose`
4. Update crontab or Docker schedule
5. Monitor first few runs

No data migration needed - cache is built on first refresh.

## Support

For issues or questions:
1. Check logs in `logs/cache_refresh.log`
2. Review cache statistics
3. Test with `--verbose` flag
4. Verify Netshot API connectivity
