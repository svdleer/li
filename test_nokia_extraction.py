#!/usr/bin/env python3
"""
Test Nokia diagnostic with real configurationAsfc data
"""
import requests
import urllib3
import re
import json

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETSHOT_API_URL = "https://localhost:8443/api"
NETSHOT_API_KEY = "CWuoygkAW7IVNrPxycNy3omca5m3ahib"
DEVICE_ID = 12135

headers = {
    'X-Netshot-API-Token': NETSHOT_API_KEY,
    'Content-Type': 'application/json'
}

print(f"Fetching device {DEVICE_ID} configs...")
response = requests.get(f"{NETSHOT_API_URL}/devices/{DEVICE_ID}/configs", headers=headers, verify=False, timeout=30)
configs = response.json()
config_id = configs[0].get('id')

print(f"Fetching configurationAsfc from config {config_id}...")
config_response = requests.get(f"{NETSHOT_API_URL}/configs/{config_id}/configurationAsfc", headers=headers, verify=False, timeout=30)
config_asfc = config_response.text

print(f"Config length: {len(config_asfc)}")
print(f"Contains LI_MIRROR: {'LI_MIRROR' in config_asfc}")

# Simulate the diagnostic
result = {
    "LI_LOOPBACK": None
}

pattern = r'mirror-dest\s+"LI_MIRROR".*?gateway\s+ip-address\s+source\s+(\d+\.\d+\.\d+\.\d+)'
match = re.search(pattern, config_asfc, re.IGNORECASE | re.DOTALL)

if match:
    result["LI_LOOPBACK"] = match.group(1)
    print(f"\n✓ SUCCESS! Extracted IP: {result['LI_LOOPBACK']}")
    
    # Show context
    match_pos = match.start()
    context = config_asfc[max(0, match_pos-100):match_pos+200]
    print(f"\nContext around match:")
    print("-" * 80)
    print(context)
    print("-" * 80)
else:
    print("\n✗ Pattern did not match")
    
    # Check if LI_MIRROR exists
    if 'LI_MIRROR' in config_asfc:
        idx = config_asfc.find('LI_MIRROR')
        snippet = config_asfc[max(0, idx-100):idx+300]
        print(f"\nLI_MIRROR found but pattern didn't match. Here's the context:")
        print("-" * 80)
        print(snippet)
        print("-" * 80)

print(f"\nFinal result: {json.dumps(result, indent=2)}")
