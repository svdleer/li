#!/usr/bin/env python3
"""
DHCP Validation Cache Warmer
Runs as background job to keep DHCP validation cache fresh
Usage: python dhcp_cache_warmer.py
Add to crontab: */15 * * * * /path/to/venv/bin/python /path/to/dhcp_cache_warmer.py
"""
import os
import sys
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netshot_api import NetshotAPI
from dhcp_integration import DHCPIntegration as DHCPDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dhcp_cache_warmer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def warm_dhcp_cache():
    """Fetch all devices and update DHCP validation cache"""
    logger.info("=== Starting DHCP cache warmer ===")
    start_time = datetime.now()
    
    try:
        # Initialize connections
        netshot_api = NetshotAPI()
        dhcp_db = DHCPDatabase()
        
        if not dhcp_db.connect():
            logger.error("Failed to connect to DHCP database")
            return False
        
        # Get all CMTS devices from Netshot
        logger.info("Fetching CMTS devices from Netshot...")
        devices = netshot_api.get_cmts_devices(force_refresh=False)  # Use cache
        logger.info(f"Found {len(devices)} CMTS devices")
        
        # Validate each device and store in cache
        validated_count = 0
        error_count = 0
        
        for device in devices:
            try:
                device_name = device.get('name')
                dhcp_hostname = device.get('oss10_hostname') or device_name
                primary = device.get('primary_subnet')
                subnets = device.get('subnets', [])
                
                # Separate IPv4 and IPv6 subnets
                ipv4_subnets = [s for s in subnets if '.' in s and ':' not in s]
                ipv6_subnets = [s for s in subnets if ':' in s]
                
                if primary and dhcp_hostname:
                    # Run validation
                    validation = dhcp_db.validate_device_dhcp(dhcp_hostname, primary, ipv4_subnets, ipv6_subnets)
                    validation['dhcp_hostname'] = dhcp_hostname
                    
                    # Save to cache
                    if dhcp_db.save_dhcp_validation(device_name, validation):
                        validated_count += 1
                        logger.debug(f"Cached validation for {device_name}: {validation.get('dhcp_scopes_count')} scopes")
                    else:
                        error_count += 1
                        logger.warning(f"Failed to cache validation for {device_name}")
                        
            except Exception as e:
                error_count += 1
                logger.error(f"Error validating {device.get('name')}: {e}")
        
        dhcp_db.disconnect()
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== Cache warming complete ===")
        logger.info(f"Validated: {validated_count}, Errors: {error_count}, Duration: {duration:.1f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"Cache warmer failed: {e}")
        return False


if __name__ == '__main__':
    success = warm_dhcp_cache()
    sys.exit(0 if success else 1)
