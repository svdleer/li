#!/usr/bin/env python3
"""
DHCP Database Integration Module
=================================

Cross-references CMTS interfaces with DHCP database to enrich device data.
Matches DHCP scopes with CMTS interfaces for comprehensive network mapping.

Author: Silvester van der Leer
Version: 2.0
"""

import os
import logging
import mysql.connector
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager


class DHCPIntegration:
    """Handle DHCP database queries and CMTS interface cross-referencing"""
    
    def __init__(self, db_config: Dict = None):
        """
        Initialize DHCP integration
        
        Args:
            db_config: Database configuration dictionary with keys:
                      host, database, user, password, port
        """
        self.logger = logging.getLogger('dhcp_integration')
        
        # Use provided config or load from environment
        self.db_config = db_config or {
            'host': os.getenv('DHCP_DB_HOST', os.getenv('DB_HOST', 'localhost')),
            'database': os.getenv('DHCP_DB_DATABASE', os.getenv('DB_DATABASE', 'dhcp')),
            'user': os.getenv('DHCP_DB_USER', os.getenv('DB_USER', '')),
            'password': os.getenv('DHCP_DB_PASSWORD', os.getenv('DB_PASSWORD', '')),
            'port': int(os.getenv('DHCP_DB_PORT', os.getenv('DB_PORT', '3306')))
        }
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = mysql.connector.connect(**self.db_config)
            yield conn
        except mysql.connector.Error as e:
            self.logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn and conn.is_connected():
                conn.close()
    
    def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                
                self.logger.info("DHCP database connection successful")
                return result is not None
                
        except Exception as e:
            self.logger.error(f"DHCP database connection test failed: {e}")
            return False
    
    def get_dhcp_scopes(self, cmts_hostname: str = None) -> List[Dict]:
        """
        Get DHCP scopes from database
        
        Args:
            cmts_hostname: Optional filter by CMTS hostname
            
        Returns:
            List of DHCP scope dictionaries with keys:
            - scope_id: Scope ID
            - network: Network address
            - netmask: Network mask
            - gateway: Default gateway
            - cmts: CMTS hostname
            - interface: CMTS interface
            - vlan: VLAN ID (if available)
        """
        try:
            query = """
                SELECT 
                    id as scope_id,
                    network,
                    netmask,
                    gateway,
                    cmts_hostname as cmts,
                    cmts_interface as interface,
                    vlan_id as vlan,
                    description
                FROM dhcp_scopes
                WHERE active = 1
            """
            
            params = []
            if cmts_hostname:
                query += " AND cmts_hostname = %s"
                params.append(cmts_hostname)
            
            query += " ORDER BY cmts_hostname, cmts_interface"
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, params)
                scopes = cursor.fetchall()
                cursor.close()
                
                self.logger.info(f"Found {len(scopes)} DHCP scopes" + 
                               (f" for {cmts_hostname}" if cmts_hostname else ""))
                return scopes
                
        except Exception as e:
            self.logger.error(f"Error fetching DHCP scopes: {e}")
            return []
    
    def get_dhcp_scopes_by_interface(self, cmts_hostname: str, 
                                     interface_name: str) -> List[Dict]:
        """
        Get DHCP scopes for a specific CMTS interface
        
        Args:
            cmts_hostname: CMTS hostname
            interface_name: Interface name
            
        Returns:
            List of DHCP scope dictionaries
        """
        try:
            query = """
                SELECT 
                    id as scope_id,
                    network,
                    netmask,
                    gateway,
                    vlan_id as vlan,
                    description
                FROM dhcp_scopes
                WHERE active = 1
                  AND cmts_hostname = %s
                  AND cmts_interface = %s
                ORDER BY network
            """
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, (cmts_hostname, interface_name))
                scopes = cursor.fetchall()
                cursor.close()
                
                self.logger.debug(f"Found {len(scopes)} DHCP scopes for " +
                                f"{cmts_hostname} interface {interface_name}")
                return scopes
                
        except Exception as e:
            self.logger.error(f"Error fetching DHCP scopes for interface: {e}")
            return []
    
    def cross_reference_cmts_interfaces(self, cmts_device: Dict, 
                                       netshot_interfaces: List[Dict]) -> List[Dict]:
        """
        Cross-reference Netshot interfaces with DHCP database
        
        Args:
            cmts_device: CMTS device dictionary from Netshot
            netshot_interfaces: List of interface dictionaries from Netshot
            
        Returns:
            List of enriched interface dictionaries with DHCP scope information
        """
        try:
            cmts_hostname = cmts_device.get('name', '')
            
            if not cmts_hostname:
                self.logger.warning("No hostname provided for CMTS device")
                return netshot_interfaces
            
            # Get all DHCP scopes for this CMTS
            dhcp_scopes = self.get_dhcp_scopes(cmts_hostname)
            
            # Create mapping of interface -> scopes
            interface_scopes = {}
            for scope in dhcp_scopes:
                interface = scope.get('interface', '')
                if interface not in interface_scopes:
                    interface_scopes[interface] = []
                interface_scopes[interface].append(scope)
            
            # Enrich Netshot interfaces with DHCP data
            enriched_interfaces = []
            for interface in netshot_interfaces:
                interface_name = interface.get('name', '')
                
                # Add DHCP scopes to interface
                interface['dhcp_scopes'] = interface_scopes.get(interface_name, [])
                interface['has_dhcp'] = len(interface.get('dhcp_scopes', [])) > 0
                
                enriched_interfaces.append(interface)
            
            # Count how many interfaces have DHCP
            dhcp_count = sum(1 for i in enriched_interfaces if i.get('has_dhcp'))
            self.logger.info(f"Cross-referenced {dhcp_count} interfaces with DHCP for {cmts_hostname}")
            
            return enriched_interfaces
            
        except Exception as e:
            self.logger.error(f"Error cross-referencing CMTS interfaces: {e}")
            return netshot_interfaces
    
    def get_subnets_from_dhcp(self, cmts_hostname: str) -> List[str]:
        """
        Get all subnets/networks for a CMTS from DHCP database
        
        Args:
            cmts_hostname: CMTS hostname
            
        Returns:
            List of subnet strings in CIDR notation
        """
        try:
            scopes = self.get_dhcp_scopes(cmts_hostname)
            subnets = []
            
            for scope in scopes:
                network = scope.get('network')
                netmask = scope.get('netmask')
                
                if network and netmask:
                    # Convert netmask to CIDR prefix
                    prefix = self._netmask_to_cidr(netmask)
                    if prefix:
                        subnet = f"{network}/{prefix}"
                        if subnet not in subnets:
                            subnets.append(subnet)
            
            self.logger.info(f"Found {len(subnets)} subnets from DHCP for {cmts_hostname}")
            return subnets
            
        except Exception as e:
            self.logger.error(f"Error getting subnets from DHCP: {e}")
            return []
    
    def _netmask_to_cidr(self, netmask: str) -> Optional[int]:
        """
        Convert netmask to CIDR prefix length
        
        Args:
            netmask: Netmask in dotted decimal notation (e.g., 255.255.255.0)
            
        Returns:
            CIDR prefix length (e.g., 24) or None if invalid
        """
        try:
            # Convert netmask to binary and count 1s
            octets = netmask.split('.')
            if len(octets) != 4:
                return None
            
            binary = ''.join([bin(int(octet))[2:].zfill(8) for octet in octets])
            return binary.count('1')
            
        except Exception as e:
            self.logger.warning(f"Invalid netmask format '{netmask}': {e}")
            return None
    
    def enrich_cmts_device(self, cmts_device: Dict, 
                          netshot_interfaces: List[Dict] = None) -> Dict:
        """
        Enrich CMTS device with DHCP database information
        
        Args:
            cmts_device: CMTS device dictionary from Netshot
            netshot_interfaces: Optional list of Netshot interfaces
            
        Returns:
            Enriched device dictionary with DHCP information
        """
        try:
            cmts_hostname = cmts_device.get('name', '')
            
            # Cross-reference interfaces if provided
            if netshot_interfaces:
                enriched_interfaces = self.cross_reference_cmts_interfaces(
                    cmts_device, netshot_interfaces
                )
                cmts_device['interfaces_with_dhcp'] = enriched_interfaces
            
            # Add DHCP subnets to device
            dhcp_subnets = self.get_subnets_from_dhcp(cmts_hostname)
            
            # Merge with existing subnets from Netshot
            existing_subnets = set(cmts_device.get('subnets', []))
            all_subnets = list(existing_subnets.union(set(dhcp_subnets)))
            
            cmts_device['subnets'] = all_subnets
            cmts_device['dhcp_subnets'] = dhcp_subnets
            cmts_device['netshot_subnets'] = list(existing_subnets)
            
            self.logger.info(f"Enriched {cmts_hostname} with {len(dhcp_subnets)} DHCP subnets")
            
            return cmts_device
            
        except Exception as e:
            self.logger.error(f"Error enriching CMTS device: {e}")
            return cmts_device
    
    def get_cmts_statistics(self, cmts_hostname: str = None) -> Dict:
        """
        Get statistics about CMTS DHCP configuration
        
        Args:
            cmts_hostname: Optional filter by CMTS hostname
            
        Returns:
            Dictionary with statistics
        """
        try:
            query = """
                SELECT 
                    cmts_hostname,
                    COUNT(*) as scope_count,
                    COUNT(DISTINCT cmts_interface) as interface_count,
                    COUNT(DISTINCT vlan_id) as vlan_count
                FROM dhcp_scopes
                WHERE active = 1
            """
            
            params = []
            if cmts_hostname:
                query += " AND cmts_hostname = %s"
                params.append(cmts_hostname)
            
            query += " GROUP BY cmts_hostname"
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, params)
                
                if cmts_hostname:
                    result = cursor.fetchone()
                    cursor.close()
                    return result or {}
                else:
                    results = cursor.fetchall()
                    cursor.close()
                    return {r['cmts_hostname']: r for r in results}
                    
        except Exception as e:
            self.logger.error(f"Error getting CMTS statistics: {e}")
            return {}


# Convenience function
def get_dhcp_integration() -> DHCPIntegration:
    """Create and return a configured DHCP integration instance"""
    return DHCPIntegration()


if __name__ == "__main__":
    # Test the DHCP integration
    logging.basicConfig(level=logging.DEBUG)
    
    dhcp = get_dhcp_integration()
    
    if dhcp.test_connection():
        print("✓ DHCP database connection successful")
        
        # Test fetching scopes
        scopes = dhcp.get_dhcp_scopes()
        print(f"✓ Found {len(scopes)} DHCP scopes")
        
        if scopes:
            # Get statistics
            stats = dhcp.get_cmts_statistics()
            print(f"✓ Found {len(stats)} CMTS devices with DHCP configuration")
    else:
        print("✗ DHCP database connection failed")
