#!/usr/bin/env python3
"""
Create Netshot device group with devices matching specific IPs
"""
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETSHOT_API_URL = "https://localhost:8443/api"
NETSHOT_API_KEY = "obD5VpnxnkZH6mbvjN5jXy6WRbYemF1q"

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
print(f"Fetching interfaces for all devices...")

matching_devices = []
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
            matching_devices.append({'id': device_id, 'name': device_name})
            print(f"  ✓ Found: {device_name}")

print(f"\nTotal matching devices: {len(matching_devices)}")

# Create new group
group_name = "LI_Target_Devices"
group_data = {
    "name": group_name,
    "hiddenFromReports": False
}

print(f"\nCreating device group '{group_name}'...")
create_response = requests.post(f"{NETSHOT_API_URL}/devicegroups", headers=headers, json=group_data, verify=False)

if create_response.ok:
    group = create_response.json()
    group_id = group.get('id')
    print(f"✓ Group created with ID: {group_id}")
    
    # Add devices to group
    print(f"\nAdding {len(matching_devices)} devices to group...")
    for device in matching_devices:
        add_data = {"group": group_id, "device": device['id']}
        add_response = requests.post(f"{NETSHOT_API_URL}/devicegroups/{group_id}/devices", headers=headers, json=add_data, verify=False)
        if add_response.ok:
            print(f"  ✓ Added: {device['name']}")
        else:
            print(f"  ✗ Failed: {device['name']}")
    
    print(f"\n✓ Successfully created group '{group_name}' with {len(matching_devices)} devices")
else:
    print(f"✗ Failed to create group: {create_response.status_code} - {create_response.text}")
