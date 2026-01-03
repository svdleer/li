#!/usr/bin/env python3
"""
Subnet Validator and Cross-Reference Module
============================================

Handles subnet fetching from Netshot and cross-referencing with MySQL database.
- For CMTS: Fetch from Netshot AND validate against MySQL
- For PE: Fetch from Netshot only (no validation)

Author: Silvester van der Leer
Version: 2.0
"""

import logging
from typing import List, Dict, Tuple, Set
from ipaddress import ip_network, IPv4Network, IPv6Network

logger = logging.getLogger(__name__)


class SubnetValidator:
    """Validates subnets from Netshot against MySQL database"""
    
    def __init__(self, db_connection=None, netshot_client=None):
        """
        Initialize subnet validator
        
        Args:
            db_connection: MySQL database connection (optional for demo)
            netshot_client: Netshot API client (optional for demo)
        """
        self.db_connection = db_connection
        self.netshot_client = netshot_client
        self.demo_mode = (db_connection is None or netshot_client is None)
        
        if self.demo_mode:
            logger.info("SubnetValidator running in DEMO MODE")
    
    # ========================================================================
    # NETSHOT Subnet Fetching
    # ========================================================================
    
    def fetch_subnets_from_netshot(self, device_name: str, device_type: str) -> Dict[str, List[str]]:
        """
        Fetch IPv4 and IPv6 subnets from Netshot for a specific device
        
        Args:
            device_name: CMTS or PE hostname
            device_type: 'CMTS' or 'PE'
        
        Returns:
            Dict with 'ipv4' and 'ipv6' subnet lists
        """
        if self.demo_mode:
            return self._fetch_subnets_demo(device_name, device_type)
        
        try:
            # Real implementation would query Netshot API
            # Example: response = self.netshot_client.get_device_subnets(device_name)
            
            logger.info(f"Fetching subnets from Netshot for {device_name}")
            
            # Parse Netshot response and extract subnets from interfaces
            ipv4_subnets = []
            ipv6_subnets = []
            
            # TODO: Implement actual Netshot API call
            # This would parse interface configurations and extract subnet information
            
            return {
                'ipv4': ipv4_subnets,
                'ipv6': ipv6_subnets
            }
        except Exception as e:
            logger.error(f"Error fetching subnets from Netshot: {e}")
            return {'ipv4': [], 'ipv6': []}
    
    def _fetch_subnets_demo(self, device_name: str, device_type: str) -> Dict[str, List[str]]:
        """
        Demo implementation - generates mock subnet data
        
        Args:
            device_name: Device hostname
            device_type: 'CMTS' or 'PE'
        
        Returns:
            Dict with 'ipv4' and 'ipv6' subnet lists
        """
        # Extract device number from name (e.g., cmts-amsterdam-01 -> 01)
        parts = device_name.split('-')
        device_num = int(parts[-1]) if parts[-1].isdigit() else 1
        
        if device_type == 'CMTS':
            # CMTS subnets (public cable modem ranges)
            ipv4 = [
                f'203.{80 + (device_num * 4)}.0.0/22',
                f'203.{81 + (device_num * 4)}.0.0/22',
                f'198.18.{80 + device_num}.0/23',
                f'198.18.{82 + device_num}.0/23',
            ]
            ipv6 = [
                f'2a02:1{device_num:02x}00::/40',
                f'2a02:1{device_num:02x}10::/44',
            ]
        else:  # PE
            # PE subnets (business customer ranges)
            ipv4 = [
                f'198.51.{100 + device_num}.0/24',
                f'203.0.{113 + device_num}.0/24',
            ]
            ipv6 = [
                f'2001:db8:{device_num:x}00::/48',
                f'2001:db8:{device_num:x}10::/48',
            ]
        
        logger.info(f"DEMO: Fetched {len(ipv4)} IPv4 + {len(ipv6)} IPv6 subnets from Netshot for {device_name}")
        
        return {
            'ipv4': ipv4,
            'ipv6': ipv6
        }
    
    # ========================================================================
    # MySQL Database Cross-Reference
    # ========================================================================
    
    def fetch_subnets_from_mysql(self, device_name: str) -> Dict[str, List[str]]:
        """
        Fetch known subnets from MySQL database for a CMTS device
        
        Args:
            device_name: CMTS hostname
        
        Returns:
            Dict with 'ipv4' and 'ipv6' subnet lists
        """
        if self.demo_mode:
            return self._fetch_subnets_mysql_demo(device_name)
        
        try:
            logger.info(f"Querying MySQL for subnets assigned to {device_name}")
            
            cursor = self.db_connection.cursor()
            
            # Query IPv4 subnets
            cursor.execute("""
                SELECT subnet_cidr FROM ipv4_subnets 
                WHERE cmts_hostname = %s 
                AND is_active = 1
            """, (device_name,))
            ipv4_subnets = [row[0] for row in cursor.fetchall()]
            
            # Query IPv6 subnets
            cursor.execute("""
                SELECT subnet_cidr FROM ipv6_subnets 
                WHERE cmts_hostname = %s 
                AND is_active = 1
            """, (device_name,))
            ipv6_subnets = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            
            logger.info(f"Found {len(ipv4_subnets)} IPv4 + {len(ipv6_subnets)} IPv6 subnets in MySQL for {device_name}")
            
            return {
                'ipv4': ipv4_subnets,
                'ipv6': ipv6_subnets
            }
        except Exception as e:
            logger.error(f"Error querying MySQL database: {e}")
            return {'ipv4': [], 'ipv6': []}
    
    def _fetch_subnets_mysql_demo(self, device_name: str) -> Dict[str, List[str]]:
        """
        Demo implementation - simulates MySQL database lookup
        
        Args:
            device_name: CMTS hostname
        
        Returns:
            Dict with 'ipv4' and 'ipv6' subnet lists
        """
        # Extract device number
        parts = device_name.split('-')
        device_num = int(parts[-1]) if parts[-1].isdigit() else 1
        
        # Simulate database having most but not all subnets
        # (some Netshot subnets won't match, simulating real-world drift)
        ipv4 = [
            f'203.{80 + (device_num * 4)}.0.0/22',  # Matches Netshot
            f'203.{81 + (device_num * 4)}.0.0/22',  # Matches Netshot
            f'198.18.{80 + device_num}.0/23',       # Matches Netshot
            # Missing: f'198.18.{82 + device_num}.0/23' - not in DB!
            f'172.16.{device_num}.0/24',            # Extra subnet only in DB
        ]
        ipv6 = [
            f'2a02:1{device_num:02x}00::/40',       # Matches Netshot
            # Missing: f'2a02:1{device_num:02x}10::/44' - not in DB!
        ]
        
        logger.info(f"DEMO: Found {len(ipv4)} IPv4 + {len(ipv6)} IPv6 subnets in MySQL for {device_name}")
        
        return {
            'ipv4': ipv4,
            'ipv6': ipv6
        }
    
    # ========================================================================
    # Cross-Reference Logic
    # ========================================================================
    
    def validate_cmts_subnets(self, device_name: str) -> Dict:
        """
        Fetch subnets from Netshot and cross-reference with MySQL for CMTS
        
        Only subnets present in BOTH Netshot AND MySQL are included in XML
        
        Args:
            device_name: CMTS hostname
        
        Returns:
            Dict with validated subnets and validation results
        """
        logger.info(f"Validating subnets for CMTS: {device_name}")
        
        # Fetch from both sources
        netshot_subnets = self.fetch_subnets_from_netshot(device_name, 'CMTS')
        mysql_subnets = self.fetch_subnets_from_mysql(device_name)
        
        # Convert to sets for comparison
        netshot_ipv4 = set(netshot_subnets['ipv4'])
        netshot_ipv6 = set(netshot_subnets['ipv6'])
        mysql_ipv4 = set(mysql_subnets['ipv4'])
        mysql_ipv6 = set(mysql_subnets['ipv6'])
        
        # Find matches (intersection) - only these go into XML
        valid_ipv4 = netshot_ipv4 & mysql_ipv4
        valid_ipv6 = netshot_ipv6 & mysql_ipv6
        
        # Find mismatches for reporting
        only_netshot_ipv4 = netshot_ipv4 - mysql_ipv4
        only_netshot_ipv6 = netshot_ipv6 - mysql_ipv6
        only_mysql_ipv4 = mysql_ipv4 - netshot_ipv4
        only_mysql_ipv6 = mysql_ipv6 - netshot_ipv6
        
        validation_result = {
            'device_name': device_name,
            'device_type': 'CMTS',
            'valid_subnets': {
                'ipv4': sorted(list(valid_ipv4)),
                'ipv6': sorted(list(valid_ipv6))
            },
            'validation_stats': {
                'netshot_ipv4_count': len(netshot_ipv4),
                'netshot_ipv6_count': len(netshot_ipv6),
                'mysql_ipv4_count': len(mysql_ipv4),
                'mysql_ipv6_count': len(mysql_ipv6),
                'matched_ipv4_count': len(valid_ipv4),
                'matched_ipv6_count': len(valid_ipv6),
                'total_valid': len(valid_ipv4) + len(valid_ipv6)
            },
            'mismatches': {
                'only_in_netshot_ipv4': sorted(list(only_netshot_ipv4)),
                'only_in_netshot_ipv6': sorted(list(only_netshot_ipv6)),
                'only_in_mysql_ipv4': sorted(list(only_mysql_ipv4)),
                'only_in_mysql_ipv6': sorted(list(only_mysql_ipv6))
            }
        }
        
        # Log validation results
        logger.info(f"CMTS {device_name} validation: "
                   f"{len(valid_ipv4)} IPv4 + {len(valid_ipv6)} IPv6 matched")
        
        if only_netshot_ipv4 or only_netshot_ipv6:
            logger.warning(f"CMTS {device_name}: Subnets in Netshot but NOT in MySQL: "
                          f"{len(only_netshot_ipv4)} IPv4, {len(only_netshot_ipv6)} IPv6")
        
        if only_mysql_ipv4 or only_mysql_ipv6:
            logger.warning(f"CMTS {device_name}: Subnets in MySQL but NOT in Netshot: "
                          f"{len(only_mysql_ipv4)} IPv4, {len(only_mysql_ipv6)} IPv6")
        
        return validation_result
    
    def get_pe_subnets(self, device_name: str) -> Dict:
        """
        Fetch subnets from Netshot for PE devices (no validation needed)
        
        For PE devices, we only use Netshot data without cross-referencing
        
        Args:
            device_name: PE hostname
        
        Returns:
            Dict with subnets from Netshot
        """
        logger.info(f"Fetching subnets for PE: {device_name} (no validation)")
        
        netshot_subnets = self.fetch_subnets_from_netshot(device_name, 'PE')
        
        result = {
            'device_name': device_name,
            'device_type': 'PE',
            'valid_subnets': {
                'ipv4': netshot_subnets['ipv4'],
                'ipv6': netshot_subnets['ipv6']
            },
            'validation_stats': {
                'netshot_ipv4_count': len(netshot_subnets['ipv4']),
                'netshot_ipv6_count': len(netshot_subnets['ipv6']),
                'total_valid': len(netshot_subnets['ipv4']) + len(netshot_subnets['ipv6'])
            },
            'note': 'PE devices use Netshot data only, no MySQL validation'
        }
        
        logger.info(f"PE {device_name}: {len(netshot_subnets['ipv4'])} IPv4 + "
                   f"{len(netshot_subnets['ipv6'])} IPv6 subnets from Netshot")
        
        return result
    
    # ========================================================================
    # Batch Processing
    # ========================================================================
    
    def validate_all_devices(self, cmts_devices: List[Dict], pe_devices: List[Dict]) -> Dict:
        """
        Validate subnets for all CMTS and PE devices
        
        Args:
            cmts_devices: List of CMTS device dicts with 'name' key
            pe_devices: List of PE device dicts with 'name' key
        
        Returns:
            Dict with validation results for all devices
        """
        results = {
            'cmts': {},
            'pe': {},
            'summary': {
                'total_cmts': len(cmts_devices),
                'total_pe': len(pe_devices),
                'cmts_with_mismatches': 0,
                'total_valid_subnets': 0
            }
        }
        
        # Validate CMTS devices
        for device in cmts_devices:
            device_name = device['name']
            validation = self.validate_cmts_subnets(device_name)
            results['cmts'][device_name] = validation
            
            # Track mismatches
            has_mismatch = (
                len(validation['mismatches']['only_in_netshot_ipv4']) > 0 or
                len(validation['mismatches']['only_in_netshot_ipv6']) > 0 or
                len(validation['mismatches']['only_in_mysql_ipv4']) > 0 or
                len(validation['mismatches']['only_in_mysql_ipv6']) > 0
            )
            if has_mismatch:
                results['summary']['cmts_with_mismatches'] += 1
            
            results['summary']['total_valid_subnets'] += validation['validation_stats']['total_valid']
        
        # Get PE device subnets (no validation)
        for device in pe_devices:
            device_name = device['name']
            pe_result = self.get_pe_subnets(device_name)
            results['pe'][device_name] = pe_result
            results['summary']['total_valid_subnets'] += pe_result['validation_stats']['total_valid']
        
        logger.info(f"Validation complete: {results['summary']['total_cmts']} CMTS + "
                   f"{results['summary']['total_pe']} PE devices, "
                   f"{results['summary']['total_valid_subnets']} total valid subnets")
        
        return results


