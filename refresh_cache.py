#!/usr/bin/env python3
"""
Cache Refresh Script
====================

Pre-populates cache with Netshot device data before daily XML generation.
Designed to run as a scheduled cron job or Docker service.

This script fetches and caches:
- All production devices
- Device interfaces
- Loopback addresses
- Subnet configurations
- DHCP data (for CMTS devices)

Usage:
    python refresh_cache.py [--force] [--verbose]

Docker Usage:
    docker-compose exec app python refresh_cache.py

Author: Silvester van der Leer
Version: 1.0
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our modules
from netshot_api import get_netshot_client
from dhcp_integration import get_dhcp_integration
from cache_manager import get_cache_manager


def setup_logging(verbose: bool = False):
    """Configure logging"""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/cache_refresh.log', mode='a')
        ]
    )
    
    return logging.getLogger('cache_refresh')


def refresh_device_cache(netshot, logger, force=False):
    """
    Refresh device cache from Netshot
    
    Args:
        netshot: NetshotAPI instance
        logger: Logger instance
        force: Force refresh even if cache is valid
    
    Returns:
        Number of devices cached
    """
    logger.info("=" * 60)
    logger.info("STEP 1: Refreshing device list cache")
    logger.info("=" * 60)
    
    try:
        # Fetch all production devices (this will cache them)
        devices = netshot.get_production_devices(force_refresh=force)
        
        logger.info(f"✓ Cached {len(devices)} production devices")
        
        return len(devices)
        
    except Exception as e:
        logger.error(f"✗ Failed to cache devices: {e}")
        return 0


def refresh_device_details_cache(netshot, logger, force=False):
    """
    Refresh device details cache (interfaces, loopbacks, subnets)
    
    Args:
        netshot: NetshotAPI instance
        logger: Logger instance
        force: Force refresh even if cache is valid
    
    Returns:
        Statistics dictionary
    """
    logger.info("=" * 60)
    logger.info("STEP 2: Refreshing device details cache")
    logger.info("=" * 60)
    
    stats = {
        'devices_processed': 0,
        'interfaces_cached': 0,
        'loopbacks_cached': 0,
        'subnets_cached': 0,
        'errors': 0
    }
    
    try:
        # Get devices from cache (should be populated in step 1)
        devices = netshot.get_production_devices(force_refresh=False)
        
        if not devices:
            logger.warning("No devices found in cache")
            return stats
        
        logger.info(f"Processing {len(devices)} devices...")
        
        for i, device in enumerate(devices, 1):
            device_id = device.get('id')
            device_name = device.get('name', f'device_{device_id}')
            
            try:
                # Log progress every 10 devices
                if i % 10 == 0:
                    logger.info(f"  Progress: {i}/{len(devices)} devices...")
                
                # Cache interfaces
                interfaces = netshot.get_device_interfaces(device_id, force_refresh=force)
                if interfaces:
                    stats['interfaces_cached'] += len(interfaces)
                
                # Cache loopback
                loopback = netshot.get_loopback_interface(device_id, device_name, force_refresh=force)
                if loopback:
                    stats['loopbacks_cached'] += 1
                
                # Cache subnets
                subnets = netshot.get_device_subnets(device_id, device_name, force_refresh=force)
                if subnets:
                    stats['subnets_cached'] += len(subnets)
                
                stats['devices_processed'] += 1
                
            except Exception as e:
                logger.error(f"  Error processing device {device_name}: {e}")
                stats['errors'] += 1
                continue
        
        logger.info("✓ Device details cache refresh completed")
        logger.info(f"  - Devices processed: {stats['devices_processed']}")
        logger.info(f"  - Interfaces cached: {stats['interfaces_cached']}")
        logger.info(f"  - Loopbacks cached: {stats['loopbacks_cached']}")
        logger.info(f"  - Subnets cached: {stats['subnets_cached']}")
        if stats['errors'] > 0:
            logger.warning(f"  - Errors encountered: {stats['errors']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"✗ Failed to cache device details: {e}")
        return stats


def refresh_dhcp_cache(dhcp, logger):
    """
    Refresh DHCP data cache
    
    Args:
        dhcp: DHCPIntegration instance
        logger: Logger instance
    
    Returns:
        Number of DHCP scopes cached
    """
    logger.info("=" * 60)
    logger.info("STEP 3: Refreshing DHCP cache")
    logger.info("=" * 60)
    
    try:
        # Get DHCP scopes (this should cache them if DHCPIntegration supports caching)
        scopes = dhcp.get_dhcp_scopes()
        
        logger.info(f"✓ Retrieved {len(scopes)} DHCP scopes")
        
        return len(scopes)
        
    except Exception as e:
        logger.error(f"✗ Failed to cache DHCP data: {e}")
        return 0


def print_cache_statistics(cache_manager, logger):
    """
    Print cache statistics
    
    Args:
        cache_manager: CacheManager instance
        logger: Logger instance
    """
    logger.info("=" * 60)
    logger.info("CACHE STATISTICS")
    logger.info("=" * 60)
    
    try:
        stats = cache_manager.get_stats()
        
        logger.info(f"Cache directory: {stats.get('cache_dir')}")
        logger.info(f"Total entries: {stats.get('total_entries')}")
        logger.info(f"Valid entries: {stats.get('valid_entries')}")
        logger.info(f"Expired entries: {stats.get('expired_entries')}")
        logger.info(f"Total size: {stats.get('total_size_mb')} MB")
        
        # Cleanup expired entries
        if stats.get('expired_entries', 0) > 0:
            logger.info("Cleaning up expired cache entries...")
            removed = cache_manager.cleanup_expired()
            logger.info(f"✓ Removed {removed} expired entries")
        
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")


def main():
    """Main function"""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Refresh Netshot API cache for daily XML generation')
    parser.add_argument('--force', action='store_true', help='Force refresh, bypass existing cache')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--devices-only', action='store_true', help='Only refresh device list')
    parser.add_argument('--details-only', action='store_true', help='Only refresh device details')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Ensure logs directory exists
    Path('logs').mkdir(exist_ok=True)
    
    # Start time
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info("NETSHOT CACHE REFRESH STARTED")
    logger.info("=" * 60)
    logger.info(f"Start time: {start_time}")
    logger.info(f"Force refresh: {args.force}")
    
    try:
        # Initialize clients
        logger.info("Initializing API clients...")
        netshot = get_netshot_client()
        dhcp = get_dhcp_integration()
        cache_manager = get_cache_manager()
        
        # Check Netshot connection
        if not netshot.test_connection():
            logger.error("✗ Cannot connect to Netshot API")
            return 1
        
        logger.info("✓ Connected to Netshot API")
        
        # Step 1: Refresh device list
        if not args.details_only:
            device_count = refresh_device_cache(netshot, logger, force=args.force)
            if device_count == 0:
                logger.error("✗ No devices found, aborting")
                return 1
        
        # Step 2: Refresh device details
        if not args.devices_only:
            stats = refresh_device_details_cache(netshot, logger, force=args.force)
            if stats['devices_processed'] == 0:
                logger.warning("⚠ No device details were cached")
        
        # Step 3: Refresh DHCP cache
        if not args.devices_only and not args.details_only:
            dhcp_count = refresh_dhcp_cache(dhcp, logger)
        
        # Print statistics
        print_cache_statistics(cache_manager, logger)
        
        # End time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("CACHE REFRESH COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"End time: {end_time}")
        logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        
        return 0
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("CACHE REFRESH FAILED")
        logger.error("=" * 60)
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
