#!/usr/bin/env python3
"""
Test Nokia diagnostic on real Netshot device via API
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

print(f"Fetching device {DEVICE_ID} from Netshot...")
response = requests.get(f"{NETSHOT_API_URL}/devices/{DEVICE_ID}", headers=headers, verify=False, timeout=30)
response.raise_for_status()
device = response.json()

print(f"Device: {device.get('name')}")
print(f"Family: {device.get('family')}")

# Try to get configs
print(f"\nFetching configs for device {DEVICE_ID}...")
response = requests.get(f"{NETSHOT_API_URL}/devices/{DEVICE_ID}/configs", headers=headers, verify=False, timeout=30)
if response.ok:
    configs = response.json()
    print(f"Found {len(configs)} config snapshots")
    
    if configs:
        latest_config = sorted(configs, key=lambda c: c.get('changeDate', 0), reverse=True)[0]
        config_id = latest_config.get('id')
        print(f"Latest config ID: {config_id}")
        
        # Try to get different config types
        config_types = ['lawfulInterception', 'configurationAsfc', 'configuration', 'runningConfig', 'mdConfig']
        
        print(f"\nTesting config types:")
        for config_type in config_types:
            try:
                url = f"{NETSHOT_API_URL}/configs/{config_id}/{config_type}"
                resp = requests.get(url, headers=headers, verify=False, timeout=30)
                if resp.ok:
                    config_data = resp.text if isinstance(resp.text, str) else str(resp.text)
                    print(f"✓ {config_type}: {len(config_data)} characters")
                    
                    # Check if LI_MIRROR is in this config
                    if 'LI_MIRROR' in config_data:
                        print(f"  → Contains LI_MIRROR!")
                        # Show snippet
                        idx = config_data.find('LI_MIRROR')
                        snippet = config_data[max(0, idx-50):min(len(config_data), idx+150)]
                        print(f"  Snippet: ...{snippet}...")
                else:
                    print(f"✗ {config_type}: HTTP {resp.status_code}")
            except Exception as e:
                print(f"✗ {config_type}: {str(e)[:50]}")

