#!/usr/bin/env python3
"""
Background Cache Warmer Job
============================
Refreshes device validation cache in MySQL

Run via cron every 15 minutes:
*/15 * * * * cd /path/to/li && ./venv/bin/python cache_warmer.py >> logs/cache_warmer.log 2>&1

Author: Silvester van der Leer
Version: 1.0
"""

import os
import sys
import logging
from datetime import datetime
from netshot_api import NetshotAPI
from dhcp_integration import DHCPIntegration as DHCPDatabase
from app_cache import AppCache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def warm_device_validation_cache():
    """Fetch all CMTS devices and validate DHCP, store in MySQL cache"""
    logger.info("=" * 60)
    logger.info("Starting cache warmer job")
    
    start_time = datetime.now()
    cmts_success = 0
    cmts_errors = 0
    pe_success = 0
    pe_errors = 0
    
    try:
        # Initialize connections
        netshot_api = NetshotAPI(use_cache=True)  # Use file cache for Netshot data
        dhcp_db = DHCPDatabase()
        app_cache = AppCache()
        
        if not dhcp_db.connect():
            logger.error("Failed to connect to DHCP database")
            return
        
        if not app_cache.connect():
            logger.error("Failed to connect to app cache database")
            dhcp_db.disconnect()
            return
        
        # Get all CMTS devices
        logger.info("Fetching CMTS devices from Netshot...")
        devices = netshot_api.get_cmts_devices(force_refresh=False)
        logger.info(f"Found {len(devices)} CMTS devices")
        
        # Process each device
        for idx, device in enumerate(devices, 1):
            device_name = device.get('name')
            device_id = device.get('id')
            
            if not device_name:
                continue
            
            try:
                # Use OSS10 hostname if available
                dhcp_hostname = device.get('oss10_hostname') or device_name
                primary = device.get('primary_subnet')
                subnets = device.get('subnets', [])
                
                # Separate IPv4 and IPv6 subnets, filter only PUBLIC ones
                from subnet_utils import is_public_ipv4, is_public_ipv6
                ipv4_subnets = [s for s in subnets if '.' in s and ':' not in s and is_public_ipv4(s.split('/')[0])]
                ipv6_subnets = [s for s in subnets if ':' in s and is_public_ipv6(s.split('/')[0])]
                
                if primary and dhcp_hostname:
                    # Validate DHCP
                    validation = dhcp_db.validate_device_dhcp(
                        dhcp_hostname, primary, ipv4_subnets, ipv6_subnets
                    )
                    validation['dhcp_hostname'] = dhcp_hostname
                    
                    # Store in MySQL cache (24 hour TTL)
                    app_cache.set(
                        cache_key=f'device_validation:{device_name}',
                        cache_type='device_validation',
                        data=validation,
                        ttl_seconds=86400
                    )
                    
                    cmts_success += 1
                    logger.info(
                        f"[{idx}/{len(devices)}] {device_name}: "
                        f"DHCP={'✓' if validation.get('has_dhcp') else '✗'} "
                        f"({validation.get('dhcp_scopes_count', 0)} scopes)"
                    )
                else:
                    logger.warning(f"[{idx}/{len(devices)}] {device_name}: Missing primary subnet or hostname")
                    
            except Exception as e:
                cmts_errors += 1
                logger.error(f"[{idx}/{len(devices)}] {device_name}: Error - {e}")
        
        # Get and cache PE devices
        logger.info("\nFetching PE devices from Netshot...")
        pe_devices = netshot_api.get_pe_devices(force_refresh=False)
        logger.info(f"Found {len(pe_devices)} PE devices")
        
        # Process each PE device
        for idx, device in enumerate(pe_devices, 1):
            device_name = device.get('name')
            
            if not device_name:
                continue
            
            try:
                # Store PE device data in MySQL cache
                pe_data = {
                    'device_name': device_name,
                    'device_id': device.get('id'),
                    'device_type': device.get('device_type'),
                    'loopback': device.get('loopback'),
                    'ipv4_subnets': device.get('ipv4_subnets', []),
                    'ipv6_subnets': device.get('ipv6_subnets', []),
                    'total_subnets': len(device.get('subnets', []))
                }
                
                # Store in MySQL cache (24 hour TTL)
                app_cache.set(
                    cache_key=f'pe_device:{device_name}',
                    cache_type='pe_device',
                    data=pe_data,
                    ttl_seconds=86400
                )
                
                pe_success += 1
                logger.info(
                    f"[{idx}/{len(pe_devices)}] {device_name}: "
                    f"{pe_data['total_subnets']} subnets "
                    f"({len(pe_data['ipv4_subnets'])} IPv4 + {len(pe_data['ipv6_subnets'])} IPv6)"
                )
                
            except Exception as e:
                pe_errors += 1
                logger.error(f"[{idx}/{len(pe_devices)}] {device_name}: Error - {e}")
        
        # Cleanup expired cache entries
        logger.info("Cleaning up expired cache entries...")
        app_cache.cleanup_expired()
        
        # Close connections
        dhcp_db.disconnect()
        app_cache.disconnect()
        
        # Summary
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"Cache warmer completed in {duration:.1f}s")
        logger.info(f"CMTS devices - Success: {cmts_success}, Errors: {cmts_errors}")
        logger.info(f"PE devices   - Success: {pe_success}, Errors: {pe_errors}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error in cache warmer: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    warm_device_validation_cache()
