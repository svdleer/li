#!/usr/bin/env python3
"""
Fix Missing OSS10 Hostnames
============================
Updates devices with short hostnames (cbr/dbr/abr) to fetch OSS10 descriptive names.
"""

import json
import hashlib
import re
from netshot_api import NetshotAPI
from cache_manager import CacheManager

def has_short_hostname(device_name):
    """Check if device has a short hostname like cbr/dbr/abr instead of OSS10 name"""
    if not device_name:
        return False
    
    # Pattern: contains cbr, dbr, or abr followed by digits
    pattern = r'(cbr|dbr|abr)\d+'
    return bool(re.search(pattern, device_name.lower()))

def main():
    print("Fixing missing OSS10 hostnames...")
    
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
    
    # Extract actual device list
    devices = cache_data.get('value', [])
    
    if not isinstance(devices, list):
        print(f"ERROR: Unexpected cache format")
        return
    
    print(f"Loaded {len(devices)} devices from cache")
    
    # Find devices with short hostnames (cbr/dbr/abr)
    short_hostname_devices = []
    for d in devices:
        device_name = d.get('name', '')
        oss10_name = d.get('oss10_hostname')
        
        # If device name has cbr/dbr/abr but no OSS10 name, or OSS10 is same as short name
        if has_short_hostname(device_name) and (not oss10_name or oss10_name == device_name):
            short_hostname_devices.append(d)
    
    print(f"Found {len(short_hostname_devices)} devices with short hostnames")
    
    if not short_hostname_devices:
        print("All devices have OSS10 hostnames!")
        return
    
    # Fetch missing OSS10 hostnames
    updated = 0
    for device in short_hostname_devices:
        device_id = device.get('id')
        device_name = device.get('name')
        
        print(f"  Fetching OSS10 name for {device_name} (ID: {device_id})...", end='')
        
        # Fetch device details from Netshot
        device_data = api._make_request(f'devices/{device_id}')
        
        if device_data:
            # Extract OSS10 from comments
            comments = device_data.get('comments', '')
            oss10 = api._extract_oss10_from_comments(comments)
            
            if oss10 and oss10 != device_name:
                device['oss10_hostname'] = oss10
                updated += 1
                print(f" ✓ {oss10}")
            else:
                print(" ✗ Not found in comments")
        else:
            print(" ✗ API error")
    
    if updated > 0:
        # Save updated device list back to cache
        cache_data['value'] = devices
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        print(f"\n✓ Updated {updated} devices with OSS10 hostnames")
        print("Refresh your browser to see the changes!")
    else:
        print("\nNo OSS10 hostnames could be fetched from Netshot")

if __name__ == '__main__':
    main()
