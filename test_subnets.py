#!/usr/bin/env python3
"""Test subnet fetching from Netshot"""
from netshot_api import NetshotAPI

# Create API instance with NO caching
api = NetshotAPI(use_cache=False)

# Get subnets directly
print("Testing AL-RC0263-CCAP001 (ID: 10978)")
print("=" * 60)

subnets = api.get_device_subnets(10978, "AL-RC0263-CCAP001", force_refresh=True)
print(f"\nSubnets returned: {len(subnets)}")
print(f"First 10:")
for subnet in subnets[:10]:
    print(f"  {subnet}")
if len(subnets) > 10:
    print(f"  ... and {len(subnets) - 10} more")
