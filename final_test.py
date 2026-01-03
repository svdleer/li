#!/usr/bin/env python3
"""Final verification - what will browser see?"""
from netshot_api import NetshotAPI

# Use cache like the web app does
api = NetshotAPI(use_cache=True)

# Get devices with cache (like web app)
print("Fetching from CACHE (like web app)...")
devices = api.get_cmts_devices()

# Find AL-RC0263-CCAP001
device = next((d for d in devices if d['name'] == 'AL-RC0263-CCAP001'), None)

if device:
    subnets = device.get('subnets', [])
    print(f"\n✅ AL-RC0263-CCAP001")
    print(f"   Subnet count: {len(subnets)}")
    print(f"   First 5: {subnets[:5]}")
    
    if len(subnets) == 64:
        print(f"\n✅ SUCCESS! Browser will see 64 subnets")
    else:
        print(f"\n❌ FAIL! Browser will see {len(subnets)} subnets, not 64")
else:
    print("❌ Device not found")
