"""
DHCP Database Interface
Connects to MariaDB/MySQL database to validate DHCP scopes against Netshot data
"""
import os
import re
import logging
import pymysql

logger = logging.getLogger(__name__)


def is_public_ipv4(subnet_str):
    """Check if subnet is public (not RFC1918 or test ranges)"""
    try:
        # Extract IP from CIDR notation
        ip = subnet_str.split('/')[0]
        return not (ip.startswith('10.') or 
                    re.match(r'^172\.(1[6-9]|2[0-9]|3[0-1])\.', ip) or
                    ip.startswith('192.168.') or
                    ip.startswith('198.18.'))
    except:
        return True  # If parsing fails, assume public


class DHCPDatabase:
    """Interface to DHCP MariaDB database"""
    
    def __init__(self):
        # Load settings from ConfigManager
        try:
            from config_manager import get_config_manager
            config_mgr = get_config_manager()
            # DHCP database connection (for scope data)
            self.host = config_mgr.get_setting('mysql_host') or os.getenv('MYSQL_HOST', 'localhost')
            self.port = int(config_mgr.get_setting('mysql_port') or os.getenv('MYSQL_PORT', '3306'))
            self.database = config_mgr.get_setting('mysql_database') or 'access'
            self.user = config_mgr.get_setting('mysql_user') or os.getenv('MYSQL_USER', 'access')
            self.password = config_mgr.get_setting('mysql_password') or os.getenv('MYSQL_PASSWORD', '')
            # Separate cache database connection (for cache tables)
            self.cache_host = config_mgr.get_setting('cache_host') or os.getenv('CACHE_HOST', 'localhost')
            self.cache_port = int(config_mgr.get_setting('cache_port') or os.getenv('CACHE_PORT', '3306'))
            self.cache_user = config_mgr.get_setting('cache_user') or os.getenv('CACHE_USER', 'access')
            self.cache_password = config_mgr.get_setting('cache_password') or os.getenv('CACHE_PASSWORD', '')
            self.cache_database = config_mgr.get_setting('cache_database') or 'li_xml'
        except Exception as e:
            logger.warning(f"Could not load from ConfigManager, using environment: {e}")
            self.host = os.getenv('MYSQL_HOST', 'localhost')
            self.port = int(os.getenv('MYSQL_PORT', '3306'))
            self.database = 'access'
            self.user = os.getenv('MYSQL_USER', 'access')
            self.password = os.getenv('MYSQL_PASSWORD', '')
            self.cache_host = os.getenv('CACHE_HOST', 'localhost')
            self.cache_port = int(os.getenv('CACHE_PORT', '3306'))
            self.cache_user = os.getenv('CACHE_USER', 'access')
            self.cache_password = os.getenv('CACHE_PASSWORD', '')
            self.cache_database = 'li_xml'
        
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=3  # Add 3 second timeout
            )
            logger.info(f"Connected to DHCP database at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to DHCP database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("DHCP database connection closed")
    
    def get_scopes_by_primary(self, primary_subnet):
        """
        Get all DHCP scopes that match a primary subnet
        
        Args:
            primary_subnet: Primary subnet in CIDR format (e.g., "10.254.216.1/24")
        
        Returns:
            List of scope dictionaries
        """
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            with self.connection.cursor() as cursor:
                query = """
                    SELECT scope, primscope, class, disabled, total, freeleases, 
                           leases, freeother, cnrid
                    FROM scopesnew 
                    WHERE primscope = %s
                    ORDER BY scope
                """
                cursor.execute(query, (primary_subnet,))
                results = cursor.fetchall()
                logger.debug(f"Found {len(results)} DHCP scopes for primary subnet {primary_subnet}")
                return results
        except Exception as e:
            logger.error(f"Error querying DHCP scopes: {e}")
            return []
    
    def get_ipv6_scopes_by_hostname(self, hostname):
        """
        Get all DHCPv6 scopes for a specific hostname
        
        Args:
            hostname: Device hostname
        
        Returns:
            List of IPv6 scope dictionaries
        """
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            with self.connection.cursor() as cursor:
                query = """
                    SELECT prefixname, hostname, leased, dynamic, cnrid
                    FROM ipv6scopesnew 
                    WHERE hostname = %s
                    ORDER BY prefixname
                """
                cursor.execute(query, (hostname,))
                results = cursor.fetchall()
                logger.debug(f"Found {len(results)} DHCPv6 scopes for hostname {hostname}")
                return results
        except Exception as e:
            logger.error(f"Error querying DHCPv6 scopes: {e}")
            return []
    
    def get_all_primary_scopes(self):
        """
        Get all unique primary scopes from the database
        
        Returns:
            Set of primary subnet strings
        """
        if not self.connection:
            if not self.connect():
                return set()
        
        try:
            with self.connection.cursor() as cursor:
                query = "SELECT DISTINCT primscope FROM scopesnew"
                cursor.execute(query)
                results = cursor.fetchall()
                primary_scopes = {row['primscope'] for row in results}
                logger.debug(f"Found {len(primary_scopes)} unique primary scopes in DHCP database")
                return primary_scopes
        except Exception as e:
            logger.error(f"Error querying primary scopes: {e}")
            return set()
    
    def validate_device_dhcp(self, device_name, primary_subnet, public_ipv4_subnets, public_ipv6_subnets):
        """
        Validate that a device's subnets match DHCP database
        
        Args:
            device_name: Device hostname
            primary_subnet: Primary subnet from Netshot diagnostic
            public_ipv4_subnets: List of public IPv4 subnets from Netshot diagnostic
            public_ipv6_subnets: List of public IPv6 subnets from Netshot diagnostic
        
        Returns:
            Dictionary with validation results
        """
        result = {
            'has_dhcp': False,
            'dhcp_scopes': [],
            'dhcp_scopes_count': 0,
            'dhcp_ipv6_scopes': [],
            'missing_in_dhcp': [],
            'extra_in_dhcp': [],
            'matched': [],
            'ipv6_missing_in_dhcp': [],
            'ipv6_matched': []
        }
        
        if not primary_subnet:
            return result
        
        # Get IPv4 DHCP scopes for this primary subnet
        dhcp_scopes = self.get_scopes_by_primary(primary_subnet)
        result['dhcp_scopes'] = dhcp_scopes
        
        # Get IPv6 DHCP scopes by hostname
        dhcp_ipv6_scopes = self.get_ipv6_scopes_by_hostname(device_name)
        result['dhcp_ipv6_scopes'] = dhcp_ipv6_scopes
        
        # Filter public IPv4 scopes and exclude the primary subnet itself
        public_dhcp_scopes = [s for s in dhcp_scopes if is_public_ipv4(s['scope']) and s['scope'] != primary_subnet]
        
        # Filter unique IPv6 scopes (exclude -PD duplicates which are for prefix delegation)
        unique_ipv6_scopes = []
        seen_prefixes = set()
        for scope in dhcp_ipv6_scopes:
            prefix = scope['prefixname']
            # Remove -PD suffix to get base prefix
            base_prefix = prefix.replace('-PD', '') if prefix.endswith('-PD') else prefix
            if base_prefix not in seen_prefixes:
                seen_prefixes.add(base_prefix)
                unique_ipv6_scopes.append(scope)
        
        # Count both IPv4 and IPv6 scopes (excluding primary and IPv6 duplicates)
        ipv4_count = len(public_dhcp_scopes)
        ipv6_count = len(unique_ipv6_scopes)
        scope_count = ipv4_count + ipv6_count
        
        # If we got 0 or 1 scopes, retry the query once
        if scope_count <= 1:
            logger.info(f"Device {device_name} has {scope_count} scope(s), retrying query...")
            import time
            time.sleep(0.5)  # Brief pause before retry
            
            # Retry IPv4 query
            dhcp_scopes_retry = self.get_scopes_by_primary(primary_subnet)
            public_dhcp_scopes_retry = [s for s in dhcp_scopes_retry if is_public_ipv4(s['scope']) and s['scope'] != primary_subnet]
            
            # Retry IPv6 query
            dhcp_ipv6_scopes_retry = self.get_ipv6_scopes_by_hostname(device_name)
            unique_ipv6_scopes_retry = []
            seen_prefixes_retry = set()
            for scope in dhcp_ipv6_scopes_retry:
                prefix = scope['prefixname']
                base_prefix = prefix.replace('-PD', '') if prefix.endswith('-PD') else prefix
                if base_prefix not in seen_prefixes_retry:
                    seen_prefixes_retry.add(base_prefix)
                    unique_ipv6_scopes_retry.append(scope)
            
            retry_count = len(public_dhcp_scopes_retry) + len(unique_ipv6_scopes_retry)
            
            # Use retry results if they're better
            if retry_count > scope_count:
                logger.info(f"Retry successful: {device_name} now has {retry_count} scopes")
                dhcp_scopes = dhcp_scopes_retry
                public_dhcp_scopes = public_dhcp_scopes_retry
                dhcp_ipv6_scopes = dhcp_ipv6_scopes_retry
                unique_ipv6_scopes = unique_ipv6_scopes_retry
                result['dhcp_scopes'] = dhcp_scopes
                result['dhcp_ipv6_scopes'] = dhcp_ipv6_scopes
                ipv4_count = len(public_dhcp_scopes)
                ipv6_count = len(unique_ipv6_scopes)
            else:
                logger.info(f"Retry did not improve results for {device_name}")
        
        result['dhcp_scopes_count'] = ipv4_count + ipv6_count
        result['has_dhcp'] = result['dhcp_scopes_count'] > 0
        
        # Validate IPv4
        if not result['has_dhcp']:
            result['missing_in_dhcp'] = public_ipv4_subnets
        else:
            dhcp_scope_set = {scope['scope'] for scope in public_dhcp_scopes}
            netshot_scope_set = set(public_ipv4_subnets)
            result['missing_in_dhcp'] = list(netshot_scope_set - dhcp_scope_set)
            result['extra_in_dhcp'] = list(dhcp_scope_set - netshot_scope_set)
            result['matched'] = list(netshot_scope_set & dhcp_scope_set)
        
        # Validate IPv6 (use prefixname column)
        if dhcp_ipv6_scopes:
            dhcp_ipv6_scope_set = {scope['prefixname'] for scope in dhcp_ipv6_scopes}
            netshot_ipv6_scope_set = set(public_ipv6_subnets)
            result['ipv6_missing_in_dhcp'] = list(netshot_ipv6_scope_set - dhcp_ipv6_scope_set)
            result['ipv6_matched'] = list(netshot_ipv6_scope_set & dhcp_ipv6_scope_set)
        else:
            result['ipv6_missing_in_dhcp'] = public_ipv6_subnets
        
        return result
    
    def get_cached_dhcp_validation(self, device_name):
        """Get cached DHCP validation result from MySQL"""
        if not self.connection:
            return None
        
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                query = f"""
                    SELECT * FROM {self.cache_database}.dhcp_validation_cache 
                    WHERE device_name = %s 
                    AND updated_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    ORDER BY updated_at DESC LIMIT 1
                """
                cursor.execute(query, (device_name,))
                row = cursor.fetchone()
                
                if row:
                    # Convert JSON string fields back to objects
                    import json
                    return {
                        'has_dhcp': row['has_dhcp'],
                        'dhcp_scopes_count': row['dhcp_scopes_count'],
                        'dhcp_hostname': row['dhcp_hostname'],
                        'missing_in_dhcp': json.loads(row['missing_in_dhcp']) if row['missing_in_dhcp'] else [],
                        'matched': json.loads(row['matched']) if row['matched'] else [],
                        'updated_at': row['updated_at']
                    }
        except Exception as e:
            logger.error(f"Error fetching cached validation for {device_name}: {e}")
        
        return None
    
    def save_dhcp_validation(self, device_name, validation_result):
        """Save DHCP validation result to MySQL cache"""
        if not self.connection:
            return False
        
        try:
            import json
            with self.connection.cursor() as cursor:
                query = f"""
                    INSERT INTO {self.cache_database}.dhcp_validation_cache 
                    (device_name, dhcp_hostname, has_dhcp, dhcp_scopes_count, missing_in_dhcp, matched, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                    dhcp_hostname = VALUES(dhcp_hostname),
                    has_dhcp = VALUES(has_dhcp),
                    dhcp_scopes_count = VALUES(dhcp_scopes_count),
                    missing_in_dhcp = VALUES(missing_in_dhcp),
                    matched = VALUES(matched),
                    updated_at = NOW()
                """
                cursor.execute(query, (
                    device_name,
                    validation_result.get('dhcp_hostname'),
                    validation_result.get('has_dhcp', False),
                    validation_result.get('dhcp_scopes_count', 0),
                    json.dumps(validation_result.get('missing_in_dhcp', [])),
                    json.dumps(validation_result.get('matched', []))
                ))
                self.connection.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving validation for {device_name}: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
