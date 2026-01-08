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
import time
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
        # Try to load from ConfigManager first, fall back to env vars
        try:
            from config_manager import get_config_manager
            config_mgr = get_config_manager()
            self.base_url = base_url or config_mgr.get_setting('netshot_url') or os.getenv('NETSHOT_API_URL', '')
            self.api_key = api_key or config_mgr.get_setting('netshot_api_key') or os.getenv('NETSHOT_API_KEY', '')
            self.pe_device_group = int(config_mgr.get_setting('netshot_pe_group') or os.getenv('NETSHOT_PE_GROUP', '275'))
            if not self.base_url:
                logging.warning("Netshot URL not configured. Please configure in application settings.")
        except Exception as e:
            logging.warning(f"Could not load from ConfigManager: {e}")
            self.base_url = base_url or os.getenv('NETSHOT_API_URL', '')
            self.api_key = api_key or os.getenv('NETSHOT_API_KEY', '')
            self.pe_device_group = int(os.getenv('NETSHOT_PE_GROUP', '275'))
        
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
        
        if self.base_url and not self.base_url.endswith('/'):
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
                     params: Dict = None, data: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """
        Make HTTP request to Netshot API with retry logic
        
        Args:
            endpoint: API endpoint (relative to base_url)
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            data: Request body data
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            Response data as dictionary or None on error
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** (attempt - 1)
                    self.logger.debug(f"Retry attempt {attempt + 1}/{max_retries} after {wait_time}s wait")
                    time.sleep(wait_time)
                
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
                
                # Try to parse as JSON first
                try:
                    return response.json()
                except ValueError:
                    # If JSON fails, return as text (for config endpoints)
                    return response.text
                
            except requests.exceptions.HTTPError as e:
                # Don't retry on 4xx errors (client errors)
                if hasattr(e.response, 'status_code') and 400 <= e.response.status_code < 500:
                    # Don't log 404 or 400 as errors - they're expected for optional configs
                    if e.response.status_code in [400, 404] and '/lawfulInterception' in url:
                        self.logger.debug(f"Optional config not available: {url}")
                    else:
                        self.logger.error(f"HTTP error calling {url}: {e}")
                        if hasattr(e.response, 'text'):
                            self.logger.error(f"Response: {e.response.text}")
                    return None
                    
                # Retry on 5xx errors (server errors)
                self.logger.warning(f"HTTP error calling {url} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    self.logger.error(f"Max retries exceeded for {url}")
                    return None
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # Retry on timeout and connection errors
                self.logger.warning(f"Connection error calling {url} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    self.logger.error(f"Max retries exceeded for {url}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error calling {url}: {e}")
                return None
            except ValueError as e:
                self.logger.error(f"JSON decode error for {url}: {e}")
                return None
        
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
    
    def _get_nokia_loopback_from_diagnostic(self, device_id: int, device_name: str = None) -> Optional[str]:
        """
        Get loopback IP from Nokia NOKIA_LI_INT diagnostic
        
        Args:
            device_id: Netshot device ID
            device_name: Device hostname (for logging)
            
        Returns:
            Loopback IP from diagnostic or None
        """
        try:
            # Get diagnostics for the device
            response = self._make_request(f'devices/{device_id}/diagnostics')
            if not response:
                return None
            
            diagnostics = response if isinstance(response, list) else []
            
            # Look for NOKIA_LI_INT diagnostic
            for diag in diagnostics:
                if diag.get('name') == 'NOKIA_LI_INT':
                    result_text = diag.get('result', '{}')
                    try:
                        import json
                        result = json.loads(result_text)
                        li_loopback = result.get('LI_LOOPBACK')
                        if li_loopback:
                            log_name = device_name or f"device {device_id}"
                            self.logger.info(f"Found Nokia LI loopback ({li_loopback}) from diagnostic for {log_name}")
                            return li_loopback
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse NOKIA_LI_INT diagnostic for device {device_id}")
                        continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting Nokia diagnostic for device {device_id}: {e}")
            return None
    
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
            # First, check if this is a Nokia device by checking diagnostics
            nokia_loopback = self._get_nokia_loopback_from_diagnostic(device_id, device_name)
            if nokia_loopback:
                # Cache and return Nokia diagnostic result
                if self.use_cache:
                    self.cache.set(cache_key, nokia_loopback)
                return nokia_loopback
            
            # Fall back to interface parsing for non-Nokia or if diagnostic not available
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
                    # Use Netshot's family field as device_type (more accurate than diagnostic vendor)
                    device['device_type'] = device.get('family', vendor or 'Unknown')
                    device['primary_subnet'] = self.get_device_primary_subnet(device_id, device.get('name'))
                    
                    # Add primary subnet to the beginning of subnets list if not already present
                    if device['primary_subnet'] and device['primary_subnet'] not in subnets:
                        subnets = [device['primary_subnet']] + subnets
                    device['subnets'] = subnets
                    
                    # Extract OSS10 hostname from comments for devices with CBR/ABR in hostname (case-insensitive)
                    device_name = device.get('name', '')
                    if 'cbr' in device_name.lower() or 'abr' in device_name.lower():
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
    
    def get_pe_devices(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get all PE (Provider Edge) devices from device group 275 with lawfulInterception config
        
        Args:
            force_refresh: Force refresh from API, bypass cache
            
        Returns:
            List of PE device dictionaries with enriched data and parsed subnets
        """
        try:
            # Check cache first
            cache_key = 'pe_devices_all'
            if not force_refresh and self.use_cache:
                cached = self.cache.get(cache_key)
                if cached:
                    self.logger.info(f"Using cached PE devices: {len(cached)} devices")
                    return cached
            
            self.logger.info(f"Fetching PE devices from Netshot group {self.pe_device_group}")
            
            # Get device list from configured group
            response = self._make_request('devices', params={'group': self.pe_device_group})
            if not response:
                self.logger.warning(f"No response from Netshot API for device group {self.pe_device_group}")
                return []
            
            device_list = response if isinstance(response, list) else []
            self.logger.info(f"Retrieved {len(device_list)} devices from group {self.pe_device_group}")
            
            # Get full details for each device
            pe_devices = []
            for device_summary in device_list:
                device_id = device_summary.get('id')
                if not device_id:
                    continue
                
                # Get full device details
                device = self._make_request(f'devices/{device_id}')
                if not device:
                    self.logger.warning(f"Could not get details for device {device_id}")
                    continue
                
                device_name = device.get('name', 'unknown')
                
                # Set device type
                device['device_type'] = device.get('family') or 'PE Router'
                
                # Get loopback interface
                device['loopback'] = self.get_loopback_interface(device_id, device_name)
                
                # Get lawfulInterception config (optional - not all PE devices have it)
                lawful_config = self.get_device_config(device_id, 'lawfulInterception')
                device['lawfulInterception'] = lawful_config
                
                # Parse subnets from lawfulInterception (if available)
                if lawful_config:
                    ipv4_subnets, ipv6_subnets = self._parse_lawful_interception(lawful_config)
                    device['subnets'] = ipv4_subnets + ipv6_subnets
                    device['ipv4_subnets'] = ipv4_subnets
                    device['ipv6_subnets'] = ipv6_subnets
                    self.logger.debug(f"{device_name}: Found {len(ipv4_subnets)} IPv4 + {len(ipv6_subnets)} IPv6 subnets")
                else:
                    # No lawfulInterception config available for this device
                    self.logger.debug(f"{device_name}: No lawfulInterception config available")
                    device['subnets'] = []
                    device['ipv4_subnets'] = []
                    device['ipv6_subnets'] = []
                
                pe_devices.append(device)
            
            # Cache the results
            if self.use_cache:
                self.cache.set(cache_key, pe_devices)
            
            self.logger.info(f"Retrieved {len(pe_devices)} PE devices with lawfulInterception data")
            return pe_devices
            
        except Exception as e:
            self.logger.error(f"Error fetching PE devices: {e}")
            return []
    
    def get_device_config(self, device_id: int, config_name: str) -> Optional[str]:
        """
        Get a specific config from a device
        
        Args:
            device_id: Netshot device ID
            config_name: Config name (e.g., 'lawfulInterception', 'runningConfig')
            
        Returns:
            Config content as string, or None if not found
        """
        try:
            # First get the device's config snapshots
            configs = self._make_request(f'devices/{device_id}/configs')
            
            if not configs or len(configs) == 0:
                self.logger.debug(f"No configs found for device {device_id}")
                return None
            
            # Sort by changeDate to get the most recent config
            sorted_configs = sorted(configs, key=lambda c: c.get('changeDate', 0), reverse=True)
            config_id = sorted_configs[0].get('id')
            
            if not config_id:
                self.logger.debug(f"No config ID found for device {device_id}")
                return None
            
            # Now fetch the specific config attribute using config ID
            endpoint = f'configs/{config_id}/{config_name}'
            response = self._make_request(endpoint)
            
            if not response:
                self.logger.debug(f"No {config_name} config for device {device_id}")
                return None
            
            # Try different response structures
            if isinstance(response, dict):
                # Try multiple possible keys
                config = (response.get('text') or 
                         response.get('config') or 
                         response.get('content') or
                         response.get('data'))
                if config:
                    return config
            elif isinstance(response, str):
                return response
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching config {config_name} for device {device_id}: {e}")
            return None
    
    def _parse_lawful_interception(self, config_text: str) -> tuple:
        """
        Parse IPv4 and IPv6 subnets from lawfulInterception config
        
        Args:
            config_text: The lawfulInterception configuration text
            
        Returns:
            Tuple of (ipv4_subnets, ipv6_subnets) lists
        """
        ipv4_subnets = []
        ipv6_subnets = []
        
        if not config_text:
            return ipv4_subnets, ipv6_subnets
        
        # IPv4 CIDR pattern
        ipv4_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})\b'
        
        # IPv6 CIDR pattern
        ipv6_pattern = r'\b([0-9a-fA-F:]+/\d{1,3})\b'
        
        # Extract IPv4 subnets
        for match in re.finditer(ipv4_pattern, config_text):
            subnet = match.group(1)
            try:
                ip, prefix = subnet.split('/')
                octets = ip.split('.')
                if len(octets) == 4 and all(0 <= int(o) <= 255 for o in octets):
                    if 0 <= int(prefix) <= 32:
                        # Only add public IPs
                        if not (ip.startswith('10.') or 
                               re.match(r'^172\.(1[6-9]|2[0-9]|3[0-1])\.', ip) or
                               ip.startswith('192.168.') or
                               ip.startswith('198.18.')):
                            if subnet not in ipv4_subnets:
                                ipv4_subnets.append(subnet)
            except:
                continue
        
        # Extract IPv6 subnets
        for match in re.finditer(ipv6_pattern, config_text):
            subnet = match.group(1)
            try:
                ip, prefix = subnet.split('/')
                if ':' in ip and 0 <= int(prefix) <= 128:
                    # Only add public IPs (exclude link-local and ULA)
                    ip_lower = ip.lower()
                    if not (ip_lower.startswith('fe80:') or
                           ip_lower.startswith('fc00:') or
                           ip_lower.startswith('fd00:')):
                        if subnet not in ipv6_subnets:
                            ipv6_subnets.append(subnet)
            except:
                continue
        
        return ipv4_subnets, ipv6_subnets
    
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
