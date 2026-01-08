#!/usr/bin/env python3
"""
Lookup device names from Netshot by IP addresses
"""
import os
os.environ['NETSHOT_BASE_URL'] = 'https://localhost:8443'

from netshot_api import NetshotAPI
import sys

# List of IP addresses to lookup
ip_addresses = """
213.51.3.41 
213.51.0.9  
213.51.0.10 
213.51.0.56 
213.51.0.57 
213.51.2.35 
213.51.0.60 
213.51.63.1 
213.51.63.3 
213.51.63.5 
213.51.3.40 
213.51.0.50 
213.51.3.111
213.51.3.199
213.51.3.23 
213.51.3.24 
213.51.1.171
213.51.0.47 
213.51.63.2 
213.51.63.4 
213.51.63.6 
213.51.0.53 
213.51.0.51 
213.51.1.170
213.51.3.22 
213.51.3.99 
213.51.3.21 
213.51.0.61 
213.51.2.30 
213.51.3.29 
213.51.3.30 
213.51.2.40 
213.51.1.175
213.51.0.13 
213.51.0.14 
213.51.0.58 
213.51.0.59 
213.51.2.31 
213.51.2.32 
213.51.2.33 
213.51.1.174
213.51.1.178
213.51.1.179
213.51.2.47 
213.51.2.39 
213.51.1.172
213.51.1.173
213.51.2.38 
213.51.1.176
213.51.1.177
213.51.1.166
213.51.1.167
213.51.0.31 
213.51.0.32 
213.51.0.54 
213.51.0.55 
213.51.2.46 
213.51.2.29 
213.51.2.34 
213.51.2.28 
213.51.2.41 
213.51.1.168
213.51.1.169
""".strip().split('\n')

def main():
    # Initialize Netshot API
    api = NetshotAPI()
    
    # Get all CMTS and PE devices
    print("Fetching all devices from Netshot...")
    cmts_devices = api.get_cmts_devices()
    pe_devices = api.get_pe_devices()
    devices = cmts_devices + pe_devices
    
    if not devices:
        print("Error: Could not fetch devices from Netshot")
        sys.exit(1)
    
    # Build a mapping of IP -> device info
    ip_to_device = {}
    for device in devices:
        mgmt_ip = device.get('mgmtAddress', {}).get('ip')
        if mgmt_ip:
            ip_to_device[mgmt_ip] = device
    
    print(f"\nTotal devices in Netshot: {len(devices)}")
    print(f"Devices with management IP: {len(ip_to_device)}\n")
    print("=" * 80)
    print(f"{'IP Address':<20} {'Device Name':<30} {'Type':<15}")
    print("=" * 80)
    
    found = 0
    not_found = []
    
    for ip_line in ip_addresses:
        ip = ip_line.strip()
        if not ip:
            continue
            
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
    print(f"  Total IPs searched: {len([ip for ip in ip_addresses if ip.strip()])}")
    print(f"  Found in Netshot: {found}")
    print(f"  Not found: {len(not_found)}")
    
    if not_found:
        print(f"\nIPs not found in Netshot:")
        for ip in not_found:
            print(f"  - {ip}")

if __name__ == '__main__':
    main()
