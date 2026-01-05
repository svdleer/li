"""
Extract Public IP Subnets from Bundle/IP-Bundle/Cable-Mac Interfaces (CIDR Format)
Supports: 
- Cisco cBR8: interface Bundle1
- Casa 100G (CCAP1xx/CBRxx): interface ip-bundle 1
- Commscope EVO (CCAPVxxx): interface ip-bundle 1
- Commscope E6000 (CCAP0xx/DBRxx): configure interface cable-mac 1.0
Python Diagnostic - Uses cached running config

Author  : Silvester van der Leer
Version : 1.0 
Date    : 01-01-2026

"""
import re
import json

def normalize_subnet(ip, prefix):
    """
    Normalize subnet from host IP to network address
    Example: 10.254.216.1/24 -> 10.254.216.0/24
    
    Args:
        ip: IP address string
        prefix: CIDR prefix length
        
    Returns:
        Normalized subnet string
    """
    try:
        # Split IP into octets
        octets = [int(x) for x in ip.split('.')]
        
        # Calculate network address based on prefix length
        mask_bits = int(prefix)
        
        # Create mask
        mask = (0xFFFFFFFF << (32 - mask_bits)) & 0xFFFFFFFF
        
        # Convert IP to integer
        ip_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
        
        # Apply mask to get network address
        network_int = ip_int & mask
        
        # Convert back to octets
        network_octets = [
            (network_int >> 24) & 0xFF,
            (network_int >> 16) & 0xFF,
            (network_int >> 8) & 0xFF,
            network_int & 0xFF
        ]
        
        return f"{'.'.join(map(str, network_octets))}/{prefix}"
    except:
        # If normalization fails, return original
        return f"{ip}/{prefix}"

def netmask_to_cidr(netmask):
    """Convert netmask to CIDR prefix length"""
    try:
        return sum([bin(int(x)).count('1') for x in netmask.split('.')])
    except:
        return None

def is_public_ipv4(ip):
    """Check if IPv4 address is public (not RFC1918 or test ranges)"""
    return not (ip.startswith('10.') or 
                re.match(r'^172\.(1[6-9]|2[0-9]|3[0-1])\.', ip) or
                ip.startswith('192.168.') or
                ip.startswith('198.18.'))

def is_public_ipv6(ipv6):
    """Check if IPv6 address is public (not link-local or ULA)"""
    ipv6_lower = ipv6.lower()
    return not (ipv6_lower.startswith('fe80:') or
                ipv6_lower.startswith('fc00:') or
                ipv6_lower.startswith('fd00:'))

def extract_ipv4_subnets(text, result):
    """Extract and filter public IPv4 subnets from text"""
    ipv4_pattern = r'ip address (\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)(\s+secondary)?'
    for match in re.finditer(ipv4_pattern, text):
        ip, mask, secondary = match.group(1), match.group(2), match.group(3)
        cidr_prefix = netmask_to_cidr(mask)
        if cidr_prefix:
            subnet = normalize_subnet(ip, cidr_prefix)
            # Mark primary subnet (the one without 'secondary') - regardless of public/private
            if not secondary and "primary_subnet" not in result:
                result["primary_subnet"] = subnet
            # Only add public IPs to the subnets list
            if is_public_ipv4(ip):
                result["ipv4_subnets"].append(subnet)

def extract_ipv6_subnets(text, result):
    """Extract and filter public IPv6 subnets from text"""
    ipv6_pattern = r'ipv6 address ([0-9a-fA-F:]+)/(\d+)'
    for match in re.finditer(ipv6_pattern, text):
        ipv6, prefix = match.group(1), match.group(2)
        # Normalize /56 to /40
        if prefix == '56':
            prefix = '40'
        if is_public_ipv6(ipv6):
            result["ipv6_subnets"].append(f"{ipv6}/{prefix}")

