#!/usr/bin/env python3
"""
Get Nokia LI_LOOPBACK IPs from diagnostic results
"""
import requests
import urllib3
import json

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETSHOT_API_URL = "https://localhost:8443/api"
NETSHOT_API_KEY = "CWuoygkAW7IVNrPxycNy3omca5m3ahib"
DEVICE_GROUP = 205
DIAGNOSTIC_NAME = "NOKIA_LI_INT"

headers = {
    'X-Netshot-API-Token': NETSHOT_API_KEY,
    'Content-Type': 'application/json'
}

print(f"Fetching devices from group {DEVICE_GROUP}...")
response = requests.get(f"{NETSHOT_API_URL}/devices", params={'group': DEVICE_GROUP}, headers=headers, verify=False, timeout=30)
devices = response.json()
print(f"Found {len(devices)} devices\n")

print("=" * 80)
print(f"{'Device Name':<40} {'LI_LOOPBACK IP':<20}")
print("=" * 80)

li_ips = []
for device in devices:
    device_name = device.get('name', 'N/A')
    device_id = device.get('id')
    
    # Get diagnostic results
    diag_response = requests.get(f"{NETSHOT_API_URL}/devices/{device_id}/diagnostics", headers=headers, verify=False, timeout=30)
    
    if diag_response.ok:
        diagnostics = diag_response.json()
        
        # Find NOKIA_LI_INT diagnostic
        for diag in diagnostics:
            if diag.get('name') == DIAGNOSTIC_NAME:
                result_text = diag.get('result', '{}')
                try:
                    result = json.loads(result_text)
                    li_loopback = result.get('LI_LOOPBACK')
                    if li_loopback:
                        print(f"{device_name:<40} {li_loopback:<20}")
                        li_ips.append({'device': device_name, 'ip': li_loopback})
                except:
                    pass

print("=" * 80)
print(f"\nTotal LI_LOOPBACK IPs found: {len(li_ips)}")
print("\nList of IPs:")
for item in li_ips:
    print(f"  {item['ip']} - {item['device']}")
