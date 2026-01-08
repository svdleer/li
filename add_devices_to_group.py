#!/usr/bin/env python3
"""
Add devices to LI_Target_Devices group
"""
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETSHOT_API_URL = "https://localhost:8443/api"
NETSHOT_API_KEY = "obD5VpnxnkZH6mbvjN5jXy6WRbYemF1q"
headers = {'X-Netshot-API-Token': NETSHOT_API_KEY, 'Content-Type': 'application/json'}

# Device names from the search (57 devices found)
device_names = [
    "TNF-C9006-AH-001", "TNF-C9910-AH-001", "TNF-C9910-AH-002", "AH-TR0009-DR101", 
    "AH-TR0009-DR102", "amr-rc0011-dr102", "asd-rc0001-dr102", "TNF-C9006-ASD-003",
    "asd-tr0006-dr102", "TNF-C9901-ASD-001", "TNF-C9001-ASD-003", "TNF-C9010-ASD-003",
    "TNF-C9010-ASD-004", "asd-tr0021-dr102", "ASD-TR0021-DR103", "asd-tr0042-dr102",
    "asd-tr0409-dr102", "asd-tr0411-dr106", "TNF-C9010-ASD-002", "TNF-C9001-ASD-002",
    "TNF-C9010-ASD-001", "asd-tr0610-dr103", "asn-rc0002-dr102", "TNF-C9001-MT-001",
    "TNF-C9001-MT-002", "dv-rc0001-dr102", "ehv-rc0002-dr102", "TNF-C9910-EHV-001",
    "TNF-C9910-EHV-002", "EHV-TR0001-DR101", "EHV-TR0001-DR102", "gn-rc0002-dr102",
    "gv-rc0011-dr102", "gv-rc0052-dr102", "hm-rc0100-dr102", "hm-rc0100-dr103",
    "hm-rc0100-dr104", "ht-rc0001-dr102", "hvs-rc0002-dr102", "lls-rc0100-dr101",
    "lls-rc0100-dr102", "mnd-rc0001-dr102", "nm-rc0110-dr101", "nm-rc0110-dr102",
    "rt-lc0100-dr102", "rt-rc0173-dr102", "slr-tr0004-cr103-new", "slr-tr0004-cr104-new",
    "SLR-TR0004-DR101", "SLR-TR0004-DR102", "tb-rc0001-dr102", "venl-rc0003-dr102",
    "vnn-rc0001-dr102", "weer-rc0002-dr102", "zl-rc0001-dr102", "zp-rc0100-dr101",
    "zp-rc0100-dr102"
]

print("Fetching all devices from groups 206 and 209...")
devices_206 = requests.get(f"{NETSHOT_API_URL}/devices", params={'group': 206}, headers=headers, verify=False).json()
devices_209 = requests.get(f"{NETSHOT_API_URL}/devices", params={'group': 209}, headers=headers, verify=False).json()
all_devices = devices_206 + devices_209

print(f"Total devices fetched: {len(all_devices)}")

# Find matching devices
device_ids = []
for device in all_devices:
    if device.get('name') in device_names:
        device_ids.append({'id': device.get('id'), 'name': device.get('name')})

print(f"Found {len(device_ids)} matching devices")

# Create group
group_name = "LI_Target_Devices"
group_data = {"name": group_name}
print(f"\nCreating group '{group_name}'...")
create_response = requests.post(f"{NETSHOT_API_URL}/groups", headers=headers, json=group_data, verify=False)

if create_response.ok:
    group = create_response.json()
    group_id = group.get('id')
    print(f"✓ Group created with ID: {group_id}")
elif create_response.status_code == 409:
    # Group already exists, get its ID
    groups = requests.get(f"{NETSHOT_API_URL}/groups", headers=headers, verify=False).json()
    group_id = next((g['id'] for g in groups if g.get('name') == group_name), None)
    if group_id:
        print(f"✓ Group already exists with ID: {group_id}")
    else:
        print("✗ Could not find group")
        exit(1)
else:
    print(f"✗ Failed to create group: {create_response.status_code}")
    exit(1)

# Add devices to group
print(f"\nAdding {len(device_ids)} devices to group...")
for device in device_ids:
    add_data = {"group": group_id, "device": device['id']}
    add_response = requests.post(f"{NETSHOT_API_URL}/groups/{group_id}/devices", headers=headers, json=add_data, verify=False)
    if add_response.ok:
        print(f"  ✓ {device['name']}")
    else:
        print(f"  ✗ {device['name']} - {add_response.status_code}")

print(f"\n✓ Done! Added devices to group '{group_name}'")
