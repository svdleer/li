#!/usr/bin/env python3
"""
Fix Missing Loopbacks
=====================
Surgically updates devices with missing loopbacks without rebuilding entire cache.
"""

import json
import hashlib
from netshot_api import NetshotAPI
from cache_manager import CacheManager

def main():
    print("Fixing missing loopbacks...")
    
    api = NetshotAPI()
    cache = CacheManager('.cache')
    
    # Load the cached device list
    cache_key = 'cmts_devices_207'
    key_hash = hashlib.md5(cache_key.encode()).hexdigest()
    cache_file = cache._get_cache_file_path(cache_key)
    
    if not cache_file.exists():
        print("ERROR: Device list cache doesn't exist. Run cache_warmer first.")
        return
    
    # Read the cached device list
    with open(cache_file, 'r') as f:
        cache_data = json.load(f)
    
    # Extract actual device list (cache stores it under 'value' key)
    devices = cache_data.get('value') if isinstance(cache_data, dict) else cache_data
    
    if not isinstance(devices, list):
        print(f"ERROR: Unexpected cache format: {type(devices)}")
        print(f"Cache keys: {cache_data.keys() if isinstance(cache_data, dict) else 'N/A'}")
        return
    
    print(f"Loaded {len(devices)} devices from cache")
    
    # Find devices without loopbacks
    no_loopback = [d for d in devices if not d.get('loopback') and d.get('id')]
    print(f"Found {len(no_loopback)} devices without loopback")
    
    if not no_loopback:
        print("All devices have loopbacks!")
        return
    
    # Fetch missing loopbacks
    updated = 0
    for device in no_loopback:
        device_id = device.get('id')
        device_name = device.get('name')
        
        print(f"  Fetching loopback for {device_name} (ID: {device_id})...", end='')
        
        # Force fresh fetch from Netshot
        loopback = api.get_loopback_interface(device_id, device_name, force_refresh=True)
        
        if loopback:
            device['loopback'] = loopback
            updated += 1
            print(f" ✓ {loopback}")
        else:
            print(" ✗ Not found")
    
    if updated > 0:
        # Save updated device list back to cache
        if isinstance(cache_data, dict) and 'value' in cache_data:
            cache_data['value'] = devices
            save_data = cache_data
        else:
            save_data = devices
            
        with open(cache_file, 'w') as f:
            json.dump(save_data, f)
        
        print(f"\n✓ Updated {updated} devices with loopbacks")
        print("Refresh your browser to see the changes!")
    else:
        print("\nNo loopbacks could be fetched from Netshot")

if __name__ == '__main__':
    main()
