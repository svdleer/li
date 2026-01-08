#!/usr/bin/env python3
"""
Add devices with target IPs to group 275
"""
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETSHOT_API_URL = "https://localhost:8443/api"
NETSHOT_API_KEY = "obD5VpnxnkZH6mbvjN5jXy6WRbYemF1q"
TARGET_GROUP_ID = 275

headers = {
    'X-Netshot-API-Token': NETSHOT_API_KEY,
    'Content-Type': 'application/json'
}

# Target IPs
target_ips = [
    "213.51.3.41", "213.51.0.9", "213.51.0.10", "213.51.0.56", "213.51.0.57",
    "213.51.2.35", "213.51.0.60", "213.51.63.1", "213.51.63.3", "213.51.63.5",
    "213.51.3.40", "213.51.0.50", "213.51.3.111", "213.51.3.199", "213.51.3.23",
    "213.51.3.24", "213.51.1.171", "213.51.0.47", "213.51.63.2", "213.51.63.4",
    "213.51.63.6", "213.51.0.53", "213.51.0.51", "213.51.1.170", "213.51.3.22",
    "213.51.3.99", "213.51.3.21", "213.51.0.61", "213.51.2.30", "213.51.3.29",
    "213.51.3.30", "213.51.2.40", "213.51.1.175", "213.51.0.13", "213.51.0.14",
    "213.51.0.58", "213.51.0.59", "213.51.2.31", "213.51.2.32", "213.51.2.33",
    "213.51.1.174", "213.51.1.178", "213.51.1.179", "213.51.2.47", "213.51.2.39",
    "213.51.1.172", "213.51.1.173", "213.51.2.38", "213.51.1.176", "213.51.1.177",
    "213.51.1.166", "213.51.1.167", "213.51.0.31", "213.51.0.32", "213.51.0.54",
    "213.51.0.55", "213.51.2.46", "213.51.2.29", "213.51.2.34", "213.51.2.28",
    "213.51.2.41", "213.51.1.168", "213.51.1.169"
]

print(f"Fetching devices from groups 206 and 209...")
devices_206 = requests.get(f"{NETSHOT_API_URL}/devices", params={'group': 206}, headers=headers, verify=False).json()
devices_209 = requests.get(f"{NETSHOT_API_URL}/devices", params={'group': 209}, headers=headers, verify=False).json()
all_devices = devices_206 + devices_209

print(f"Total devices: {len(all_devices)}")
print(f"Finding devices with target IPs...")

device_ids = []
for idx, device in enumerate(all_devices):
    if (idx + 1) % 50 == 0:
        print(f"  Processed {idx + 1}/{len(all_devices)} devices...")
    
    device_id = device.get('id')
    device_name = device.get('name')
    
    # Get interfaces
    interfaces_response = requests.get(f"{NETSHOT_API_URL}/devices/{device_id}/interfaces", headers=headers, verify=False, timeout=30)
    if interfaces_response.ok:
        interfaces = interfaces_response.json()
        device_ips = set()
        for iface in interfaces:
            for ip4 in iface.get('ip4Addresses', []):
                device_ips.add(ip4.get('address'))
        
        # Check if any target IP matches
        if any(ip in target_ips for ip in device_ips):
            device_ids.append(device_id)
            print(f"  ✓ Found: {device_name} (ID: {device_id})")

print(f"\nTotal matching devices: {len(device_ids)}")

# Update group 275
payload = {
    "name": "LI_Target_Devices",
    "folder": "",
    "hiddenFromReports": False,
    "staticDevices": device_ids
}

print(f"\nUpdating group {TARGET_GROUP_ID} with {len(device_ids)} devices...")
response = requests.put(f"{NETSHOT_API_URL}/groups/{TARGET_GROUP_ID}", headers=headers, json=payload, verify=False)

if response.ok:
    print(f"✓ Successfully updated group {TARGET_GROUP_ID}")
    print(f"  Added {len(device_ids)} devices")
else:
    print(f"✗ Failed to update group: {response.status_code}")
    print(f"  Response: {response.text}")
