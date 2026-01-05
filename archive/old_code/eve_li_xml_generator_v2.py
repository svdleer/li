#!/usr/bin/env python3
"""
EVE LI XML Generator V2 - Netshot Integration
==============================================

Refactored version that uses Netshot API and DHCP database
for comprehensive device and network management.

Key Changes from V1:
- Netshot API as primary data source
- DHCP database for CMTS cross-referencing
- Modular architecture
- Enhanced error handling
- Web application integration

Author: Silvester van der Leer
Version: 2.0
"""

import os
import sys
import gzip
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from xml.dom import minidom
import requests

# Import our new modules
from netshot_api import get_netshot_client, NetshotAPI
from dhcp_integration import get_dhcp_integration, DHCPIntegration

# Import base generator for XML functions
from eve_li_xml_generator import EVEXMLGenerator as BaseGenerator


class EVEXMLGeneratorV2(BaseGenerator):
    """
    Enhanced XML Generator using Netshot and DHCP database
    Extends the base generator with new data source integration
    """
    
    def __init__(self):
        """Initialize V2 generator with new data sources"""
        super().__init__()
        
        # Initialize new integrations
        self.netshot = get_netshot_client()
        self.dhcp = get_dhcp_integration()
        
        self.logger.info("Initialized EVE XML Generator V2 with Netshot integration")
    
    def get_devices_from_api(self) -> List[Dict]:
        """
        Override: Get devices from Netshot instead of old API
        
        Returns:
            List of device dictionaries from Netshot
        """
        self.logger.info("Fetching devices from Netshot API")
        
        try:
            # Get all production devices from Netshot
            devices = self.netshot.get_production_devices()
            
            self.logger.info(f"Retrieved {len(devices)} devices from Netshot")
            return devices
            
        except Exception as e:
            self.logger.error(f"Error fetching devices from Netshot: {e}")
            return []
    
    def get_cmts_devices(self) -> List[Dict]:
        """
        Get CMTS devices with enriched data from Netshot and DHCP
        
        Returns:
            List of CMTS device dictionaries with loopback, subnets, and DHCP data
        """
        try:
            self.logger.info("Fetching CMTS devices with enriched data")
            
            # Get CMTS devices from Netshot (use cache for performance)
            cmts_devices = self.netshot.get_cmts_devices(force_refresh=False)
            
            # Filter out [NONAME] and VCAS devices
            cmts_devices = [d for d in cmts_devices 
                          if d.get('name') != '[NONAME]' 
                          and d.get('oss10_hostname') != '[NONAME]'
                          and 'VCAS' not in d.get('name', '').upper()]
            
            # Batch load DHCP data from MySQL cache (single query instead of 450+)
            from app_cache import AppCache
            import json
            cache = AppCache()
            if cache.connect():
                cursor = cache.connection.cursor()
                
                # Get all device validation cache in one query
                cursor.execute(
                    "SELECT cache_key, data FROM cache WHERE cache_type = 'device_validation'"
                )
                
                # Build lookup dict
                dhcp_cache = {}
                for row in cursor.fetchall():
                    cache_key = row['cache_key']
                    device_name = cache_key.replace('device_validation:', '')
                    data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                    dhcp_cache[device_name] = data
                
                # Apply DHCP data to devices
                for device in cmts_devices:
                    device_name = device.get('name')
                    cached_data = dhcp_cache.get(device_name)
                    
                    if cached_data:
                        # Extract DHCP subnets from cache
                        dhcp_scopes = cached_data.get('dhcp_scopes', [])
                        dhcp_ipv6_scopes = cached_data.get('dhcp_ipv6_scopes', [])
                        
                        # Convert to subnet list
                        dhcp_subnets = [s.get('scope') for s in dhcp_scopes if s.get('scope')]
                        dhcp_ipv6_subnets = [s.get('prefixname') for s in dhcp_ipv6_scopes if s.get('prefixname')]
                        
                        device['dhcp_subnets'] = dhcp_subnets + dhcp_ipv6_subnets
                    else:
                        device['dhcp_subnets'] = []
                
                cache.disconnect()
                self.logger.info(f"Loaded DHCP data for {len(dhcp_cache)} devices from cache")
            
            self.logger.info(f"Retrieved {len(cmts_devices)} CMTS devices with DHCP data")
            return cmts_devices
            
        except Exception as e:
            self.logger.error(f"Error getting CMTS devices: {e}")
            return []
    
    def get_pe_devices(self) -> List[Dict]:
        """
        Get PE devices from Netshot
        
        Returns:
            List of PE device dictionaries with loopback and subnets
        """
        try:
            self.logger.info("Fetching PE devices from Netshot")
            
            pe_devices = self.netshot.get_pe_devices()
            
            self.logger.info(f"Retrieved {len(pe_devices)} PE devices")
            return pe_devices
            
        except Exception as e:
            self.logger.error(f"Error getting PE devices: {e}")
            return []
    
    def process_vfz_devices(self) -> Dict:
        """
        Process VFZ/CMTS devices and generate XML
        
        Returns:
            Dictionary with processing results
        """
        try:
            self.logger.info("="*50)
            self.logger.info("Starting VFZ/CMTS device processing with Netshot")
            self.logger.info("="*50)
            
            # Get CMTS devices
            devices = self.get_cmts_devices()
            
            if not devices:
                self.logger.warning("No CMTS devices found")
                return {
                    'success': False,
                    'message': 'No CMTS devices found',
                    'device_count': 0
                }
            
            # Generate XML
            xml_file = self._generate_vfz_xml(devices)
            
            if xml_file:
                # Compress
                compressed_file = self._compress_xml(xml_file)
                
                result = {
                    'success': True,
                    'message': f'Successfully processed {len(devices)} CMTS devices',
                    'device_count': len(devices),
                    'xml_file': xml_file,
                    'compressed_file': compressed_file
                }
                
                self.logger.info(f"VFZ processing completed: {xml_file}")
                return result
            else:
                return {
                    'success': False,
                    'message': 'XML generation failed',
                    'device_count': len(devices)
                }
                
        except Exception as e:
            self.logger.error(f"Error processing VFZ devices: {e}")
            return {
                'success': False,
                'message': str(e),
                'device_count': 0
            }
    
    def process_pe_devices(self) -> Dict:
        """
        Process PE devices and generate XML
        
        Returns:
            Dictionary with processing results
        """
        try:
            self.logger.info("="*50)
            self.logger.info("Starting PE device processing with Netshot")
            self.logger.info("="*50)
            
            # Get PE devices
            devices = self.get_pe_devices()
            
            if not devices:
                self.logger.warning("No PE devices found")
                return {
                    'success': False,
                    'message': 'No PE devices found',
                    'device_count': 0
                }
            
            # Generate XML
            xml_file = self._generate_pe_xml(devices)
            
            if xml_file:
                # Compress
                compressed_file = self._compress_xml(xml_file)
                
                result = {
                    'success': True,
                    'message': f'Successfully processed {len(devices)} PE devices',
                    'device_count': len(devices),
                    'xml_file': xml_file,
                    'compressed_file': compressed_file
                }
                
                self.logger.info(f"PE processing completed: {xml_file}")
                return result
            else:
                return {
                    'success': False,
                    'message': 'XML generation failed',
                    'device_count': len(devices)
                }
                
        except Exception as e:
            self.logger.error(f"Error processing PE devices: {e}")
            return {
                'success': False,
                'message': str(e),
                'device_count': 0
            }
    
    def _generate_vfz_xml(self, devices: List[Dict]) -> Optional[str]:
        """
        Generate VFZ XML from Netshot device data
        
        Args:
            devices: List of CMTS devices from Netshot
            
        Returns:
            Path to generated XML file or None
        """
        try:
            # Create XML root
            root = ET.Element('EVE_LI_Targets')
            root.set('xmlns', 'http://eve.li/schema')
            
            device_count = 0
            network_count = 0
            
            for device in devices:
                hostname = device.get('name', '')
                loopback = device.get('loopback')
                subnets = device.get('subnets', [])
                
                if not hostname or not loopback:
                    self.logger.warning(f"Skipping device without hostname or loopback: {device}")
                    continue
                
                # Create device element
                device_elem = ET.SubElement(root, 'Target')
                device_elem.set('type', 'CMTS')
                
                # Add hostname
                hostname_elem = ET.SubElement(device_elem, 'Hostname')
                hostname_elem.text = hostname
                
                # Add loopback
                loopback_elem = ET.SubElement(device_elem, 'LoopbackIP')
                loopback_elem.text = loopback
                
                # Add networks
                networks_elem = ET.SubElement(device_elem, 'Networks')
                
                for subnet in subnets:
                    if self.validate_ip_address(subnet):
                        network_elem = ET.SubElement(networks_elem, 'Network')
                        network_elem.text = subnet
                        network_count += 1
                
                device_count += 1
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d')
            output_dir = Path(self.config['PATHS']['output_dir'])
            output_dir.mkdir(exist_ok=True)
            
            xml_file = output_dir / f"EVE_NL_Infra_CMTS-{timestamp}.xml"
            
            # Write XML
            tree = ET.ElementTree(root)
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            
            with open(xml_file, 'w') as f:
                f.write(xml_str)
            
            self.logger.info(f"Generated VFZ XML: {device_count} devices, {network_count} networks")
            self.logger.info(f"XML file: {xml_file}")
            
            return str(xml_file)
            
        except Exception as e:
            self.logger.error(f"Error generating VFZ XML: {e}")
            return None
    
    def _generate_pe_xml(self, devices: List[Dict]) -> Optional[str]:
        """
        Generate PE XML from Netshot device data
        
        Args:
            devices: List of PE devices from Netshot
            
        Returns:
            Path to generated XML file or None
        """
        try:
            # Create XML root
            root = ET.Element('EVE_LI_Targets')
            root.set('xmlns', 'http://eve.li/schema')
            
            device_count = 0
            network_count = 0
            
            for device in devices:
                hostname = device.get('name', '')
                loopback = device.get('loopback')
                subnets = device.get('subnets', [])
                
                if not hostname or not loopback:
                    self.logger.warning(f"Skipping device without hostname or loopback: {device}")
                    continue
                
                # Create device element
                device_elem = ET.SubElement(root, 'Target')
                device_elem.set('type', 'PE')
                
                # Add hostname
                hostname_elem = ET.SubElement(device_elem, 'Hostname')
                hostname_elem.text = hostname
                
                # Add loopback
                loopback_elem = ET.SubElement(device_elem, 'LoopbackIP')
                loopback_elem.text = loopback
                
                # Add networks
                networks_elem = ET.SubElement(device_elem, 'Networks')
                
                for subnet in subnets:
                    if self.validate_ip_address(subnet):
                        network_elem = ET.SubElement(networks_elem, 'Network')
                        network_elem.text = subnet
                        network_count += 1
                
                device_count += 1
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d')
            output_dir = Path(self.config['PATHS']['output_dir'])
            output_dir.mkdir(exist_ok=True)
            
            xml_file = output_dir / f"EVE_NL_SOHO-{timestamp}.xml"
            
            # Write XML
            tree = ET.ElementTree(root)
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            
            with open(xml_file, 'w') as f:
                f.write(xml_str)
            
            self.logger.info(f"Generated PE XML: {device_count} devices, {network_count} networks")
            self.logger.info(f"XML file: {xml_file}")
            
            return str(xml_file)
            
        except Exception as e:
            self.logger.error(f"Error generating PE XML: {e}")
            return None
    
    def _compress_xml(self, xml_file: str) -> Optional[str]:
        """Compress XML file with gzip"""
        try:
            compressed_file = f"{xml_file}.gz"
            
            with open(xml_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            self.logger.info(f"Compressed XML to {compressed_file}")
            return compressed_file
            
        except Exception as e:
            self.logger.error(f"Error compressing XML: {e}")
            return None
    
    def upload_xml_file(self, xml_file: str) -> Tuple[bool, str]:
        """
        Upload XML file to EVE LI server
        
        Args:
            xml_file: Path to XML file to upload
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if verification mode
            verification_mode = self.config['UPLOAD'].get('verification_mode', 'true').lower() == 'true'
            
            if verification_mode:
                self.logger.info(f"VERIFICATION MODE: Would upload {xml_file}")
                return (True, "Verification mode - upload simulated")
            
            # Actual upload logic here
            upload_url = self.config['UPLOAD']['api_base_url']
            username = self.config['UPLOAD']['api_username']
            password = self.config['UPLOAD']['api_password']
            
            self.logger.info(f"Uploading {xml_file} to {upload_url}")
            
            with open(xml_file, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f"{upload_url}/upload",
                    files=files,
                    auth=(username, password),
                    verify=False,
                    timeout=int(self.config['UPLOAD'].get('timeout', 600))
                )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully uploaded {xml_file}")
                return (True, "Upload successful")
            else:
                self.logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return (False, f"Upload failed: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error uploading XML: {e}")
            return (False, str(e))


def main():
    """Main entry point for V2 generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EVE LI XML Generator V2 with Netshot')
    parser.add_argument('--mode', choices=['vfz', 'pe', 'both', 'test'], 
                       default='both', help='Processing mode')
    args = parser.parse_args()
    
    # Create generator
    generator = EVEXMLGeneratorV2()
    
    if args.mode == 'test':
        print("Testing Netshot connection...")
        if generator.netshot.test_connection():
            print("✓ Netshot API connected")
        else:
            print("✗ Netshot API connection failed")
        
        print("\nTesting DHCP database...")
        if generator.dhcp.test_connection():
            print("✓ DHCP database connected")
        else:
            print("✗ DHCP database connection failed")
        
        return
    
    # Process devices
    if args.mode in ['vfz', 'both']:
        result = generator.process_vfz_devices()
        print(f"\nVFZ Processing: {result}")
    
    if args.mode in ['pe', 'both']:
        result = generator.process_pe_devices()
        print(f"\nPE Processing: {result}")


if __name__ == "__main__":
    main()