def diagnose(cli, device, diagnostic):
    # Get device name and config from Netshot cache (try both keys)
    device_name = device.get('name') or 'unknown'
    config = device.get('runningConfig') or device.get('currentConfig') or ''
    
    # Detect vendor and interface type based on hostname pattern
    vendor = 'unknown'
    interface_name = None
    
    # Casa 100G CCAP and CBR devices
    if re.match(r'^.*(CCAP1\d{2}|CBR\d{2}).*$', device_name, re.IGNORECASE):
        vendor = 'Casa 100G'
        interface_name = 'ip-bundle 1'
    elif re.match(r'^.*CCAPV\d{3}.*$', device_name, re.IGNORECASE):
        vendor = 'Commscope EVO'
        interface_name = 'ip-bundle 1'
    elif re.match(r'^.*(CCAP0\d{2}|DBR\d{2}).*$', device_name, re.IGNORECASE):
        vendor = 'Commscope E6000'
        interface_name = 'cable-mac 1.0'
    else:
        vendor = 'Cisco IOS/IOS-XE'
        interface_name = 'Bundle1'
    
    result = {
        "device_name": device_name,
        "vendor": vendor,
        "interface": interface_name,
        "found": False,
        "ipv4_subnets": [],
        "ipv6_subnets": []
    }
    
    if not config:
        diagnostic.set(json.dumps(result, indent=2))
        return
    
    # Parse based on vendor
    if vendor == 'Commscope E6000':
        # E6000: Extract all lines with cable-mac 1.0 and IP addresses
        ipv4_e6000_pattern = r'configure interface cable-mac 1\.0 ip address (\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)(\s+secondary)?'
        ipv6_e6000_pattern = r'configure interface cable-mac 1\.0 ipv6 address ([0-9a-fA-F:]+)/(\d+)'
        
        # Extract IPv4
        for match in re.finditer(ipv4_e6000_pattern, config):
            ip, mask, secondary = match.group(1), match.group(2), match.group(3)
            cidr_prefix = netmask_to_cidr(mask)
            if cidr_prefix:
                subnet = normalize_subnet(ip, cidr_prefix)
                # Mark primary subnet (the one without 'secondary') - regardless of public/private
                if not secondary and "primary_subnet" not in result:
                    result["primary_subnet"] = subnet
                # Only add public IPs to the subnets list
                if is_public_ipv4(ip):
                    result["ipv4_subnets"].append(subnet)
        
        # Extract IPv6
        for match in re.finditer(ipv6_e6000_pattern, config):
            ipv6, prefix = match.group(1), match.group(2)
            # Normalize /56 to /40
            if prefix == '56':
                prefix = '40'
            if is_public_ipv6(ipv6):
                result["ipv6_subnets"].append(f"{ipv6}/{prefix}")
    
    elif interface_name == 'ip-bundle 1':
        # Casa 100G / Commscope EVO: Block format
        patterns = [
            r'interface ip-bundle 1\s+(.*?)(?=\ninterface\s|\n!\s*\n|\Z)',
            r'interface ip-bundle 1\s+(.*?)(?=^interface\s|^!\s*$|\Z)',
            r'interface ip-bundle 1([\s\S]*?)(?=\ninterface|\n!$|\Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, config, re.MULTILINE | re.DOTALL)
            if match:
                interface_config = match.group(0)
                extract_ipv4_subnets(interface_config, result)
                extract_ipv6_subnets(interface_config, result)
                if result["ipv4_subnets"] or result["ipv6_subnets"]:
                    break
    
    elif interface_name == 'Bundle1':
        # Cisco: Standard interface block
        patterns = [
            r'interface Bundle1\s+(.*?)(?=\n^interface\s|\n^!\s*$|\Z)',
            r'interface Bundle1([\s\S]*?)(?=\ninterface|\n!$|\Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, config, re.MULTILINE | re.DOTALL)
            if match:
                interface_config = match.group(0)
                extract_ipv4_subnets(interface_config, result)
                extract_ipv6_subnets(interface_config, result)
                if result["ipv4_subnets"] or result["ipv6_subnets"]:
                    break
    
    # Set found=True if we have any subnets
    if result["ipv4_subnets"] or result["ipv6_subnets"]:
        result["found"] = True
    
    # Set the diagnostic result as JSON
    diagnostic.set(json.dumps(result, indent=2))