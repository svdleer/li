#!/usr/bin/env python3
"""
Standalone script to lookup device names from Netshot by IP addresses
Does not modify any existing scripts
"""
import requests
import urllib3
from typing import List, Dict

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
NETSHOT_API_URL = "https://localhost:8443/api"
NETSHOT_API_KEY = "CWuoygkAW7IVNrPxycNy3omca5m3ahib"
DEVICE_GROUPS = [206, 209]  # Groups to query

# List of IP addresses to lookup
IP_ADDRESSES = [
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

def get_devices_from_group(group_id: int) -> List[Dict]:
    """Fetch devices from a specific Netshot group"""
    headers = {
        'X-Netshot-API-Token': NETSHOT_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        url = f"{NETSHOT_API_URL}/devices?group={group_id}"
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching devices from group {group_id}: {e}")
        return []

def get_device_interfaces(device_id: int) -> List[Dict]:
    """Fetch interfaces for a specific device"""
    headers = {
        'X-Netshot-API-Token': NETSHOT_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        url = f"{NETSHOT_API_URL}/devices/{device_id}/interfaces"
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return []

def main():
    print("Fetching devices from Netshot groups:", DEVICE_GROUPS)
    print("=" * 80)
    
    # Fetch devices from all groups
    all_devices = []
    for group_id in DEVICE_GROUPS:
        devices = get_devices_from_group(group_id)
        print(f"Group {group_id}: {len(devices)} devices")
        all_devices.extend(devices)
    
    print(f"\nTotal devices fetched: {len(all_devices)}")
    print("Fetching interfaces for all devices (this may take a while)...")
    
    # Build IP to device mapping by checking all interfaces
    ip_to_device = {}
    for i, device in enumerate(all_devices, 1):
        if i % 50 == 0:
            print(f"  Processed {i}/{len(all_devices)} devices...")
        
        device_id = device.get('id')
        interfaces = get_device_interfaces(device_id)
        
        for interface in interfaces:
            # Check IPv4 addresses
            ip4_addresses = interface.get('ip4Addresses', [])
            for ip4_addr in ip4_addresses:
                ip = ip4_addr.get('ip')
                if ip:
                    ip_to_device[ip] = device
            
            # Check IPv6 addresses
            ip6_addresses = interface.get('ip6Addresses', [])
            for ip6_addr in ip6_addresses:
                ip = ip6_addr.get('ip')
                if ip:
                    ip_to_device[ip] = device
    
    print(f"Processed {len(all_devices)} devices")
    print(f"Total IPs found: {len(ip_to_device)}\n")
    print("=" * 80)
    print(f"{'IP Address':<20} {'Device Name':<30} {'Type':<15}")
    print("=" * 80)
    
    found = 0
    not_found = []
    
    for ip in IP_ADDRESSES:
        if ip in ip_to_device:
            device = ip_to_device[ip]
            name = device.get('name', 'N/A')
            device_type = device.get('family', 'N/A')
            print(f"{ip:<20} {name:<30} {device_type:<15}")
            found += 1
        else:
            not_found.append(ip)
            print(f"{ip:<20} {'NOT FOUND':<30} {'-':<15}")
    
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  Total IPs searched: {len(IP_ADDRESSES)}")
    print(f"  Found in Netshot: {found}")
    print(f"  Not found: {len(not_found)}")
    
    if not_found:
        print(f"\nIPs not found in Netshot:")
        for ip in not_found:
            print(f"  - {ip}")

if __name__ == '__main__':
    main()
