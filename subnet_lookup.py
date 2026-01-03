#!/usr/bin/env python3
"""
Subnet Search & Lookup Module
==============================

Search for IP addresses and CIDR blocks to find:
- Which device owns the subnet
- Whether it's included in XML generation
- Validation status (for CMTS)
- Full subnet details

Author: Silvester van der Leer
Version: 2.0
"""

import logging
from typing import Dict, List, Optional, Tuple
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address, IPv4Network, IPv6Network

logger = logging.getLogger(__name__)


class SubnetLookup:
    """Search and lookup tool for IP addresses and subnets"""
    
    def __init__(self, cmts_devices: List[Dict], pe_devices: List[Dict], validation_results: Dict):
        """
        Initialize subnet lookup with device and validation data
        
        Args:
            cmts_devices: List of CMTS devices with subnet info
            pe_devices: List of PE devices with subnet info
            validation_results: Validation results from subnet_validator
        """
        self.cmts_devices = cmts_devices
        self.pe_devices = pe_devices
        self.validation_results = validation_results
        
        # Build reverse lookup index: subnet -> device mapping
        self.subnet_index = self._build_subnet_index()
        
        logger.info(f"SubnetLookup initialized with {len(self.subnet_index)} indexed subnets")
    
    def _build_subnet_index(self) -> Dict[str, Dict]:
        """
        Build index of all subnets mapped to their devices
        
        Returns:
            Dict mapping subnet CIDR to device info
        """
        index = {}
        
        # Index CMTS subnets
        for device in self.cmts_devices:
            device_name = device['name']
            
            # Get validation results for this device
            validation = self.validation_results['cmts'].get(device_name, {})
            valid_subnets = validation.get('valid_subnets', {'ipv4': [], 'ipv6': []})
            
            # Index all subnets from the device
            for subnet_cidr in device.get('subnets', []):
                # Determine if included in XML (validated for CMTS)
                is_ipv6 = ':' in subnet_cidr
                included_in_xml = subnet_cidr in (
                    valid_subnets['ipv6'] if is_ipv6 else valid_subnets['ipv4']
                )
                
                index[subnet_cidr] = {
                    'device_name': device_name,
                    'device_type': 'CMTS',
                    'device_info': device,
                    'subnet_cidr': subnet_cidr,
                    'included_in_xml': included_in_xml,
                    'validation_status': 'validated' if included_in_xml else 'excluded',
                    'validation_reason': self._get_validation_reason(
                        device_name, subnet_cidr, validation
                    )
                }
        
        # Index PE subnets (all included)
        for device in self.pe_devices:
            device_name = device['name']
            
            for subnet_cidr in device.get('subnets', []):
                index[subnet_cidr] = {
                    'device_name': device_name,
                    'device_type': 'PE',
                    'device_info': device,
                    'subnet_cidr': subnet_cidr,
                    'included_in_xml': True,  # PE subnets always included
                    'validation_status': 'included',
                    'validation_reason': 'PE device - no validation required'
                }
        
        return index
    
    def _get_validation_reason(self, device_name: str, subnet_cidr: str, validation: Dict) -> str:
        """Get human-readable reason for subnet validation status"""
        if not validation:
            return 'No validation data available'
        
        valid_subnets = validation.get('valid_subnets', {'ipv4': [], 'ipv6': []})
        mismatches = validation.get('mismatches', {})
        
        is_ipv6 = ':' in subnet_cidr
        
        # Check if validated (in both Netshot and MySQL)
        if subnet_cidr in (valid_subnets['ipv6'] if is_ipv6 else valid_subnets['ipv4']):
            return 'Present in both Netshot and MySQL - Validated ✓'
        
        # Check mismatches
        if is_ipv6:
            if subnet_cidr in mismatches.get('only_in_netshot_ipv6', []):
                return 'Only in Netshot - NOT in MySQL ⚠️'
            if subnet_cidr in mismatches.get('only_in_mysql_ipv6', []):
                return 'Only in MySQL - NOT in Netshot ⚠️'
        else:
            if subnet_cidr in mismatches.get('only_in_netshot_ipv4', []):
                return 'Only in Netshot - NOT in MySQL ⚠️'
            if subnet_cidr in mismatches.get('only_in_mysql_ipv4', []):
                return 'Only in MySQL - NOT in Netshot ⚠️'
        
        return 'Unknown validation status'
    
    # ========================================================================
    # Search Functions
    # ========================================================================
    
    def search_by_ip(self, ip_string: str) -> List[Dict]:
        """
        Search for an IP address to find which subnet(s) contain it
        
        Args:
            ip_string: IP address as string (e.g., "203.80.5.100")
        
        Returns:
            List of matching subnet info dictionaries
        """
        try:
            ip = ip_address(ip_string)
        except ValueError as e:
            logger.error(f"Invalid IP address: {ip_string}")
            return []
        
        matches = []
        
        for subnet_cidr, info in self.subnet_index.items():
            try:
                network = ip_network(subnet_cidr, strict=False)
                if ip in network:
                    match = info.copy()
                    match['match_type'] = 'ip_in_subnet'
                    match['search_query'] = ip_string
                    matches.append(match)
            except ValueError:
                continue
        
        logger.info(f"IP search '{ip_string}': {len(matches)} matches found")
        return matches
    
    def search_by_cidr(self, cidr_string: str) -> Optional[Dict]:
        """
        Search for exact CIDR match
        
        Args:
            cidr_string: CIDR notation (e.g., "203.80.0.0/22")
        
        Returns:
            Subnet info dict if found, None otherwise
        """
        try:
            # Normalize CIDR
            network = ip_network(cidr_string, strict=False)
            normalized_cidr = str(network)
            
            result = self.subnet_index.get(normalized_cidr)
            if result:
                match = result.copy()
                match['match_type'] = 'exact_cidr'
                match['search_query'] = cidr_string
                logger.info(f"CIDR search '{cidr_string}': Match found on {result['device_name']}")
                return match
            else:
                logger.info(f"CIDR search '{cidr_string}': No match found")
                return None
                
        except ValueError as e:
            logger.error(f"Invalid CIDR: {cidr_string}")
            return None
    
    def search_by_device(self, device_name: str) -> List[Dict]:
        """
        Get all subnets for a specific device
        
        Args:
            device_name: Device hostname
        
        Returns:
            List of subnet info dictionaries
        """
        matches = [
            info.copy() for info in self.subnet_index.values()
            if info['device_name'].lower() == device_name.lower()
        ]
        
        # Add match metadata
        for match in matches:
            match['match_type'] = 'device_name'
            match['search_query'] = device_name
        
        logger.info(f"Device search '{device_name}': {len(matches)} subnets found")
        return matches
    
    def search_by_location(self, location: str) -> List[Dict]:
        """
        Get all subnets for devices in a specific location
        
        Args:
            location: Location name (e.g., "Amsterdam")
        
        Returns:
            List of subnet info dictionaries
        """
        matches = []
        
        for info in self.subnet_index.values():
            device_location = info['device_info'].get('location', '').lower()
            if location.lower() in device_location:
                match = info.copy()
                match['match_type'] = 'location'
                match['search_query'] = location
                matches.append(match)
        
        logger.info(f"Location search '{location}': {len(matches)} subnets found")
        return matches
    
    def search(self, query: str) -> Dict:
        """
        Universal search - auto-detects query type
        
        Args:
            query: Search query (IP, CIDR, device name, or location)
        
        Returns:
            Dict with search results and metadata
        """
        query = query.strip()
        
        if not query:
            return {
                'query': query,
                'query_type': 'empty',
                'results': [],
                'total_matches': 0
            }
        
        # Try IP address
        if '/' not in query and (':' in query or query.replace('.', '').isdigit()):
            ip_results = self.search_by_ip(query)
            if ip_results:
                return {
                    'query': query,
                    'query_type': 'ip_address',
                    'results': ip_results,
                    'total_matches': len(ip_results)
                }
        
        # Try CIDR
        if '/' in query:
            cidr_result = self.search_by_cidr(query)
            if cidr_result:
                return {
                    'query': query,
                    'query_type': 'cidr',
                    'results': [cidr_result],
                    'total_matches': 1
                }
        
        # Try device name
        device_results = self.search_by_device(query)
        if device_results:
            return {
                'query': query,
                'query_type': 'device_name',
                'results': device_results,
                'total_matches': len(device_results)
            }
        
        # Try location
        location_results = self.search_by_location(query)
        if location_results:
            return {
                'query': query,
                'query_type': 'location',
                'results': location_results,
                'total_matches': len(location_results)
            }
        
        # No matches
        return {
            'query': query,
            'query_type': 'no_match',
            'results': [],
            'total_matches': 0,
            'message': f'No matches found for "{query}"'
        }
    
    # ========================================================================
    # Statistics
    # ========================================================================
    
    def get_statistics(self) -> Dict:
        """Get statistics about indexed subnets"""
        stats = {
            'total_subnets': len(self.subnet_index),
            'cmts_subnets': 0,
            'pe_subnets': 0,
            'included_in_xml': 0,
            'excluded_from_xml': 0,
            'ipv4_count': 0,
            'ipv6_count': 0
        }
        
        for info in self.subnet_index.values():
            if info['device_type'] == 'CMTS':
                stats['cmts_subnets'] += 1
            else:
                stats['pe_subnets'] += 1
            
            if info['included_in_xml']:
                stats['included_in_xml'] += 1
            else:
                stats['excluded_from_xml'] += 1
            
            if ':' in info['subnet_cidr']:
                stats['ipv6_count'] += 1
            else:
                stats['ipv4_count'] += 1
        
        return stats


