"""
Test the CMTS Public Subnets Diagnostic
"""
import re
import json

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
    ipv4_pattern = r'ip address (\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)'
    for match in re.finditer(ipv4_pattern, text):
        ip, mask = match.group(1), match.group(2)
        if is_public_ipv4(ip):
            cidr_prefix = netmask_to_cidr(mask)
            if cidr_prefix:
                result["ipv4_subnets"].append(f"{ip}/{cidr_prefix}")

def extract_ipv6_subnets(text, result):
    """Extract and filter public IPv6 subnets from text"""
    ipv6_pattern = r'ipv6 address ([0-9a-fA-F:]+)/(\d+)'
    for match in re.finditer(ipv6_pattern, text):
        ipv6, prefix = match.group(1), match.group(2)
        if is_public_ipv6(ipv6):
            result["ipv6_subnets"].append(f"{ipv6}/{prefix}")

def diagnose_test(device_name, config):
    """Test version of diagnose function"""
    # Detect vendor and interface type based on hostname pattern
    vendor = 'unknown'
    interface_name = None
    
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
        return result
    
    # Parse based on vendor
    if vendor == 'Commscope E6000':
        # E6000: Extract all lines with cable-mac 1.0 and IP addresses
        ipv4_e6000_pattern = r'configure interface cable-mac 1\.0 ip address (\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)'
        ipv6_e6000_pattern = r'configure interface cable-mac 1\.0 ipv6 address ([0-9a-fA-F:]+)/(\d+)'
        
        # Extract IPv4
        for match in re.finditer(ipv4_e6000_pattern, config):
            ip, mask = match.group(1), match.group(2)
            if is_public_ipv4(ip):
                cidr_prefix = netmask_to_cidr(mask)
                if cidr_prefix:
                    result["ipv4_subnets"].append(f"{ip}/{cidr_prefix}")
        
        # Extract IPv6
        for match in re.finditer(ipv6_e6000_pattern, config):
            ipv6, prefix = match.group(1), match.group(2)
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
    
    return result

if __name__ == '__main__':
    # Test with E6000 config
    config_file = 'ZNB-LC0001-CCAP001_currentConfig_2025-12-29_18-42.cfg'
    device_name = 'ZNB-LC0001-CCAP001'
    
    print(f"Testing diagnostic on: {device_name}")
    print("=" * 80)
    
    with open(config_file, 'r') as f:
        config = f.read()
    
    result = diagnose_test(device_name, config)
    
    print(json.dumps(result, indent=2))
    print("\n" + "=" * 80)
    print(f"Found: {result['found']}")
    print(f"IPv4 Subnets: {len(result['ipv4_subnets'])}")
    print(f"IPv6 Subnets: {len(result['ipv6_subnets'])}")