# ============================================================================
# Convenience Functions
# ============================================================================

def create_subnet_validator(demo_mode: bool = True):
    """
    Factory function to create SubnetValidator instance
    
    Args:
        demo_mode: If True, create demo validator without DB/Netshot connections
    
    Returns:
        SubnetValidator instance
    """
    if demo_mode:
        return SubnetValidator(db_connection=None, netshot_client=None)
    else:
        # TODO: Initialize real connections
        # db_conn = mysql.connector.connect(...)
        # netshot_client = NetshotAPIClient(...)
        # return SubnetValidator(db_connection=db_conn, netshot_client=netshot_client)
        raise NotImplementedError("Production mode requires database and Netshot client initialization")


if __name__ == "__main__":
    # Demo test
    logging.basicConfig(level=logging.INFO)
    
    validator = create_subnet_validator(demo_mode=True)
    
    # Test CMTS validation
    print("\n=== Testing CMTS Validation ===")
    cmts_result = validator.validate_cmts_subnets("cmts-amsterdam-01")
    print(f"Valid subnets: {cmts_result['valid_subnets']}")
    print(f"Mismatches: {cmts_result['mismatches']}")
    
    # Test PE fetching
    print("\n=== Testing PE Subnet Fetching ===")
    pe_result = validator.get_pe_subnets("pe-core-ams-01")
    print(f"PE subnets: {pe_result['valid_subnets']}")
