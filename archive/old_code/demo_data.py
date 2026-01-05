#!/usr/bin/env python3
"""
Demo Data Generator
===================

Generates realistic mock data for demonstration purposes.
No real Netshot, DHCP database, or Azure AD required!

Author: Silvester van der Leer
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict


class DemoDataGenerator:
    """Generate realistic demo data for EVE LI system"""
    
    def __init__(self):
        """Initialize demo data generator"""
        self.cmts_names = [
            "cmts-amsterdam-01", "cmts-amsterdam-02", "cmts-rotterdam-01",
            "cmts-utrecht-01", "cmts-eindhoven-01", "cmts-groningen-01",
            "cmts-tilburg-01", "cmts-breda-01", "cmts-nijmegen-01"
        ]
        
        self.pe_names = [
            "pe-core-ams-01", "pe-core-ams-02", "pe-edge-rtm-01",
            "pe-edge-utr-01", "pe-border-ehv-01", "pe-agg-gro-01",
            "pe-agg-tlb-01", "pe-dist-bre-01"
        ]
        
        self.locations = [
            "Amsterdam DC1", "Amsterdam DC2", "Rotterdam DC", "Utrecht DC",
            "Eindhoven", "Groningen", "Tilburg", "Breda", "Nijmegen"
        ]
    
    def generate_cmts_devices(self) -> List[Dict]:
        """Generate demo CMTS devices"""
        devices = []
        
        # Define CMTS types
        cmts_types = [
            'Commscope E6000',
            'Commscope Evo',
            'Casa 100G',
            'Cisco cBR8',
            'Commscope E6000',
            'Casa 100G',
            'Cisco cBR8',
            'Commscope Evo',
            'Commscope E6000'
        ]
        
        # Define vendors based on device type
        cmts_vendors = [
            'Commscope',
            'Commscope',
            'Casa Systems',
            'Cisco',
            'Commscope',
            'Casa Systems',
            'Cisco',
            'Commscope',
            'Commscope'
        ]
        
        for i, name in enumerate(self.cmts_names):
            device = {
                'id': 1000 + i,
                'name': name,
                'family': 'Casa CMTS',
                'device_type': cmts_types[i],
                'vendor': cmts_vendors[i],
                'mgmtAddress': f'10.1.{i+1}.254',
                'status': 'PRODUCTION',
                'networkClass': 'CMTS',
                'location': self.locations[i],
                'contact': 'noc@example.com',
                'softwareVersion': f'8.{random.randint(1,5)}.{random.randint(1,9)}',
                'loopback': f'10.100.{i+1}.1',
                'subnets': self._generate_cmts_subnets(i),
                'dhcp_subnets': self._generate_dhcp_subnets(i),
            }
            
            # Some subnets from DHCP, some from interfaces
            device['netshot_subnets'] = device['subnets'][:2]
            
            devices.append(device)
        
        return devices
    
    def generate_pe_devices(self) -> List[Dict]:
        """Generate demo PE devices"""
        devices = []
        
        # Define PE types
        pe_types = [
            'Cisco ASR9000',
            'Nokia 7750 SR',
            'Cisco ASR9000',
            'Nokia 7750 SR',
            'Cisco ASR9000',
            'Nokia 7750 SR',
            'Cisco ASR9000',
            'Nokia 7750 SR'
        ]
        
        # Define vendors based on device type
        pe_vendors = [
            'Cisco',
            'Nokia',
            'Cisco',
            'Nokia',
            'Cisco',
            'Nokia',
            'Cisco',
            'Nokia'
        ]
        
        for i, name in enumerate(self.pe_names):
            device = {
                'id': 2000 + i,
                'name': name,
                'family': 'Cisco IOS XR',
                'device_type': pe_types[i],
                'vendor': pe_vendors[i],
                'mgmtAddress': f'10.2.{i+1}.254',
                'status': 'PRODUCTION',
                'networkClass': 'PE',
                'location': self.locations[i % len(self.locations)],
                'contact': 'noc@example.com',
                'softwareVersion': f'7.{random.randint(1,8)}.{random.randint(1,5)}',
                'loopback': f'10.200.{i+1}.1',
                'subnets': self._generate_pe_subnets(i)
            }
            
            devices.append(device)
        
        return devices
    
    def _generate_cmts_subnets(self, device_index: int) -> List[str]:
        for i, name in enumerate(self.pe_names):
            device = {
                'id': 2000 + i,
                'name': name,
                'family': 'Cisco IOS XR',
                'mgmtAddress': f'10.2.{i+1}.254',
                'status': 'PRODUCTION',
                'networkClass': 'PE',
                'location': self.locations[i % len(self.locations)],
                'contact': 'noc@example.com',
                'softwareVersion': f'7.{random.randint(1,8)}.{random.randint(1,5)}',
                'loopback': f'10.200.{i+1}.1',
                'subnets': self._generate_pe_subnets(i)
            }
            
            devices.append(device)
        
        return devices
    
    def _generate_cmts_subnets(self, device_index: int) -> List[str]:
        """Generate realistic CMTS subnets - PUBLIC ONLY for XML"""
        subnets = []
        
        # Public cable modem subnets (customer-facing)
        public_base = 80 + (device_index * 4)
        for i in range(5):
            subnets.append(f'203.{public_base+i}.0.0/22')
        
        # Additional public ranges
        for i in range(2):
            subnets.append(f'198.18.{public_base+i}.0/23')
        
        # Single public IPv6 /40 subnet per CMTS
        subnets.append(f'2a02:1{device_index:x}00::/40')
        
        return subnets
    
    def _generate_dhcp_subnets(self, device_index: int) -> List[str]:
        """Generate DHCP scopes for CMTS"""
        subnets = []
        base = 10 + (device_index * 5)
        
        # DHCP manages the cable modem subnets (IPv4)
        for i in range(4):
            subnets.append(f'172.{base+i}.0.0/22')
        
        # DHCPv6 manages the IPv6 /40 subnet
        subnets.append(f'2001:db8:{device_index:x}00::/40')
        
        return subnets
    
    def _generate_pe_subnets(self, device_index: int) -> List[str]:
        """Generate realistic PE subnets - PUBLIC ONLY for XML"""
        subnets = []
        
        # Public business customer subnets
        public_base = 100 + (device_index * 8)
        for i in range(8):
            subnets.append(f'198.51.{public_base+i}.0/24')
        
        # Additional public ranges
        for i in range(4):
            subnets.append(f'203.{public_base+10+i}.0.0/24')
        
        # Multiple public IPv6 subnets
        for i in range(3):
            subnets.append(f'2a02:2{device_index:x}{i}0::/48')
        
        return subnets
    
    def generate_dhcp_scopes(self, cmts_hostname: str = None) -> List[Dict]:
        """Generate demo DHCP scopes"""
        scopes = []
        
        devices_to_process = [cmts_hostname] if cmts_hostname else self.cmts_names
        
        for device_name in devices_to_process:
            device_index = self.cmts_names.index(device_name) if device_name in self.cmts_names else 0
            base = 10 + (device_index * 5)
            
            # Cable interface scopes
            for i in range(8):
                scope = {
                    'scope_id': (device_index * 100) + i + 1,
                    'network': f'172.{base}.{i*4}.0',
                    'netmask': '255.255.252.0',
                    'gateway': f'172.{base}.{i*4}.1',
                    'cmts': device_name,
                    'interface': f'Cable{i//2}/0/{i%2}',
                    'vlan': 1000 + (i * 10),
                    'description': f'Cable modem pool {i+1}'
                }
                scopes.append(scope)
        
        return scopes
    
    def generate_xml_files(self) -> List[Dict]:
        """Generate demo XML file list with upload status"""
        files = []
        
        # Status options (success is more common than failed)
        statuses = ['success', 'success', 'success', 'success', 'success', 'failed', 'pending']
        
        for i in range(10):
            date = datetime.now() - timedelta(days=i)
            upload_status = random.choice(statuses)
            
            # Generate response JSON based on status
            if upload_status == 'success':
                response_json = {
                    'status': 'success',
                    'message': 'XML file uploaded successfully',
                    'file_id': f'xml_{random.randint(1000, 9999)}',
                    'records_processed': random.randint(50, 200),
                    'timestamp': (date + timedelta(minutes=random.randint(2, 15))).isoformat()
                }
            elif upload_status == 'failed':
                response_json = {
                    'status': 'error',
                    'message': random.choice([
                        'Connection timeout to EVE LI server',
                        'Invalid XML format detected',
                        'Authentication failed - check credentials',
                        'Server returned 500 Internal Error'
                    ]),
                    'error_code': random.choice(['CONN_TIMEOUT', 'INVALID_XML', 'AUTH_FAILED', 'SERVER_ERROR']),
                    'timestamp': (date + timedelta(minutes=random.randint(2, 15))).isoformat()
                }
            else:  # pending
                response_json = {
                    'status': 'pending',
                    'message': 'Upload not yet attempted',
                    'timestamp': None
                }
            
            # CMTS file
            files.append({
                'name': f'EVE_NL_Infra_CMTS-{date.strftime("%Y%m%d")}.xml.gz',
                'path': f'output/EVE_NL_Infra_CMTS-{date.strftime("%Y%m%d")}.xml.gz',
                'size': random.randint(50000, 150000),
                'size_mb': round(random.uniform(0.05, 0.15), 2),
                'modified': date,
                'modified_str': date.strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'CMTS',
                'upload_status': upload_status,
                'upload_time': (date + timedelta(minutes=random.randint(2, 15))).strftime('%Y-%m-%d %H:%M:%S') if upload_status != 'pending' else 'Not uploaded',
                'response_json': json.dumps(response_json, indent=2)
            })
            
            # PE file
            upload_status = random.choice(statuses)
            if upload_status == 'success':
                response_json = {
                    'status': 'success',
                    'message': 'XML file uploaded successfully',
                    'file_id': f'xml_{random.randint(1000, 9999)}',
                    'records_processed': random.randint(30, 150),
                    'timestamp': (date + timedelta(minutes=random.randint(2, 15))).isoformat()
                }
            elif upload_status == 'failed':
                response_json = {
                    'status': 'error',
                    'message': random.choice([
                        'Connection timeout to EVE LI server',
                        'Invalid XML format detected',
                        'Authentication failed - check credentials',
                        'Server returned 500 Internal Error'
                    ]),
                    'error_code': random.choice(['CONN_TIMEOUT', 'INVALID_XML', 'AUTH_FAILED', 'SERVER_ERROR']),
                    'timestamp': (date + timedelta(minutes=random.randint(2, 15))).isoformat()
                }
            else:  # pending
                response_json = {
                    'status': 'pending',
                    'message': 'Upload not yet attempted',
                    'timestamp': None
                }
            
            files.append({
                'name': f'EVE_NL_SOHO-{date.strftime("%Y%m%d")}.xml.gz',
                'path': f'output/EVE_NL_SOHO-{date.strftime("%Y%m%d")}.xml.gz',
                'size': random.randint(30000, 80000),
                'size_mb': round(random.uniform(0.03, 0.08), 2),
                'modified': date,
                'modified_str': date.strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'PE',
                'upload_status': upload_status,
                'upload_time': (date + timedelta(minutes=random.randint(2, 15))).strftime('%Y-%m-%d %H:%M:%S') if upload_status != 'pending' else 'Not uploaded',
                'response_json': json.dumps(response_json, indent=2)
            })
        
        return sorted(files, key=lambda x: x['modified'], reverse=True)
    
    def generate_log_files(self) -> List[Dict]:
        """Generate demo log file list"""
        logs = []
        
        for i in range(5):
            date = datetime.now() - timedelta(days=i)
            logs.append({
                'name': f'eve_xml_{date.strftime("%Y%m%d")}.log',
                'path': f'logs/eve_xml_{date.strftime("%Y%m%d")}.log',
                'size': random.randint(10000, 50000),
                'modified': date.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return logs
    
    def generate_demo_user(self) -> Dict:
        """Generate demo operator user (default)"""
        return {
            'name': 'Demo Operator',
            'preferred_username': 'operator@example.com',
            'email': 'operator@example.com',
            'oid': 'demo-operator-id-12345'
        }
    
    def generate_demo_admin(self) -> Dict:
        """Generate demo admin user"""
        return {
            'name': 'Demo Admin',
            'preferred_username': 'admin@example.com',
            'email': 'admin@example.com',
            'oid': 'demo-admin-id-12345'
        }
    
    def generate_demo_viewer(self) -> Dict:
        """Generate demo viewer user"""
        return {
            'name': 'Demo Viewer',
            'preferred_username': 'viewer@example.com',
            'email': 'viewer@example.com',
            'oid': 'demo-viewer-id-12345'
        }


# Singleton instance
_demo_generator = None

def get_demo_generator() -> DemoDataGenerator:
    """Get or create demo data generator instance"""
    global _demo_generator
    if _demo_generator is None:
        _demo_generator = DemoDataGenerator()
    return _demo_generator


if __name__ == "__main__":
    """Test demo data generation"""
    print("Demo Data Generator Test\n")
    
    generator = get_demo_generator()
    
    # Test CMTS devices
    cmts = generator.generate_cmts_devices()
    print(f"✓ Generated {len(cmts)} CMTS devices")
    print(f"  Sample: {cmts[0]['name']} at {cmts[0]['location']}")
    print(f"  Loopback: {cmts[0]['loopback']}")
    print(f"  Subnets: {len(cmts[0]['subnets'])}")
    
    # Test PE devices
    pe = generator.generate_pe_devices()
    print(f"\n✓ Generated {len(pe)} PE devices")
    print(f"  Sample: {pe[0]['name']} at {pe[0]['location']}")
    print(f"  Loopback: {pe[0]['loopback']}")
    print(f"  Subnets: {len(pe[0]['subnets'])}")
    
    # Test DHCP scopes
    scopes = generator.generate_dhcp_scopes(cmts[0]['name'])
    print(f"\n✓ Generated {len(scopes)} DHCP scopes for {cmts[0]['name']}")
    print(f"  Sample: {scopes[0]['network']}/{scopes[0]['netmask']}")
    
    # Test XML files
    xml_files = generator.generate_xml_files()
    print(f"\n✓ Generated {len(xml_files)} XML file records")
    print(f"  Latest: {xml_files[0]['name']} ({xml_files[0]['size_mb']} MB)")
    
    print("\n✅ All demo data generation tests passed!")