# ============================================================================
# Convenience Functions
# ============================================================================

def create_subnet_lookup(cmts_devices: List[Dict], pe_devices: List[Dict], 
                         validation_results: Dict) -> SubnetLookup:
    """Factory function to create SubnetLookup instance"""
    return SubnetLookup(cmts_devices, pe_devices, validation_results)


if __name__ == "__main__":
    # Demo test
    logging.basicConfig(level=logging.INFO)
    
    # Mock data for testing
    from demo_data import get_demo_generator
    from subnet_validator import create_subnet_validator
    
    demo_gen = get_demo_generator()
    cmts_devices = demo_gen.generate_cmts_devices()
    pe_devices = demo_gen.generate_pe_devices()
    
    validator = create_subnet_validator(demo_mode=True)
    validation_results = validator.validate_all_devices(cmts_devices, pe_devices)
    
    lookup = create_subnet_lookup(cmts_devices, pe_devices, validation_results)
    
    print("\n=== Subnet Lookup Demo ===")
    print(f"\nStatistics: {lookup.get_statistics()}")
    
    # Test IP search
    print("\n--- IP Search: 203.80.5.100 ---")
    ip_results = lookup.search_by_ip("203.80.5.100")
    for result in ip_results:
        print(f"  Device: {result['device_name']} ({result['device_type']})")
        print(f"  Subnet: {result['subnet_cidr']}")
        print(f"  In XML: {result['included_in_xml']}")
        print(f"  Status: {result['validation_reason']}")
    
    # Test CIDR search
    print("\n--- CIDR Search: 203.80.0.0/22 ---")
    cidr_result = lookup.search_by_cidr("203.80.0.0/22")
    if cidr_result:
        print(f"  Device: {cidr_result['device_name']} ({cidr_result['device_type']})")
        print(f"  In XML: {cidr_result['included_in_xml']}")
        print(f"  Status: {cidr_result['validation_reason']}")
    
    # Test universal search
    print("\n--- Universal Search: cmts-amsterdam-01 ---")
    search_result = lookup.search("cmts-amsterdam-01")
    print(f"  Query Type: {search_result['query_type']}")
    print(f"  Total Matches: {search_result['total_matches']}")
