#!/usr/bin/env python3
"""
Add devices by name to group 275
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

# Device names from earlier successful search
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

print(f"Fetching all devices from groups 206 and 209...")
devices_206 = requests.get(f"{NETSHOT_API_URL}/devices", params={'group': 206}, headers=headers, verify=False).json()
devices_209 = requests.get(f"{NETSHOT_API_URL}/devices", params={'group': 209}, headers=headers, verify=False).json()
all_devices = devices_206 + devices_209

print(f"Total devices: {len(all_devices)}")
print(f"Finding matching devices by name...")

device_ids = []
found_names = []
for device in all_devices:
    device_name = device.get('name')
    if device_name in device_names:
        device_id = device.get('id')
        device_ids.append(device_id)
        found_names.append(device_name)
        print(f"  ✓ {device_name} (ID: {device_id})")

print(f"\nTotal matching devices: {len(device_ids)}")
print(f"Not found: {set(device_names) - set(found_names)}")

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
