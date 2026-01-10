#!/usr/bin/env python3
"""
Check if lawfulInterception contains LI_MIRROR
"""
import requests
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETSHOT_API_URL = "https://localhost:8443/api"
NETSHOT_API_KEY = "CWuoygkAW7IVNrPxycNy3omca5m3ahib"
DEVICE_ID = 12135

headers = {'X-Netshot-API-Token': NETSHOT_API_KEY}

# Get configs
response = requests.get(f"{NETSHOT_API_URL}/devices/{DEVICE_ID}/configs", headers=headers, verify=False, timeout=30)
config_id = response.json()[0].get('id')

# Get lawfulInterception
print("Checking lawfulInterception...")
response = requests.get(f"{NETSHOT_API_URL}/configs/{config_id}/lawfulInterception", headers=headers, verify=False, timeout=30)
lawful_config = response.text

print(f"Length: {len(lawful_config)}")
print(f"Contains LI_MIRROR: {'LI_MIRROR' in lawful_config}")

if 'LI_MIRROR' in lawful_config:
    pattern = r'mirror-dest\s+"LI_MIRROR".*?gateway\s+ip-address\s+source\s+(\d+\.\d+\.\d+\.\d+)'
    match = re.search(pattern, lawful_config, re.IGNORECASE | re.DOTALL)
    if match:
        print(f"✓ IP found: {match.group(1)}")
    else:
        idx = lawful_config.find('LI_MIRROR')
        print(f"Snippet:\n{lawful_config[max(0,idx-100):idx+300]}")
