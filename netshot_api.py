#!/usr/bin/env python3
"""
Netshot API Integration Module
================================

Handles all interactions with Netshot REST API:
- Get devices with "IN PRODUCTION" status
- Get loopback interfaces from devices
- Get subnets from devices
- Caching support for performance optimization

Author: Silvester van der Leer
Version: 2.1
"""

import ipaddress
import os
import logging
import json
import re
import requests
from typing import List, Dict, Optional
from requests.auth import HTTPBasicAuth
import urllib3

# Import cache manager
from cache_manager import CacheManager, get_cache_manager

# Disable SSL warnings for internal APIs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NetshotAPI:
    """Client for Netshot REST API with caching support"""
    
    def __init__(self, base_url: str = None, username: str = None, password: str = None,
                 api_key: str = None, timeout: int = 30, verify_ssl: bool = False, 
                 use_cache: bool = True, cache_ttl: int = None):
        """
        Initialize Netshot API client
        
        Args:
            base_url: Netshot API base URL (e.g., https://netshot.domain.com/api)
            username: API username (for Basic Auth)
            password: API password (for Basic Auth)
            api_key: API key (for Token Auth, alternative to username/password)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            use_cache: Enable caching (default: True)
            cache_ttl: Cache TTL in seconds (default: from env or 24 hours)
        """
        self.base_url = base_url or os.getenv('NETSHOT_API_URL', 'https://netshot.local/api')
        self.api_key = api_key or os.getenv('NETSHOT_API_KEY', '')
        self.username = username or os.getenv('NETSHOT_USERNAME', '')
        self.password = password or os.getenv('NETSHOT_PASSWORD', '')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.logger = logging.getLogger('netshot_api')
        
        # Initialize cache
        self.use_cache = use_cache and os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
        if self.use_cache:
            cache_dir = os.getenv('CACHE_DIR', '.cache')
            ttl = cache_ttl or int(os.getenv('CACHE_TTL', '86400'))  # 24 hours default
            self.cache = CacheManager(cache_dir=cache_dir, default_ttl=ttl)
            self.logger.info(f"Caching enabled: TTL={ttl}s, dir={cache_dir}")
        else:
            self.cache = None
            self.logger.info("Caching disabled")
        
        if not self.base_url.endswith('/'):
            self.base_url += '/'
    
    def _extract_oss10_from_comments(self, comments: str) -> Optional[str]:
        """
        Extract OSS10 hostname from device comments
        
        Args:
            comments: Device comments string
            
        Returns:
            OSS10 hostname if found, None otherwise
        """
        if not comments:
            return None
            
        # Look for OSS10: pattern in comments
        match = re.search(r'OSS10[:\s]+([^\s,;]+)', comments, re.IGNORECASE)
        if match:
            oss10_name = match.group(1).strip()
            self.logger.debug(f"Found OSS10 hostname: {oss10_name}")
            return oss10_name
        
        return None
    
    def _make_request(self, endpoint: str, method: str = 'GET', 
                     params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """
        Make HTTP request to Netshot API
        
        Args:
            endpoint: API endpoint (relative to base_url)
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            data: Request body data
            
        Returns:
            Response data as dictionary or None on error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            
            # Prepare headers and authentication
            headers = {}
            auth = None
            
            if self.api_key:
                # Use API key authentication (Bearer token or X-API-Key header)
                headers['X-Netshot-API-Token'] = self.api_key
            elif self.username and self.password:
                # Use Basic authentication
                auth = HTTPBasicAuth(self.username, self.password)
            
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                auth=auth,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            response.raise_for_status()
            
            if response.status_code == 204:  # No content
                return {}
                
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error calling {url}: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Response: {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error calling {url}: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"JSON decode error for {url}: {e}")
            return None
    
    def _normalize_subnet(self, subnet_str: str) -> str:
        """
        Normalize subnet from host IP to network address
        Example: 10.254.216.1/24 -> 10.254.216.0/24
        
        Args:
            subnet_str: Subnet string in CIDR format
            
        Returns:
            Normalized subnet with network address
        """
        try:
            network = ipaddress.ip_network(subnet_str, strict=False)
            return str(network)
        except Exception as e:
            self.logger.warning(f"Failed to normalize subnet {subnet_str}: {e}")
            return subnet_str
    
    def test_connection(self) -> bool:
        """
        Test API connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Testing Netshot API connection to {self.base_url}")
            response = self._make_request('devices', params={'limit': 1})
            
            if response is not None:
                self.logger.info("Netshot API connection successful")
                return True
            else:
                self.logger.error("Netshot API connection failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Netshot API connection test failed: {e}")
            return False
    
    def get_production_devices(self, device_family: str = None, force_refresh: bool = False) -> List[Dict]:
        """
        Get all devices with "IN PRODUCTION" status from Netshot
        
        Args:
            device_family: Optional filter by device family (e.g., 'Cisco IOS', 'Casa CMTS')
            force_refresh: Force refresh from API, bypass cache
            
        Returns:
            List of device dictionaries with keys:
            - id: Device ID
            - name: Device hostname
            - family: Device family
            - mgmtAddress: Management IP address
            - status: Device status
            - loopback: Loopback interface (if available)
        """
        # Check cache first
        cache_key = f"production_devices_{device_family or 'all'}"
        if self.use_cache and not force_refresh:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self.logger.info(f"Retrieved {len(cached_data)} devices from cache")
                return cached_data
        
        try:
            self.logger.info("Fetching devices with IN PRODUCTION status from Netshot")
            
            # Netshot API endpoint for devices
            response = self._make_request('devices')
            
            if response is None:
                self.logger.error("Failed to fetch devices from Netshot")
                return []
            
            devices = response if isinstance(response, list) else response.get('devices', [])
            
            # Filter for "IN PRODUCTION" status
            production_devices = []
            for device in devices:
                status = device.get('status', '').upper()
                
                # Check if device is in production
                if 'PRODUCTION' in status or status == 'ENABLED' or status == 'ACTIVE':
                    # Optional family filter
                    if device_family and device.get('family', '') != device_family:
                        continue
                    
                    production_devices.append({
                        'id': device.get('id'),
                        'name': device.get('name', ''),
                        'family': device.get('family', ''),
                        'mgmtAddress': device.get('mgmtAddress', ''),
                        'status': device.get('status', ''),
                        'networkClass': device.get('networkClass', ''),
                        'location': device.get('location', ''),
                        'contact': device.get('contact', ''),
                        'softwareVersion': device.get('softwareVersion', '')
                    })
            
            self.logger.info(f"Found {len(production_devices)} devices in production")
            
            # Cache the result
            if self.use_cache:
                self.cache.set(cache_key, production_devices)
                self.logger.debug(f"Cached {len(production_devices)} devices")
            
            return production_devices
            
        except Exception as e:
            self.logger.error(f"Error fetching production devices: {e}")
            return []
    
    def get_device_interfaces(self, device_id: int, force_refresh: bool = False) -> List[Dict]:
        """
        Get all interfaces for a specific device
        
        Args:
            device_id: Netshot device ID
            force_refresh: Force refresh from API, bypass cache
            
        Returns:
            List of interface dictionaries
        """
        # Check cache first
        cache_key = f"device_interfaces_{device_id}"
        if self.use_cache and not force_refresh:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self.logger.debug(f"Retrieved interfaces for device {device_id} from cache")
                return cached_data
        
        try:
            self.logger.debug(f"Fetching interfaces for device ID {device_id}")
            
            response = self._make_request(f'devices/{device_id}/interfaces')
            
            if response is None:
                return []
            
            interfaces = response if isinstance(response, list) else response.get('interfaces', [])
            
            # Cache the result
            if self.use_cache:
                self.cache.set(cache_key, interfaces)
                self.logger.debug(f"Cached {len(interfaces)} interfaces for device {device_id}")
            
            return interfaces
            
        except Exception as e:
            self.logger.error(f"Error fetching interfaces for device {device_id}: {e}")
            return []
    
    def get_loopback_interface(self, device_id: int, device_name: str = None, force_refresh: bool = False) -> Optional[str]:
        """
        Get the loopback interface IP address for a device
        
        Args:
            device_id: Netshot device ID
            device_name: Device hostname (for logging)
            force_refresh: Force refresh from API, bypass cache
            
        Returns:
            Loopback IP address or None if not found
        """
        # Check cache first
        cache_key = f"device_loopback_{device_id}"
        if self.use_cache and not force_refresh:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self.logger.debug(f"Retrieved loopback for device {device_id} from cache")
                return cached_data
        
        try:
            interfaces = self.get_device_interfaces(device_id, force_refresh=force_refresh)
            
            # Determine if this is a Casa device (loopback 7) or standard device
            is_casa = device_name and any(x in device_name.upper() for x in ['CCAP1', 'CBR']) if device_name else False
            
            # Look for loopback interface - priority: 213.51.x.x > preferred number > any
            correct_loopback = None  # 213.51.x.x address
            preferred_loopback = None  # Preferred loopback number (7 for Casa, 0 for others)
            fallback_loopback = None  # Any loopback if nothing else found
            
            for interface in interfaces:
                interface_name = (interface.get('interfaceName') or interface.get('name', '')).lower()
                
                # Check if this is a loopback interface
                if not any(name in interface_name for name in ['loopback', 'lo0', 'lo ']):
                    continue
                
                # Get IP address from ip4Addresses array (primary method)
                ip_address = None
                if 'ip4Addresses' in interface:
                    ip4_addresses = interface.get('ip4Addresses', [])
                    if ip4_addresses and len(ip4_addresses) > 0:
                        ip_address = ip4_addresses[0].get('ip')
                
                # Fallback to ipAddress or ip fields
                if not ip_address:
                    ip_address = interface.get('ipAddress') or interface.get('ip')
                
                if ip_address:
                    # Clean up IP address (remove subnet mask if present)
                    ip_address = ip_address.split('/')[0]
                    
                    # Priority 1: Check if this is a 213.51.x.x address (correct loopback)
                    if ip_address.startswith('213.51.'):
                        correct_loopback = ip_address
                        log_name = device_name or f"device {device_id}"
                        self.logger.debug(f"Found correct loopback ({ip_address}) for {log_name}")
                        # Don't return yet, check all interfaces in case there's a preferred one with 213.51
                    
                    # Priority 2: Check if this is the preferred loopback number
                    if is_casa:
                        # Casa devices: prefer loopback 7
                        if 'loopback7' in interface_name.replace(' ', '') or 'loopback 7' in interface_name:
                            if ip_address.startswith('213.51.'):
                                # Perfect match: loopback 7 with correct IP
                                if self.use_cache:
                                    self.cache.set(cache_key, ip_address)
                                return ip_address
                            elif not preferred_loopback:
                                preferred_loopback = ip_address
                    else:
                        # Standard devices: prefer loopback0
                        if 'loopback0' in interface_name.replace(' ', '') or 'loopback 0' in interface_name or 'lo0' in interface_name:
                            if ip_address.startswith('213.51.'):
                                # Perfect match: loopback 0 with correct IP
                                if self.use_cache:
                                    self.cache.set(cache_key, ip_address)
                                return ip_address
                            elif not preferred_loopback:
                                preferred_loopback = ip_address
                    
                    # Priority 3: Store as fallback (any loopback)
                    if not fallback_loopback:
                        fallback_loopback = ip_address
            
            # Return best available loopback in priority order
            result = correct_loopback or preferred_loopback or fallback_loopback
            if result:
                log_name = device_name or f"device {device_id}"
                self.logger.debug(f"Found loopback ({result}) for {log_name}")
                
                # Cache the result
                if self.use_cache:
                    self.cache.set(cache_key, result)
                
                return result
            
            log_name = device_name or f"device {device_id}"
            self.logger.debug(f"No loopback interface found for {log_name}")
            
            # Cache None result to avoid repeated lookups
            if self.use_cache:
                self.cache.set(cache_key, None, ttl=3600)  # Cache for 1 hour
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching loopback for device {device_id}: {e}")
            return None
    
    def get_device_subnets(self, device_id: int, device_name: str = None, force_refresh: bool = False) -> tuple:
        """
        Get all public subnets and vendor from CMTS_LI_SUBNETS diagnostic result
        
        Args:
            device_id: Netshot device ID
            device_name: Device hostname (for logging)
            force_refresh: Force refresh from API, bypass cache
            
        Returns:
            Tuple of (subnets_list, vendor_string)
        """
        # Check cache first
        cache_key = f"device_subnets_{device_id}"
        if self.use_cache and not force_refresh:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self.logger.debug(f"Retrieved subnets for device {device_id} from cache")
                return cached_data
        
        vendor = 'Unknown'
        try:
            # Fetch diagnostic results from Netshot
            self.logger.debug(f"Fetching diagnostic results for device ID {device_id}")
            response = self._make_request(f'devices/{device_id}/diagnosticresults')
            
            if response is None:
                log_name = device_name or f"device {device_id}"
                self.logger.warning(f"No diagnostic results returned for {log_name}\"")
                return ([], vendor)
            
            # Find CMTS_LI_SUBNETS diagnostic
            subnets = []
            diagnostics = response if isinstance(response, list) else [response]
            found_diagnostic = False
            
            for diag in diagnostics:
                # Check if this is the CMTS_LI_SUBNETS diagnostic
                diag_name = diag.get('diagnosticName', '')
                if diag_name == 'CMTS_LI_SUBNETS':
                    found_diagnostic = True
                    # Parse the result text (should be JSON)
                    result_text = diag.get('text', '{}')
                    try:
                        result_data = json.loads(result_text) if isinstance(result_text, str) else result_text
                        
                        # Extract vendor
                        vendor = result_data.get('vendor', 'Unknown')
                        if vendor == 'Cisco IOS/IOS-XE':
                            vendor = 'Cisco cBR8'
                        
                        # Extract IPv4 subnets and normalize them
                        ipv4_subnets = result_data.get('ipv4_subnets', [])
                        subnets.extend([self._normalize_subnet(s) for s in ipv4_subnets])
                        
                        # Extract IPv6 subnets and normalize them
                        ipv6_subnets = result_data.get('ipv6_subnets', [])
                        subnets.extend([self._normalize_subnet(s) for s in ipv6_subnets])
                        
                        log_name = device_name or f"device {device_id}"
                        if subnets:
                            self.logger.info(f"Found {len(subnets)} subnets from CMTS_LI_SUBNETS diagnostic for {log_name}")
                        else:
                            self.logger.warning(f"CMTS_LI_SUBNETS diagnostic exists but returned no subnets for {log_name}")
                        break
                        
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse CMTS_LI_SUBNETS diagnostic for device {device_id}: {e}")
            
            # Warn if diagnostic not found
            if not found_diagnostic:
                log_name = device_name or f"device {device_id}"
                self.logger.warning(f"CMTS_LI_SUBNETS diagnostic not found for {log_name} (found {len(diagnostics)} other diagnostics)")
            
            # Cache the result
            result = (subnets, vendor)
            if self.use_cache:
                self.cache.set(cache_key, result)
                self.logger.debug(f"Cached {len(subnets)} subnets and vendor for device {device_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching subnets for device {device_id}: {e}")
            return ([], 'Unknown')
    
    def get_device_primary_subnet(self, device_id: int, device_name: str = None) -> str:
        """
        Get primary subnet from CMTS_LI_SUBNETS diagnostic result
        
        Args:
            device_id: Netshot device ID
            device_name: Device hostname (for logging)
            
        Returns:
            Primary subnet string or None
        """
        try:
            # Fetch diagnostic results from Netshot
            response = self._make_request(f'devices/{device_id}/diagnosticresults')
            
            if response is None:
                return None
            
            # Find CMTS_LI_SUBNETS diagnostic
            diagnostics = response if isinstance(response, list) else [response]
            
            for diag in diagnostics:
                diag_name = diag.get('diagnosticName', '')
                if diag_name == 'CMTS_LI_SUBNETS':
                    result_text = diag.get('text', '{}')
                    try:
                        result_data = json.loads(result_text) if isinstance(result_text, str) else result_text
                        primary_subnet = result_data.get('primary_subnet')
                        return self._normalize_subnet(primary_subnet) if primary_subnet else None
                    except json.JSONDecodeError:
                        return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching primary subnet for device {device_id}: {e}")
            return None
    
    def get_cmts_devices(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get all CMTS devices from Netshot group 207
        
        Args:
            force_refresh: Force refresh from API, bypass cache
        
        Returns:
            List of CMTS device dictionaries with enriched data
        """
        # Check cache first
        cache_key = "cmts_devices_207"
        if self.use_cache and not force_refresh:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self.logger.debug("Retrieved CMTS devices from cache")
                return cached_data
        
        try:
            self.logger.info("Fetching CMTS devices from Netshot group 207")
            
            # Fetch devices from group 207
            response = self._make_request('devices', params={'group': 207})
            
            if response is None:
                return []
            
            # Extract devices list
            devices = response if isinstance(response, list) else response.get('devices', [])
            
            # Enrich device data with loopback and subnets (INPRODUCTION only)
            cmts_devices = []
            for device in devices:
                # Skip non-production devices
                if device.get('status') != 'INPRODUCTION':
                    continue
                    
                device_id = device.get('id')
                if device_id:
                    device['loopback'] = self.get_loopback_interface(device_id, device.get('name'), force_refresh)
                    subnets, vendor = self.get_device_subnets(device_id, device.get('name'), force_refresh)
                    device['subnets'] = subnets
                    device['device_type'] = vendor
                    device['primary_subnet'] = self.get_device_primary_subnet(device_id, device.get('name'))
                    
                    # Extract OSS10 hostname from comments only for devices with CBR in hostname
                    device_name = device.get('name', '')
                    if 'CBR' in device_name.upper():
                        # Fetch full device details to get comments field
                        full_device = self._make_request(f'devices/{device_id}')
                        if full_device and 'comments' in full_device:
                            device['comments'] = full_device['comments']
                            device['oss10_hostname'] = self._extract_oss10_from_comments(full_device['comments'])
                        else:
                            device['oss10_hostname'] = None
                    else:
                        device['oss10_hostname'] = None
                    
                    cmts_devices.append(device)
            
            self.logger.info(f"Found {len(cmts_devices)} CMTS devices in group 207")
            
            # Cache the result
            if self.use_cache:
                self.cache.set(cache_key, cmts_devices)
                self.logger.debug(f"Cached {len(cmts_devices)} CMTS devices")
            
            return cmts_devices
            
        except Exception as e:
            self.logger.error(f"Error fetching CMTS devices from group 207: {e}")
            return []
    
    def get_pe_devices(self) -> List[Dict]:
        """
        Get all PE (Provider Edge) devices in production
        
        Returns:
            List of PE device dictionaries with enriched data
        """
        try:
            self.logger.info("Fetching PE devices from Netshot")
            
            # Get all production devices
            all_devices = self.get_production_devices()
            
            # Filter for PE/router devices
            pe_devices = []
            for device in all_devices:
                family = device.get('family', '').lower()
                name = device.get('name', '').lower()
                network_class = device.get('networkClass', '').lower()
                
                # Identify PE devices by family, class, or naming convention
                is_pe = (
                    'router' in family or
                    'pe' in name or
                    'edge' in network_class or
                    network_class == 'pe'
                )
                
                # Exclude CMTS devices
                is_cmts = 'cmts' in family or 'casa' in family or 'cmts' in name
                
                if is_pe and not is_cmts:
                    # Enrich device data with loopback and subnets
                    device_id = device.get('id')
                    device['loopback'] = self.get_loopback_interface(device_id, device.get('name'))
                    device['subnets'] = self.get_device_subnets(device_id, device.get('name'))
                    
                    pe_devices.append(device)
            
            self.logger.info(f"Found {len(pe_devices)} PE devices")
            return pe_devices
            
        except Exception as e:
            self.logger.error(f"Error fetching PE devices: {e}")
            return []
    
    def get_device_diagnostic(self, device_id: int, diagnostic_name: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Get a specific diagnostic result from a device
        
        Args:
            device_id: Netshot device ID
            diagnostic_name: Name of the diagnostic (e.g., 'CMTS_LI_SUBNETS')
            force_refresh: Force refresh from API, bypass cache
            
        Returns:
            Diagnostic data as dictionary or None if not found
        """
        # Check cache first
        cache_key = f"device_diagnostic_{device_id}_{diagnostic_name}"
        if self.use_cache and not force_refresh:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self.logger.debug(f"Retrieved diagnostic '{diagnostic_name}' for device {device_id} from cache")
                return cached_data
        
        try:
            self.logger.debug(f"Fetching diagnostic '{diagnostic_name}' for device ID {device_id}")
            
            # Get all diagnostics for the device
            response = self._make_request(f'devices/{device_id}/diagnostics')
            
            if response is None:
                return None
            
            diagnostics = response if isinstance(response, list) else response.get('diagnostics', [])
            
            # Find the specific diagnostic
            for diagnostic in diagnostics:
                if diagnostic.get('diagnosticName') == diagnostic_name:
                    # Parse JSON text if present
                    result = diagnostic
                    if diagnostic.get('type') == 'TEXT' and 'text' in diagnostic:
                        try:
                            import json
                            result['parsed_data'] = json.loads(diagnostic['text'])
                        except json.JSONDecodeError:
                            self.logger.warning(f"Could not parse diagnostic text as JSON")
                    
                    # Cache the result
                    if self.use_cache:
                        self.cache.set(cache_key, result)
                        self.logger.debug(f"Cached diagnostic '{diagnostic_name}' for device {device_id}")
                    
                    return result
            
            self.logger.warning(f"Diagnostic '{diagnostic_name}' not found for device {device_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching diagnostic for device {device_id}: {e}")
            return None
    
    def get_cmts_li_subnets(self, device_id: int, force_refresh: bool = False) -> Dict:
        """
        Get CMTS LI subnets diagnostic data
        
        Args:
            device_id: Netshot device ID
            force_refresh: Force refresh from API, bypass cache
            
        Returns:
            Dictionary with subnet data:
            {
                'device_name': str,
                'vendor': str,
                'interface': str,
                'found': bool,
                'ipv4_subnets': list,
                'ipv6_subnets': list
            }
        """
        diagnostic = self.get_device_diagnostic(device_id, 'CMTS_LI_SUBNETS', force_refresh)
        
        if diagnostic and 'parsed_data' in diagnostic:
            return diagnostic['parsed_data']
        
        # Return empty result if not found
        return {
            'device_name': 'unknown',
            'vendor': 'unknown',
            'interface': 'unknown',
            'found': False,
            'ipv4_subnets': [],
            'ipv6_subnets': []
        }


# Convenience functions for direct use
def get_netshot_client() -> NetshotAPI:
    """Create and return a configured Netshot API client"""
    return NetshotAPI()


if __name__ == "__main__":
    # Test the Netshot API connection
    logging.basicConfig(level=logging.DEBUG)
    
    client = get_netshot_client()
    
    if client.test_connection():
        print("✓ Netshot API connection successful")
        
        # Test fetching devices
        devices = client.get_production_devices()
        print(f"✓ Found {len(devices)} production devices")
        
        if devices:
            print(f"\nSample device: {devices[0].get('name')}")
            
            # Test loopback and subnet fetching
            device_id = devices[0].get('id')
            loopback = client.get_loopback_interface(device_id)
            subnets = client.get_device_subnets(device_id)
            
            print(f"  Loopback: {loopback}")
            print(f"  Subnets: {len(subnets)} found")
    else:
        print("✗ Netshot API connection failed")
