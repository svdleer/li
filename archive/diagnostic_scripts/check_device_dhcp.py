#!/usr/bin/env python3
"""
Quick diagnostic script to check DHCP validation for a specific device
"""
import sys
import logging
from netshot_api import get_netshot_client
from dhcp_database import DHCPDatabase

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_device_dhcp(device_name):
    """Check DHCP validation for a specific device"""
    
    # Get Netshot client
    logger.info(f"Checking DHCP validation for device: {device_name}")
    netshot_client = get_netshot_client()
    
    # Get CMTS devices
    logger.info("Fetching CMTS devices from Netshot...")
    cmts_devices = netshot_client.get_cmts_devices(force_refresh=False)
    
    # Find the device
    device = None
    for d in cmts_devices:
        if d.get('name', '').lower() == device_name.lower() or \
           d.get('oss10_hostname', '').lower() == device_name.lower():
            device = d
            break
    
    if not device:
        logger.error(f"Device '{device_name}' not found in Netshot CMTS devices")
        logger.info(f"Available devices: {[d.get('name') for d in cmts_devices[:10]]}")
        return
    
    # Print device info
    print("\n" + "="*80)
    print(f"DEVICE INFORMATION: {device_name}")
    print("="*80)
    print(f"Netshot Name: {device.get('name')}")
    print(f"OSS10 Hostname: {device.get('oss10_hostname')}")
    print(f"Primary Subnet: {device.get('primary_subnet')}")
    print(f"Loopback: {device.get('loopback')}")
    print(f"Management IP: {device.get('mgmt_address')}")
    print(f"\nAll Subnets ({len(device.get('subnets', []))}):")
    for subnet in device.get('subnets', []):
        print(f"  - {subnet}")
    
    # Get public subnets
    from subnet_utils import is_public_ipv4, is_public_ipv6
    primary = device.get('primary_subnet')
    all_subnets = device.get('subnets', [])
    
    public_ipv4 = [s for s in all_subnets if '.' in s and ':' not in s and s != primary and is_public_ipv4(s.split('/')[0])]
    public_ipv6 = [s for s in all_subnets if ':' in s and is_public_ipv6(s.split('/')[0])]
    
    print(f"\nPublic IPv4 Subnets ({len(public_ipv4)}):")
    for subnet in public_ipv4:
        print(f"  - {subnet}")
    
    print(f"\nPublic IPv6 Subnets ({len(public_ipv6)}):")
    for subnet in public_ipv6:
        print(f"  - {subnet}")
    
    # Check DHCP database
    print("\n" + "="*80)
    print("DHCP DATABASE VALIDATION")
    print("="*80)
    
    dhcp_db = DHCPDatabase()
    if not dhcp_db.connect():
        logger.error("Failed to connect to DHCP database")
        return
    
    # Use OSS10 hostname for DHCP lookup
    dhcp_hostname = device.get('oss10_hostname') or device.get('name')
    logger.info(f"Looking up DHCP scopes for: {dhcp_hostname}")
    
    # Get DHCP scopes
    dhcp_scopes = dhcp_db.get_scopes_by_primary(primary)
    print(f"\nDHCP IPv4 Scopes from primary subnet {primary}: {len(dhcp_scopes)}")
    for scope in dhcp_scopes:
        print(f"  - {scope['scope']} (VLAN {scope.get('vlan', 'N/A')})")
    
    # Get IPv6 scopes
    ipv6_scopes = dhcp_db.get_ipv6_scopes_by_hostname(dhcp_hostname)
    print(f"\nDHCP IPv6 Scopes for hostname {dhcp_hostname}: {len(ipv6_scopes)}")
    for scope in ipv6_scopes:
        print(f"  - {scope['prefixname']} (prefix: {scope['prefix']})")
    
    # Run full validation
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    
    validation = dhcp_db.validate_device_dhcp(dhcp_hostname, primary, public_ipv4, public_ipv6)
    
    print(f"\nHas DHCP: {validation['has_dhcp']}")
    print(f"DHCP Scopes Count: {validation['dhcp_scopes_count']}")
    print(f"\nMatched IPv4 Subnets ({len(validation['matched'])}):")
    for subnet in validation['matched']:
        print(f"  ✓ {subnet}")
    
    print(f"\nMissing in DHCP ({len(validation['missing_in_dhcp'])}):")
    for subnet in validation['missing_in_dhcp']:
        print(f"  ✗ {subnet}")
    
    print(f"\nExtra in DHCP (not in Netshot) ({len(validation['extra_in_dhcp'])}):")
    for subnet in validation['extra_in_dhcp']:
        print(f"  ! {subnet}")
    
    print(f"\nIPv6 Matched ({len(validation.get('ipv6_matched', []))}):")
    for subnet in validation.get('ipv6_matched', []):
        print(f"  ✓ {subnet}")
    
    print(f"\nIPv6 Missing in DHCP ({len(validation.get('ipv6_missing_in_dhcp', []))}):")
    for subnet in validation.get('ipv6_missing_in_dhcp', []):
        print(f"  ✗ {subnet}")
    
    # Check cache
    print("\n" + "="*80)
    print("CACHED VALIDATION")
    print("="*80)
    
    cached = dhcp_db.get_cached_dhcp_validation(device.get('name'))
    if cached:
        print(f"Cache Updated: {cached.get('updated_at')}")
        print(f"Cached Has DHCP: {cached.get('has_dhcp')}")
        print(f"Cached Scope Count: {cached.get('dhcp_scopes_count')}")
    else:
        print("No cached validation found")
    
    dhcp_db.disconnect()
    print("\n" + "="*80)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_device_dhcp.py <device_name>")
        print("Example: python check_device_dhcp.py ad00cbr67")
        sys.exit(1)
    
    device_name = sys.argv[1]
    check_device_dhcp(device_name)
