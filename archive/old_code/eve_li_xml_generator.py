#!/home/svdleer/python/venv/bin/python
"""
EVE LI XML Generator
===================

Unified Python script that replaces both evexml.pl and shoxml.pl
Generates XML files for EVE LI with IP address validation, 
gzip compression, and detailed logging.

Features:
- IP address and subnet validation
- Gzip compression for uploads
- External trigger support
- Detailed logging with server response messages
- Email notifications
- Database connectivity
- XML schema validation

Author: Converted from Perl scripts by Silvester van der Leer
Version: 1.0
License: GPL v2
"""

import os
import sys
import gzip
import logging
import smtplib
import socket
import ipaddress
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional, Tuple
import requests
from xml.dom import minidom
import schedule
import time
import argparse
import json
import base64
from dotenv import load_dotenv


class EVEXMLGenerator:
    """Main class for EVE LI XML generation"""
    
    def __init__(self):
        """Initialize the XML generator with configuration"""
        # Load environment variables from .env file
        load_dotenv()
        
        self.logger = self._setup_logging()
        self.db_connection = None
        self.load_config()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup detailed logging configuration"""
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logger = logging.getLogger('eve_xml_generator')
        logger.setLevel(logging.DEBUG)
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(
            log_dir / f"eve_xml_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler for info and above
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
        
    def load_config(self):
        """Load configuration from environment variables only"""
        try:
            # Create config dictionary structure for compatibility
            self.config = {}
            
            # Load all configuration from environment variables
            self._load_from_environment()
            
            self.logger.info("Configuration loaded from environment variables")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
            
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        # Database configuration
        self.config['DATABASE'] = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_DATABASE', 'your_database'),
            'user': os.getenv('DB_USER', 'your_user'),
            'password': os.getenv('DB_PASSWORD', 'your_password'),
            'port': os.getenv('DB_PORT', '3306')
        }
        
        # API configuration
        self.config['API'] = {
            'base_url': os.getenv('API_BASE_URL', 'https://appdb.oss.local/isw/api'),
            'auth_token': os.getenv('API_AUTH_TOKEN', 'aXN3OlNweWVtX090R2hlYjQ='),
            'timeout': os.getenv('API_TIMEOUT', '30')
        }
        
        # Email configuration
        self.config['EMAIL'] = {
            'smtp_server': os.getenv('EMAIL_SMTP_SERVER', 'localhost'),
            'smtp_port': os.getenv('EMAIL_SMTP_PORT', '587'),
            'from_email': os.getenv('EMAIL_FROM', 'your_email@domain.com'),
            'to_email': os.getenv('EMAIL_TO', 'recipient@domain.com'),
            'username': os.getenv('EMAIL_USERNAME', ''),
            'password': os.getenv('EMAIL_PASSWORD', '')
        }
        
        # Upload configuration
        self.config['UPLOAD'] = {
            'api_base_url': os.getenv('UPLOAD_API_BASE_URL', 'https://172.17.130.70:2305'),
            'api_username': os.getenv('UPLOAD_API_USERNAME', 'xml_import'),
            'api_password': os.getenv('UPLOAD_API_PASSWORD', ''),
            'timeout': os.getenv('UPLOAD_TIMEOUT', '600'),
            'verification_mode': os.getenv('UPLOAD_VERIFICATION_MODE', 'true')
        }
        
        # Paths configuration
        self.config['PATHS'] = {
            'output_dir': os.getenv('OUTPUT_DIR', 'output'),
            'schema_file': os.getenv('SCHEMA_FILE', 'EVE_IAP_Import.xsd')
        }
        
        # Triggers configuration
        self.config['TRIGGERS'] = {
            'trigger_file': os.getenv('TRIGGER_FILE', 'trigger.txt'),
            'schedule_time': os.getenv('SCHEDULE_TIME', '09:00'),
            'weekdays_only': os.getenv('WEEKDAYS_ONLY', 'true')
        }
        
        # Logging configuration
        self.config['LOGGING'] = {
            'log_to_database': os.getenv('LOG_TO_DATABASE', 'true'),
            'log_table': os.getenv('LOG_TABLE', 'eve_xml_log'),
            'status_table': os.getenv('STATUS_TABLE', 'eve_xml_status')
        }
            
    def validate_ip_address(self, ip_addr: str) -> bool:
        """Validate IPv4/IPv6 address or subnet with detailed logging"""
        if not ip_addr or not ip_addr.strip():
            self.logger.debug("Empty IP address provided")
            return False
            
        ip_addr = ip_addr.strip()
        
        try:
            # Try to parse as single IP address first
            ip_obj = ipaddress.ip_address(ip_addr)
            if ip_obj.version == 4:
                self.logger.debug(f"Valid IPv4 address: {ip_addr}")
            else:
                self.logger.debug(f"Valid IPv6 address: {ip_addr}")
            return True
        except ValueError:
            try:
                # Try to parse as network/subnet
                network_obj = ipaddress.ip_network(ip_addr, strict=False)
                if network_obj.version == 4:
                    self.logger.debug(f"Valid IPv4 network: {ip_addr} (network: {network_obj.network_address}/{network_obj.prefixlen})")
                else:
                    self.logger.debug(f"Valid IPv6 network: {ip_addr} (network: {network_obj.network_address}/{network_obj.prefixlen})")
                return True
            except ValueError as e:
                self.logger.warning(f"Invalid IP address or network '{ip_addr}': {e}")
                return False
    
    def validate_and_normalize_ip(self, ip_addr: str) -> Optional[str]:
        """Validate and normalize IP address/network, return None if invalid"""
        if not self.validate_ip_address(ip_addr):
            return None
            
        ip_addr = ip_addr.strip()
        
        try:
            # Try as single IP first
            ip_obj = ipaddress.ip_address(ip_addr)
            return str(ip_obj)
        except ValueError:
            try:
                # Try as network
                network_obj = ipaddress.ip_network(ip_addr, strict=False)
                return str(network_obj)
            except ValueError:
                return None
    
    def get_ip_version(self, ip_addr: str) -> Optional[int]:
        """Get IP version (4 or 6) for a valid IP address or network"""
        try:
            # Try as IP address first
            ip_obj = ipaddress.ip_address(ip_addr)
            return ip_obj.version
        except ValueError:
            try:
                # Try as network
                network_obj = ipaddress.ip_network(ip_addr, strict=False)
                return network_obj.version
            except ValueError:
                return None
    
    def is_ipv6(self, ip_addr: str) -> bool:
        """Check if IP address or network is IPv6"""
        return self.get_ip_version(ip_addr) == 6
    
    def is_ipv4(self, ip_addr: str) -> bool:
        """Check if IP address or network is IPv4"""
        return self.get_ip_version(ip_addr) == 4
                
    def test_api_connection(self) -> bool:
        """Test API connection and show sample data"""
        try:
            base_url = self.config['API']['base_url']
            auth_token = self.config['API']['auth_token']
            timeout = int(self.config['API']['timeout'])
            
            # Test API connection
            url = f"{base_url}/search"
            params = {
                'type': 'hostname',
                'q': '*'
            }
            
            headers = {
                'accept': 'application/json',
                'Authorization': f'Basic {auth_token}'
            }
            
            self.logger.info(f"Testing API connection to: {url}")
            
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
                verify=False  # Skip SSL verification for internal APIs
            )
            
            self.logger.info(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"API Response Type: {type(data)}")
                
                if isinstance(data, list) and len(data) > 0:
                    self.logger.info(f"Number of devices returned: {len(data)}")
                    self.logger.info(f"Sample device data: {json.dumps(data[0], indent=2)}")
                elif isinstance(data, dict):
                    self.logger.info(f"Single device returned: {json.dumps(data, indent=2)}")
                else:
                    self.logger.info(f"Unexpected data format: {data}")
                    
                return True
            else:
                self.logger.error(f"API request failed: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"API connection test failed: {e}")
            return False
            
    def get_devices_from_api(self) -> List[Dict]:
        """Get all devices from the REST API"""
        devices = []
        try:
            base_url = self.config['API']['base_url']
            auth_token = self.config['API']['auth_token']
            timeout = int(self.config['API']['timeout'])
            
            # Prepare API request
            url = f"{base_url}/search"
            params = {
                'type': 'hostname',
                'q': '*'  # Get all devices
            }
            
            headers = {
                'accept': 'application/json',
                'Authorization': f'Basic {auth_token}'
            }
            
            # Make API request using Authorization header
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
                verify=False  # Skip SSL verification for internal APIs
            )
            
            if response.status_code == 200:
                api_data = response.json()
                self.logger.info(f"API response received: {len(api_data) if isinstance(api_data, list) else 'Unknown'} items")
                
                # Debug: Log the actual API response structure
                self.logger.info(f"API response type: {type(api_data)}")
                if isinstance(api_data, dict):
                    self.logger.info(f"API response keys: {list(api_data.keys())}")
                    # Log a sample of the response to understand structure
                    if len(str(api_data)) < 2000:  # Only log if not too large
                        self.logger.info(f"API response content: {api_data}")
                    else:
                        # Log just the first few items if it's too large
                        sample = {k: v for i, (k, v) in enumerate(api_data.items()) if i < 3}
                        self.logger.info(f"API response sample: {sample}")
                elif isinstance(api_data, list) and len(api_data) > 0:
                    self.logger.info(f"API returned list with {len(api_data)} items")
                    self.logger.info(f"First item keys: {list(api_data[0].keys()) if isinstance(api_data[0], dict) else 'Not a dict'}")
                    if len(str(api_data[0])) < 500:  # Only log if not too large
                        self.logger.info(f"First item content: {api_data[0]}")
                else:
                    self.logger.warning(f"Unexpected API response format: {type(api_data)} - {api_data}")
                
                # Process API response
                if isinstance(api_data, list):
                    for item in api_data:
                        device = self._process_api_device(item)
                        if device:
                            devices.append(device)
                elif isinstance(api_data, dict):
                    # Check if it's a wrapper dict containing actual device data
                    if 'results' in api_data or 'data' in api_data or 'devices' in api_data:
                        # Handle wrapped response
                        actual_data = api_data.get('results', api_data.get('data', api_data.get('devices', [])))
                        if isinstance(actual_data, list):
                            for item in actual_data:
                                device = self._process_api_device(item)
                                if device:
                                    devices.append(device)
                        else:
                            device = self._process_api_device(actual_data)
                            if device:
                                devices.append(device)
                    else:
                        # Handle single device response
                        device = self._process_api_device(api_data)
                        if device:
                            devices.append(device)
                        
                self.logger.info(f"Processed {len(devices)} valid devices from API")
                
            elif response.status_code == 401:
                self.logger.error("API authentication failed - invalid username/password")
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        self.logger.error(f"API error: {error_data['message']}")
                    if "authentication" in error_data:
                        auth_info = error_data["authentication"]
                        self.logger.info(f"Required auth type: {auth_info.get('type', 'Unknown')}")
                except json.JSONDecodeError:
                    pass
                
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Network connection failed to API: {e}")
            self.logger.info("This may be due to network connectivity, VPN, or DNS resolution issues")
        except requests.exceptions.Timeout as e:
            self.logger.error(f"API request timeout: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
        except Exception as e:
            self.logger.error(f"Failed to get devices from API: {e}")
            
        return devices
        
    def _get_devices_from_database_fallback(self) -> List[Dict]:
        """Fallback to database when API is not available"""
        devices = []
        
        try:
            if not self.connect_database():
                self.logger.error("Database fallback failed - cannot connect to database")
                return devices
                
            self.logger.info("Using database fallback for device information")
            
            # Get VFZ devices
            vfz_devices = self._get_vfz_devices_from_db()
            devices.extend(vfz_devices)
            
            # Get PE devices  
            pe_devices = self._get_pe_devices_from_db()
            devices.extend(pe_devices)
            
            self.logger.info(f"Retrieved {len(devices)} devices from database fallback")
            
        except Exception as e:
            self.logger.error(f"Database fallback failed: {e}")
        finally:
            self.disconnect_database()
            
        return devices
        
    def _get_vfz_devices_from_db(self) -> List[Dict]:
        """Get VFZ devices from database"""
        devices = []
        try:
            cursor = self.db_connection.cursor()
            sql = """
                SELECT UPPER(hostname), loopbackip 
                FROM devicesnew 
                WHERE active='1' 
                GROUP BY hostname 
                ORDER BY hostname ASC
            """
            cursor.execute(sql)
            
            for hostname, loopbackip in cursor.fetchall():
                if loopbackip and self.validate_ip_address(loopbackip):
                    devices.append({
                        'hostname': hostname,
                        'loopbackip': loopbackip,
                        'category': 'vfz',
                        'device_type': 'cmts'
                    })
                    
            cursor.close()
            self.logger.info(f"Retrieved {len(devices)} VFZ devices from database")
            
        except Exception as e:
            self.logger.error(f"Failed to get VFZ devices from database: {e}")
            
        return devices
        
    def _get_pe_devices_from_db(self) -> List[Dict]:
        """Get PE devices from database"""
        devices = []
        try:
            cursor = self.db_connection.cursor()
            sql = """
                SELECT UPPER(name), type, lo80, stype, port, dtcp_version, 
                       list_flags, ifindex 
                FROM tblB2B_PE_Routers 
                ORDER BY name ASC
            """
            cursor.execute(sql)
            
            for row in cursor.fetchall():
                name, device_type, lo80, stype, port, dtcp_version, list_flags, ifindex = row
                if name and lo80 and self.validate_ip_address(lo80):
                    # Clean ifindex
                    if ifindex:
                        ifindex = ifindex.replace('\r', '')
                        
                    devices.append({
                        'hostname': name,
                        'loopbackip': lo80,
                        'device_type': device_type,
                        'category': 'pe',
                        'stype': stype,
                        'port': port,
                        'dtcp_version': dtcp_version,
                        'list_flags': list_flags,
                        'ifindex': ifindex
                    })
                    
            cursor.close()
            self.logger.info(f"Retrieved {len(devices)} PE devices from database")
            
        except Exception as e:
            self.logger.error(f"Failed to get PE devices from database: {e}")
            
        return devices
        
    def get_device_networks_from_database(self, hostname: str, device_category: str) -> List[str]:
        """Get networks/scopes for a device from database"""
        networks = []
        try:
            if not self.connect_database():
                self.logger.error("Cannot connect to database for device networks")
                return networks
                
            if device_category == 'vfz':
                # Get both IPv4 and IPv6 scopes for VFZ devices
                networks.extend(self._get_vfz_scopes_from_db(hostname, 'ipv4'))
                networks.extend(self._get_vfz_scopes_from_db(hostname, 'ipv6'))
            elif device_category == 'pe':
                # Get IP blocks for PE devices
                networks.extend(self._get_pe_networks_from_db(hostname))
                
        except Exception as e:
            self.logger.error(f"Failed to get networks for {hostname}: {e}")
        finally:
            self.disconnect_database()
            
        return networks
        
    def _get_vfz_scopes_from_db(self, hostname: str, ip_version: str) -> List[str]:
        """Get VFZ scopes from database"""
        scopes = []
        try:
            cursor = self.db_connection.cursor()
            
            if ip_version == 'ipv4':
                # Get IPv4 scopes
                sql = """
                    SELECT scope
                    FROM scopes 
                    WHERE cmts = %s AND scope NOT LIKE '%:%'
                    ORDER BY scope
                """
            else:
                # Get IPv6 scopes  
                sql = """
                    SELECT scope
                    FROM scopes 
                    WHERE cmts = %s AND scope LIKE '%:%'
                    ORDER BY scope
                """
                
            cursor.execute(sql, (hostname,))
            
            for (scope,) in cursor.fetchall():
                if scope:
                    # Clean IPv6 prefixes
                    if ip_version == 'ipv6':
                        scope = scope.replace('-PD', '')
                    if self.validate_ip_address(scope):
                        scopes.append(scope)
                        
            cursor.close()
            self.logger.debug(f"Retrieved {len(scopes)} {ip_version} scopes for {hostname}")
            
        except Exception as e:
            self.logger.error(f"Failed to get {ip_version} scopes for {hostname}: {e}")
            
        return scopes
        
    def _get_pe_networks_from_db(self, hostname: str) -> List[str]:
        """Get PE networks from database"""
        networks = []
        try:
            cursor = self.db_connection.cursor()
            sql = """
                SELECT ip_block
                FROM tblB2B_PE_IP_Blocks 
                WHERE pe_router = %s AND ip_block != '0.0.0.0/0'
                ORDER BY ip_block
            """
            cursor.execute(sql, (hostname,))
            
            for (ip_block,) in cursor.fetchall():
                if ip_block and self.validate_ip_address(ip_block):
                    networks.append(ip_block)
                    
            cursor.close()
            self.logger.debug(f"Retrieved {len(networks)} networks for {hostname}")
            
        except Exception as e:
            self.logger.error(f"Failed to get networks for {hostname}: {e}")
            
        return networks
        
    def init_database_logging(self):
        """Initialize database logging tables"""
        try:
            if not self.connect_database():
                return False
                
            cursor = self.db_connection.cursor()
            
            # Create log table for detailed logging
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eve_xml_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level VARCHAR(10) NOT NULL,
                    message TEXT NOT NULL,
                    xml_type VARCHAR(10),
                    hostname VARCHAR(100),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_level (level),
                    INDEX idx_xml_type (xml_type)
                )
            """)
            
            # Create status table for current status tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eve_xml_status (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    xml_type VARCHAR(10) NOT NULL UNIQUE,
                    status VARCHAR(20) NOT NULL,
                    started_at DATETIME,
                    completed_at DATETIME,
                    device_count INT DEFAULT 0,
                    network_count INT DEFAULT 0,
                    file_path VARCHAR(255),
                    file_size BIGINT,
                    upload_status VARCHAR(50),
                    upload_response TEXT,
                    error_message TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_xml_type (xml_type),
                    INDEX idx_status (status)
                )
            """)
            
            # Create trigger table for manual runs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eve_xml_trigger (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    xml_type VARCHAR(10) NOT NULL,
                    triggered_by VARCHAR(50) DEFAULT 'manual',
                    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed TINYINT DEFAULT 0,
                    processed_at DATETIME NULL,
                    INDEX idx_processed (processed),
                    INDEX idx_xml_type (xml_type)
                )
            """)
            
            cursor.close()
            self.logger.info("Database logging tables initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database logging: {e}")
            return False
        finally:
            self.disconnect_database()
            
    def log_to_database(self, level: str, message: str, xml_type: str = None, hostname: str = None):
        """Log message to database"""
        try:
            if self.config.get('LOGGING', {}).get('log_to_database', 'false').lower() != 'true':
                return
                
            if not self.connect_database():
                return
                
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO eve_xml_log (level, message, xml_type, hostname)
                VALUES (%s, %s, %s, %s)
            """, (level, message, xml_type, hostname))
            self.db_connection.commit()
            cursor.close()
            
        except Exception as e:
            # Don't log database logging errors to avoid recursion
            pass
        finally:
            self.disconnect_database()
            
    def update_status(self, xml_type: str, status: str, **kwargs):
        """Update processing status in database"""
        try:
            if not self.connect_database():
                return
                
            cursor = self.db_connection.cursor()
            
            # Check if record exists
            cursor.execute("SELECT id FROM eve_xml_status WHERE xml_type = %s", (xml_type,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing record
                set_clauses = ['status = %s']
                values = [status]
                
                for key, value in kwargs.items():
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
                    
                values.append(xml_type)
                
                sql = f"UPDATE eve_xml_status SET {', '.join(set_clauses)} WHERE xml_type = %s"
                cursor.execute(sql, values)
            else:
                # Insert new record
                columns = ['xml_type', 'status']
                values = [xml_type, status]
                placeholders = ['%s', '%s']
                
                for key, value in kwargs.items():
                    columns.append(key)
                    values.append(value)
                    placeholders.append('%s')
                    
                sql = f"INSERT INTO eve_xml_status ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(sql, values)
                
            self.db_connection.commit()
            cursor.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update status: {e}")
        finally:
            self.disconnect_database()
            
    def check_database_trigger(self, xml_type: str) -> bool:
        """Check for database trigger for manual runs"""
        try:
            if not self.connect_database():
                return False
                
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT id FROM eve_xml_trigger 
                WHERE xml_type = %s AND processed = 0 
                ORDER BY triggered_at ASC 
                LIMIT 1
            """, (xml_type,))
            
            result = cursor.fetchone()
            
            if result:
                # Mark as processed
                trigger_id = result[0]
                cursor.execute("""
                    UPDATE eve_xml_trigger 
                    SET processed = 1, processed_at = NOW() 
                    WHERE id = %s
                """, (trigger_id,))
                self.db_connection.commit()
                
                cursor.close()
                self.logger.info(f"Database trigger found for {xml_type}")
                self.log_to_database('INFO', f'Manual trigger activated for {xml_type}', xml_type)
                return True
                
            cursor.close()
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check database trigger: {e}")
            return False
        finally:
            self.disconnect_database()
            
    def is_weekday_and_time(self) -> bool:
        """Check if current time is weekday and within schedule"""
        if self.config.get('TRIGGERS', {}).get('weekdays_only', 'true').lower() != 'true':
            return True  # Always run if weekdays_only is disabled
            
        now = datetime.now()
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
            
        # Check time - allow 30 minute window around schedule time
        schedule_time = self.config.get('TRIGGERS', {}).get('schedule_time', '09:00')
        try:
            schedule_hour, schedule_minute = map(int, schedule_time.split(':'))
            schedule_dt = now.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
            
            # Allow 30 minute window (15 minutes before, 15 minutes after)
            time_diff = abs((now - schedule_dt).total_seconds())
            return time_diff <= 900  # 15 minutes = 900 seconds
            
        except:
            self.logger.warning(f"Invalid schedule time format: {schedule_time}")
            return True
        
    def _process_api_device(self, item: Dict) -> Optional[Dict]:
        """Process a single device from API response"""
        try:
            # Debug: Log the item structure
            self.logger.debug(f"Processing API item: {item}")
            
            # Extract device information from API response
            # Handle actual API field names: HostName, IPAddress, Type, Vendor
            hostname = (item.get('HostName', '') or item.get('hostname', '')).upper()
            loopbackip = (item.get('IPAddress', '') or 
                         item.get('loopbackip', '') or 
                         item.get('management_ip', '') or 
                         item.get('ip_address', ''))
            device_type = (item.get('Type', '') or 
                          item.get('type', '') or 
                          item.get('device_type', ''))
            vendor = item.get('Vendor', '') or item.get('vendor', '')
            
            self.logger.debug(f"Extracted: hostname='{hostname}', loopbackip='{loopbackip}', device_type='{device_type}', vendor='{vendor}'")
            
            # Validate required fields
            if not hostname:
                self.logger.debug("Skipping device: no hostname")
                return None
                
            if not loopbackip:
                self.logger.debug(f"Skipping device {hostname}: no IP address")
                return None
                
            # Validate IP address
            if not loopbackip:
                self.logger.debug(f"Skipping device {hostname}: no IP address")
                return None
                
            normalized_ip = self.validate_and_normalize_ip(loopbackip)
            if not normalized_ip:
                self.logger.warning(f"Skipping device {hostname}: invalid IP address {loopbackip}")
                return None
            
            # Log IP version
            ip_version = self.get_ip_version(normalized_ip)
            self.logger.debug(f"Device {hostname}: IPv{ip_version} address {normalized_ip}")
                
            # Determine device category based on hostname, type, or vendor
            device_category = self._determine_device_category(hostname, device_type, vendor, item)
            
            if not device_category:
                self.logger.debug(f"Skipping device {hostname}: cannot determine category")
                return None
                
            device_info = {
                'hostname': hostname,
                'loopbackip': normalized_ip,
                'device_type': device_type,
                'vendor': vendor,
                'category': device_category,
                'ip_version': ip_version,
                'raw_data': item  # Keep original data for reference
            }
            
            # Add category-specific fields
            if device_category == 'pe':
                device_info.update({
                    'port': item.get('port'),
                    'dtcp_version': item.get('dtcp_version'),
                    'list_flags': item.get('list_flags'),
                    'ifindex': item.get('ifindex', '').replace('\r', '') if item.get('ifindex') else None,
                    'stype': item.get('stype')
                })
                
            self.logger.debug(f"Processed device: {hostname} ({device_category})")
            return device_info
            
        except Exception as e:
            self.logger.error(f"Error processing API device: {e}")
            return None
            
    def _determine_device_category(self, hostname: str, device_type: str, vendor: str, item: Dict) -> Optional[str]:
        """Determine if device is VFZ or PE based on hostname, type, vendor, or other attributes"""
        hostname_lower = hostname.lower()
        device_type_lower = device_type.lower() if device_type else ''
        vendor_lower = vendor.lower() if vendor else ''
        
        # VFZ device patterns (CMTS/CCAP devices) - based on actual API data
        # Check vendor and type combinations from the API response
        if vendor_lower in ['arris', 'cisco'] and device_type_lower in ['e6000', 'cbr-8', 'cbr8']:
            return 'vfz'
            
        # Check for CCAP/CMTS in hostname (like CCAP001, CCAP201)
        if 'ccap' in hostname_lower or 'cmts' in hostname_lower:
            return 'vfz'
            
        # VFZ device patterns in hostname
        vfz_patterns = ['cmts', 'ccap', 'casa', 'arris', 'harmonic']
        if any(pattern in hostname_lower for pattern in vfz_patterns):
            return 'vfz'
            
        # PE device patterns (routers)
        pe_patterns = ['pe-', 'pe_', 'router', 'asr', 'mx', 'sr-']
        if any(pattern in hostname_lower for pattern in pe_patterns):
            return 'pe'
            
        # Check device type for routers
        if device_type_lower in ['juniper', 'cisco-xr', 'sros-md', 'router', 'pe']:
            return 'pe'
            
        # Check for specific fields that indicate PE device type
        if item.get('dtcp_version') or item.get('list_flags'):
            return 'pe'
            
        # Default categorization based on other attributes
        if 'active' in item and item.get('active') == '1':
            # Assume VFZ if active field is present (from original devicesnew table)
            return 'vfz'
        
        # Based on the API data shown, devices with Type E6000/cBR-8 and Vendor Arris/Cisco are VFZ
        # If we can't determine category but have vendor/type info, assume VFZ for CMTS-like devices
        if vendor_lower in ['arris', 'cisco'] and device_type_lower:
            self.logger.info(f"Assuming VFZ category for {hostname} (vendor: {vendor}, type: {device_type})")
            return 'vfz'
            
        # If we can't determine, log and skip
        self.logger.debug(f"Cannot determine category for device {hostname} (vendor: {vendor}, type: {device_type})")
        return None
        
    def get_device_networks_from_api(self, hostname: str, device_category: str) -> List[str]:
        """Get networks/scopes for a device from API"""
        networks = []
        try:
            base_url = self.config['API']['base_url']
            username = self.config['API']['username']
            password = self.config['API']['password']
            timeout = int(self.config['API']['timeout'])
            
            # Different API endpoints or parameters for different device types
            if device_category == 'vfz':
                # Get both IPv4 and IPv6 scopes for VFZ devices
                networks.extend(self._get_vfz_scopes_from_api(hostname, 'ipv4'))
                networks.extend(self._get_vfz_scopes_from_api(hostname, 'ipv6'))
            elif device_category == 'pe':
                # Get IP blocks for PE devices
                networks.extend(self._get_pe_networks_from_api(hostname))
                
        except Exception as e:
            self.logger.error(f"Failed to get networks for {hostname}: {e}")
            
        return networks
        
    def _get_vfz_scopes_from_api(self, hostname: str, ip_version: str) -> List[str]:
        """Get VFZ scopes from API"""
        scopes = []
        try:
            # This would need to be adjusted based on your actual API structure
            # For now, using a placeholder approach
            base_url = self.config['API']['base_url']
            auth_token = self.config['API']['auth_token']
            timeout = int(self.config['API']['timeout'])
            
            # Example API call for scopes - adjust based on actual API
            url = f"{base_url}/scopes"
            params = {
                'hostname': hostname,
                'type': ip_version
            }
            
            headers = {
                'accept': 'application/json',
                'Authorization': f'Basic {auth_token}'
            }
            
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                scope_data = response.json()
                if isinstance(scope_data, list):
                    for scope_item in scope_data:
                        scope = scope_item.get('scope') or scope_item.get('network') or scope_item.get('prefix')
                        if scope:
                            # Clean IPv6 prefixes
                            if ip_version == 'ipv6':
                                scope = scope.replace('-PD', '')
                            if self.validate_ip_address(scope):
                                scopes.append(scope)
                                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed for IPv4 scopes: {e}")
        except Exception as e:
            self.logger.error(f"Error getting {ip_version} scopes for {hostname}: {e}")
            
        return scopes
        
    def _get_pe_networks_from_api(self, hostname: str) -> List[str]:
        """Get PE networks from API"""
        networks = []
        try:
            # This would need to be adjusted based on your actual API structure
            base_url = self.config['API']['base_url']
            auth_token = self.config['API']['auth_token']
            timeout = int(self.config['API']['timeout'])
            
            # Example API call for networks - adjust based on actual API
            url = f"{base_url}/networks"
            params = {
                'pe_router': hostname
            }
            
            headers = {
                'accept': 'application/json',
                'Authorization': f'Basic {auth_token}'
            }
            
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                network_data = response.json()
                if isinstance(network_data, list):
                    for network_item in network_data:
                        network = network_item.get('ip_block') or network_item.get('network') or network_item.get('cidr')
                        if network and network != '0.0.0.0/0' and self.validate_ip_address(network):
                            networks.append(network)
                            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed for networks: {e}")
        except Exception as e:
            self.logger.error(f"Error getting networks for {hostname}: {e}")
            
        return networks
        
    def connect_database(self) -> bool:
        """Connect to MySQL database"""
        try:
            import mysql.connector
            from mysql.connector import Error
            
            self.db_connection = mysql.connector.connect(
                host=self.config['DATABASE']['host'],
                database=self.config['DATABASE']['database'],
                user=self.config['DATABASE']['user'],
                password=self.config['DATABASE']['password'],
                port=int(self.config['DATABASE']['port'])
            )
            
            if self.db_connection.is_connected():
                self.logger.info("Successfully connected to database")
                return True
                
        except Error as e:
            self.logger.error(f"Database connection failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            return False
            
    def disconnect_database(self):
        """Disconnect from database"""
        try:
            if self.db_connection and self.db_connection.is_connected():
                self.db_connection.close()
                self.logger.debug("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error closing database connection: {e}")
            
    def get_vfz_devices(self) -> List[Dict]:
        """Get VFZ CMTS devices from API"""
        all_devices = self.get_devices_from_api()
        vfz_devices = [device for device in all_devices if device.get('category') == 'vfz']
        self.logger.info(f"Retrieved {len(vfz_devices)} VFZ devices from API")
        return vfz_devices
        
    def get_pe_devices(self) -> List[Dict]:
        """Get PE router devices from database"""
        devices = []
        
        try:
            if not self.connect_database():
                self.logger.error("Cannot connect to database for PE devices")
                return devices
                
            self.logger.info("Getting PE devices from database")
            devices = self._get_pe_devices_from_db()
            
        except Exception as e:
            self.logger.error(f"Failed to get PE devices from database: {e}")
        finally:
            self.disconnect_database()
            
        return devices
        
    def create_vfz_xml(self, devices: List[Dict], output_file: str) -> bool:
        """Create XML for VFZ devices - devices from API, network scopes from database"""
        try:
            root = ET.Element('iaps')
            
            for device in devices:
                hostname = device['hostname']
                loopbackip = device['loopbackip']
                
                # Get network scopes for this device from database
                networks_list = self.get_device_networks_from_database(hostname, 'vfz')
                self.logger.debug(f"Retrieved {len(networks_list)} network scopes for {hostname} from database")
                
                # Separate IPv4 and IPv6 networks
                v4_scopes = []
                v6_scopes = []
                for network in networks_list:
                    try:
                        net = ipaddress.ip_network(network, strict=False)
                        if net.version == 4:
                            v4_scopes.append(network)
                        else:
                            v6_scopes.append(network)
                    except ValueError:
                        self.logger.warning(f"Invalid network format: {network}")
                        continue
                
                # Create IAP element
                iap = ET.SubElement(root, 'iap')
                
                # Attributes
                attributes = ET.SubElement(iap, 'attributes')
                ET.SubElement(attributes, 'type').text = '18'  # SII device
                ET.SubElement(attributes, 'name').text = hostname
                ET.SubElement(attributes, 'ipaddress').text = loopbackip
                
                # Add quirks for CCAP1 devices
                if 'CCAP1' in hostname:
                    ET.SubElement(attributes, 'quirks').text = '1:m'
                
                # Groups
                groups = ET.SubElement(iap, 'groups')
                ET.SubElement(groups, 'group').text = '15'
                
                # Networks
                networks = ET.SubElement(iap, 'networks')
                
                # Add IPv4 scopes
                for scope in v4_scopes:
                    network = ET.SubElement(networks, 'network')
                    ET.SubElement(network, 'address').text = scope
                    
                # Add IPv6 scopes
                for scope in v6_scopes:
                    network = ET.SubElement(networks, 'network')
                    ET.SubElement(network, 'address').text = scope
                    
            # Write XML file
            self._write_xml_file(root, output_file)
            self.logger.info(f"VFZ XML created: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create VFZ XML: {e}")
            return False
            
    def create_pe_xml(self, devices: List[Dict], output_file: str) -> bool:
        """Create XML for PE devices"""
        try:
            root = ET.Element('iaps')
            
            for device in devices:
                hostname = device['hostname']
                loopbackip = device['loopbackip']
                device_type = device.get('device_type', 'juniper')
                
                # Get networks for this device (from database)
                networks_list = self.get_device_networks_from_database(hostname, 'pe')
                
                # Create IAP element
                iap = ET.SubElement(root, 'iap')
                
                # Attributes
                attributes = ET.SubElement(iap, 'attributes')
                
                # Set type based on device type
                type_mapping = {
                    'juniper': '1',
                    'cisco-xr': '18',
                    'sros-md': '65'
                }
                device_type_code = type_mapping.get(device_type, '1')
                ET.SubElement(attributes, 'type').text = device_type_code
                
                ET.SubElement(attributes, 'name').text = hostname
                ET.SubElement(attributes, 'ipaddress').text = loopbackip
                
                # Device-specific attributes
                if device_type == 'sros-md':
                    ET.SubElement(attributes, 'port').text = '830'
                    ET.SubElement(attributes, 'li_source').text = 'LI_MIRROR'
                elif device_type == 'cisco-xr' and device.get('ifindex'):
                    ET.SubElement(attributes, 'source_interface').text = device['ifindex']
                elif device_type == 'juniper':
                    if device.get('port'):
                        ET.SubElement(attributes, 'port').text = str(device['port'])
                    if device.get('dtcp_version'):
                        ET.SubElement(attributes, 'dtcp_version').text = str(device['dtcp_version'])
                    if device.get('list_flags'):
                        ET.SubElement(attributes, 'list_flags').text = str(device['list_flags'])
                
                # Groups
                groups = ET.SubElement(iap, 'groups')
                ET.SubElement(groups, 'group').text = '3'
                
                # Networks
                networks = ET.SubElement(iap, 'networks')
                
                for network_addr in networks_list:
                    if device_type != 'sros-md':
                        network = ET.SubElement(networks, 'network')
                        ET.SubElement(network, 'address').text = network_addr
                    else:
                        # Special handling for sros-md
                        is_ipv6 = '2001' in network_addr
                        
                        if not is_ipv6:
                            # Add two network entries with different indices
                            for ingress_idx in ['1', '2']:
                                network = ET.SubElement(networks, 'network')
                                ET.SubElement(network, 'address').text = network_addr
                                net_attrs = ET.SubElement(network, 'attributes')
                                ET.SubElement(net_attrs, 'ingress_index').text = ingress_idx
                                ET.SubElement(net_attrs, 'egress_index').text = '1'
                        else:
                            # IPv6 network
                            network = ET.SubElement(networks, 'network')
                            ET.SubElement(network, 'address').text = network_addr
                            net_attrs = ET.SubElement(network, 'attributes')
                            ET.SubElement(net_attrs, 'ingress_index').text = '1'
                            ET.SubElement(net_attrs, 'egress_index').text = '1'
                            
            # Write XML file
            self._write_xml_file(root, output_file)
            self.logger.info(f"PE XML created: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create PE XML: {e}")
            return False
            
    def _write_xml_file(self, root: ET.Element, output_file: str):
        """Write XML to file with proper formatting"""
        # Create pretty formatted XML
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ", encoding='UTF-8')
        
        # Remove extra blank lines
        lines = pretty_xml.decode('utf-8').split('\n')
        lines = [line for line in lines if line.strip()]
        pretty_xml = '\n'.join(lines)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
            
    def validate_xml_schema(self, xml_file: str) -> Tuple[bool, str]:
        """Validate XML against schema"""
        schema_file = self.config['PATHS']['schema_file']
        
        if not os.path.exists(schema_file):
            self.logger.warning(f"Schema file not found: {schema_file}")
            return True, "Schema validation skipped - schema file not found"
            
        try:
            # Use xmllint for validation (requires libxml2)
            import subprocess
            result = subprocess.run(
                ['xmllint', '--schema', schema_file, xml_file, '--noout'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self.logger.info(f"XML validation successful: {xml_file}")
                return True, "XML validation successful"
            else:
                error_msg = result.stderr.replace(os.path.dirname(xml_file) + '/', '')
                self.logger.error(f"XML validation failed: {error_msg}")
                return False, error_msg
                
        except FileNotFoundError:
            self.logger.warning("xmllint not found, skipping schema validation")
            return True, "Schema validation skipped - xmllint not available"
        except Exception as e:
            self.logger.error(f"Schema validation error: {e}")
            return False, str(e)
            
    def compress_file(self, input_file: str) -> str:
        """Compress file using gzip"""
        output_file = input_file + '.gz'
        
        try:
            with open(input_file, 'rb') as f_in:
                with gzip.open(output_file, 'wb') as f_out:
                    f_out.writelines(f_in)
                    
            self.logger.info(f"File compressed: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Failed to compress file: {e}")
            return input_file
            
    def upload_file(self, file_path: str, xml_type: str = 'vfz') -> Tuple[bool, str]:
        """Upload XML file to EVE LI API endpoint using the same method as infraxmlupload.pl"""
        try:
            # Check if in verification mode
            verification_mode = self.config['UPLOAD'].get('verification_mode', 'false').lower() == 'true'
            
            if verification_mode:
                self.logger.info(f"VERIFICATION MODE: Simulating upload of {file_path}")
                file_size = os.path.getsize(file_path)
                return True, f"VERIFICATION MODE: Upload simulated successfully (file size: {file_size} bytes)"
            
            # Read XML content from file
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Clean XML content (remove quotes and newlines like Perl script)
            xml_content = xml_content.replace('"', '\\"')
            xml_content = xml_content.replace('\r', '').replace('\n', '')
            
            # Create session with SSL verification disabled
            session = requests.Session()
            session.verify = False
            
            # Disable SSL warnings
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # API endpoints (from infraxmlupload.pl)
            api_base_url = self.config['UPLOAD'].get('api_base_url', 'https://172.17.130.70:2305')
            login_url = f"{api_base_url}/api/1/accounts/actions/login/"
            upload_url = f"{api_base_url}/api/1/iaps/actions/import_xml/"
            
            # Authentication credentials (from infraxmlupload.pl)
            auth_data = {
                "username": self.config['UPLOAD'].get('api_username', 'xml_import'),
                "password": self.config['UPLOAD'].get('api_password', '')
            }
            
            self.logger.info(f"Authenticating with EVE LI API at {login_url}")
            
            # Step 1: Login to get session and CSRF token
            login_response = session.post(
                login_url,
                json=auth_data,
                headers={'Content-Type': 'application/json'},
                timeout=int(self.config['UPLOAD'].get('timeout', '600'))
            )
            
            if not login_response.ok:
                error_msg = f"Authentication failed: {login_response.status_code} - {login_response.text}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # Extract CSRF token from cookies
            csrf_token = None
            for cookie in session.cookies:
                if cookie.name == 'csrftoken':
                    csrf_token = cookie.value
                    break
            
            if not csrf_token:
                error_msg = "Failed to extract CSRF token from login response"
                self.logger.error(error_msg)
                return False, error_msg
            
            self.logger.info("Authentication successful, uploading XML content")
            
            # Step 2: Upload XML content
            # Determine IAP groups based on XML type (from Perl scripts)
            if xml_type.lower() == 'vfz':
                iap_groups = [3]  # SOHO/VFZ groups (from sohoxmlupload.pl)
            else:
                iap_groups = [1, 4, 15]  # Infrastructure/PE groups (from infraxmlupload.pl)
            
            upload_data = {
                "iap_groups": iap_groups,
                "xml": xml_content
            }
            
            upload_headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token,
                'Referer': api_base_url
            }
            
            upload_response = session.post(
                upload_url,
                json=upload_data,
                headers=upload_headers,
                timeout=int(self.config['UPLOAD'].get('timeout', '600'))
            )
            
            # Log response details
            response_content = upload_response.text
            status_line = f"{upload_response.status_code} {upload_response.reason}"
            
            self.logger.info(f"Upload response status: {status_line}")
            self.logger.info(f"Upload response content: {response_content}")
            
            success = upload_response.ok
            result_message = f"Status: {status_line}\nResponse: {response_content}"
            
            if success:
                self.logger.info("XML upload completed successfully")
            else:
                self.logger.error(f"XML upload failed: {result_message}")
            
            return success, result_message
            
        except Exception as e:
            error_msg = f"Upload failed: {e}"
            self.logger.error(error_msg)
            return False, error_msg
            
    def send_email_report(self, xml_type: str, device_count: int, 
                         validation_result: str, upload_result: str):
        """Send email report"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            
            # Determine subject based on upload success
            if '204' in upload_result or '200' in upload_result:
                subject = f"EVE NL {xml_type} LI XML {date_str} uploaded successfully"
            else:
                subject = f"EVE NL {xml_type} LI XML {date_str} NOT uploaded successfully!"
                
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config['EMAIL']['from_email']
            msg['To'] = self.config['EMAIL']['to_email']
            msg['Subject'] = subject
            
            # Email body
            body = f"""Exporting XML...

Exported {device_count} {xml_type} devices to XML

XML validation status:
{validation_result}

Upload status:
{upload_result}

This e-mail is sent automatically by the EVE LI XML Generator
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(
                self.config['EMAIL']['smtp_server'],
                int(self.config['EMAIL']['smtp_port'])
            )
            
            if self.config['EMAIL']['username']:
                server.starttls()
                server.login(
                    self.config['EMAIL']['username'],
                    self.config['EMAIL']['password']
                )
                
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email report sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send email report: {e}")
            
    def check_trigger(self) -> bool:
        """Check for external trigger file"""
        trigger_file = self.config['TRIGGERS']['trigger_file']
        
        if os.path.exists(trigger_file):
            self.logger.info(f"Trigger file found: {trigger_file}")
            try:
                os.remove(trigger_file)
                self.logger.info("Trigger file removed")
            except Exception as e:
                self.logger.warning(f"Failed to remove trigger file: {e}")
            return True
            
        return False
        
    def process_vfz_xml(self) -> bool:
        """Process VFZ XML generation and upload with database logging"""
        xml_type = 'vfz'
        self.logger.info("Starting VFZ XML processing")
        self.log_to_database('INFO', 'Starting VFZ XML processing', xml_type)
        
        try:
            # Initialize database logging tables
            self.init_database_logging()
            
            # Update status to starting
            self.update_status(xml_type, 'starting', started_at=datetime.now())
            
            # Get devices from API
            self.update_status(xml_type, 'getting_devices')
            devices = self.get_vfz_devices()
            if not devices:
                error_msg = "No VFZ devices found"
                self.logger.warning(error_msg)
                self.log_to_database('WARNING', error_msg, xml_type)
                self.update_status(xml_type, 'failed', error_message=error_msg)
                return False
                
            self.log_to_database('INFO', f'Retrieved {len(devices)} VFZ devices', xml_type)
            
            # Create output directory
            output_dir = Path(self.config['PATHS']['output_dir'])
            output_dir.mkdir(exist_ok=True)
            
            # Generate XML
            self.update_status(xml_type, 'generating_xml', device_count=len(devices))
            date_str = datetime.now().strftime('%Y%m%d')
            xml_file = output_dir / f"EVE_NL_Infra_CMTS-{date_str}.xml"
            
            if not self.create_vfz_xml(devices, str(xml_file)):
                error_msg = "Failed to create VFZ XML"
                self.log_to_database('ERROR', error_msg, xml_type)
                self.update_status(xml_type, 'failed', error_message=error_msg)
                return False
                
            # Get file size
            file_size = os.path.getsize(str(xml_file))
            self.update_status(xml_type, 'validating', file_path=str(xml_file), file_size=file_size)
            
            # Validate XML
            validation_success, validation_msg = self.validate_xml_schema(str(xml_file))
            self.log_to_database('INFO', f'XML validation: {validation_msg}', xml_type)
            
            # Compress file
            self.update_status(xml_type, 'compressing')
            compressed_file = self.compress_file(str(xml_file))
            compressed_size = os.path.getsize(compressed_file)
            
            # Upload file
            self.update_status(xml_type, 'uploading', file_size=compressed_size)
            upload_success, upload_msg = self.upload_file(compressed_file, 'vfz')
            
            # Update final status
            if upload_success:
                self.update_status(xml_type, 'completed', 
                                 completed_at=datetime.now(),
                                 upload_status='success',
                                 upload_response=upload_msg)
                self.log_to_database('INFO', f'VFZ XML processing completed successfully', xml_type)
            else:
                self.update_status(xml_type, 'upload_failed',
                                 upload_status='failed',
                                 upload_response=upload_msg,
                                 error_message=f'Upload failed: {upload_msg}')
                self.log_to_database('ERROR', f'VFZ XML upload failed: {upload_msg}', xml_type)
            
            # Send email report
            self.send_email_report("Infra", len(devices), validation_msg, upload_msg)
            
            return upload_success
            
        except Exception as e:
            self.logger.error(f"Error in VFZ XML processing: {e}")
            return False
            
    def process_pe_xml(self) -> bool:
        """Process PE XML generation and upload with database logging"""
        xml_type = 'pe'
        self.logger.info("Starting PE XML processing")
        self.log_to_database('INFO', 'Starting PE XML processing', xml_type)
        
        try:
            # Initialize database logging tables
            self.init_database_logging()
            
            # Update status to starting
            self.update_status(xml_type, 'starting', started_at=datetime.now())
            
            # Get devices from database
            self.update_status(xml_type, 'getting_devices')
            devices = self.get_pe_devices()
            if not devices:
                error_msg = "No PE devices found"
                self.logger.warning(error_msg)
                self.log_to_database('WARNING', error_msg, xml_type)
                self.update_status(xml_type, 'failed', error_message=error_msg)
                return False
                
            self.log_to_database('INFO', f'Retrieved {len(devices)} PE devices', xml_type)
            
            # Create output directory
            output_dir = Path(self.config['PATHS']['output_dir'])
            output_dir.mkdir(exist_ok=True)
            
            # Generate XML
            self.update_status(xml_type, 'generating_xml', device_count=len(devices))
            date_str = datetime.now().strftime('%Y%m%d')
            xml_file = output_dir / f"EVE_NL_SOHO-{date_str}.xml"
            
            if not self.create_pe_xml(devices, str(xml_file)):
                error_msg = "Failed to create PE XML"
                self.log_to_database('ERROR', error_msg, xml_type)
                self.update_status(xml_type, 'failed', error_message=error_msg)
                return False
                
            # Get file size
            file_size = os.path.getsize(str(xml_file))
            self.update_status(xml_type, 'validating', file_path=str(xml_file), file_size=file_size)
            
            # Validate XML
            validation_success, validation_msg = self.validate_xml_schema(str(xml_file))
            self.log_to_database('INFO', f'XML validation: {validation_msg}', xml_type)
            
            # Compress file
            self.update_status(xml_type, 'compressing')
            compressed_file = self.compress_file(str(xml_file))
            compressed_size = os.path.getsize(compressed_file)
            
            # Upload file
            self.update_status(xml_type, 'uploading', file_size=compressed_size)
            upload_success, upload_msg = self.upload_file(compressed_file, 'pe')
            
            # Update final status
            if upload_success:
                self.update_status(xml_type, 'completed', 
                                 completed_at=datetime.now(),
                                 upload_status='success',
                                 upload_response=upload_msg)
                self.log_to_database('INFO', f'PE XML processing completed successfully', xml_type)
            else:
                self.update_status(xml_type, 'upload_failed',
                                 upload_status='failed',
                                 upload_response=upload_msg,
                                 error_message=f'Upload failed: {upload_msg}')
                self.log_to_database('ERROR', f'PE XML upload failed: {upload_msg}', xml_type)
            
            # Send email report
            self.send_email_report("SOHO", len(devices), validation_msg, upload_msg)
            
            return upload_success
            
        except Exception as e:
            self.logger.error(f"Error in PE XML processing: {e}")
            return False
    def run_cron_job(self):
        """Run from crontab - check triggers and schedule"""
        try:
            # Initialize database logging
            self.init_database_logging()
            
            # Check for manual CMTS trigger (VFZ only as requested)
            vfz_manual_trigger = self.check_database_trigger('vfz')
            
            # Check if it's scheduled time for regular run
            is_scheduled_time = self.is_weekday_and_time()
            
            if vfz_manual_trigger:
                self.logger.info("Manual VFZ trigger detected, processing VFZ XML only")
                self.log_to_database('INFO', 'Manual VFZ trigger detected', 'vfz')
                return self.process_vfz_xml()
                
            elif is_scheduled_time:
                self.logger.info("Scheduled time reached, processing both VFZ and PE XML")
                self.log_to_database('INFO', 'Scheduled run started', 'both')
                vfz_success = self.process_vfz_xml()
                pe_success = self.process_pe_xml()
                return vfz_success and pe_success
                
            else:
                # Not time to run and no manual trigger
                if datetime.now().weekday() >= 5:
                    self.logger.debug("Skipping - weekend")
                else:
                    self.logger.debug("Skipping - not scheduled time")
                return True
                
        except Exception as e:
            self.logger.error(f"Cron job failed: {e}")
            self.log_to_database('ERROR', f'Cron job failed: {e}')
            return False
            
    def run_scheduler(self):
        """Run scheduled tasks (legacy scheduler mode)"""
        schedule_time = self.config['TRIGGERS']['schedule_time']
        
        schedule.every().day.at(schedule_time).do(self.process_vfz_xml)
        schedule.every().day.at(schedule_time).do(self.process_pe_xml)
        
        self.logger.info(f"Scheduler started. Tasks scheduled for {schedule_time}")
        
        while True:
            # Check for external trigger
            if self.check_trigger():
                self.logger.info("External trigger detected, running tasks immediately")
                self.process_vfz_xml()
                self.process_pe_xml()
                
            # Run scheduled tasks
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        """Run scheduled tasks"""
        schedule_time = self.config['TRIGGERS']['schedule_time']
        
        schedule.every().day.at(schedule_time).do(self.process_vfz_xml)
        schedule.every().day.at(schedule_time).do(self.process_pe_xml)
        
        self.logger.info(f"Scheduler started. Tasks scheduled for {schedule_time}")
        
        while True:
            # Check for external trigger
            if self.check_trigger():
                self.logger.info("External trigger detected, running tasks immediately")
                self.process_vfz_xml()
                self.process_pe_xml()
                
            # Run scheduled tasks
            schedule.run_pending()
            time.sleep(60)  # Check every minute


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='EVE LI XML Generator')
    parser.add_argument('--mode', choices=['vfz', 'pe', 'both', 'schedule', 'cron', 'test', 'upload'], 
                       default='both', help='Processing mode')
    parser.add_argument('--file', type=str, help='XML file to upload (required for upload mode)')
    parser.add_argument('--type', choices=['vfz', 'pe'], default='vfz', 
                       help='XML type for upload mode (vfz or pe)')
    
    args = parser.parse_args()
    
    # Create generator instance (no config file needed - uses .env only)
    generator = EVEXMLGenerator()
    
    try:
        if args.mode == 'test':
            success = generator.test_api_connection()
            if success:
                print("API connection test successful!")
                # Try to get and display some devices
                devices = generator.get_devices_from_api()
                print(f"Found {len(devices)} devices total")
                vfz_devices = [d for d in devices if d.get('category') == 'vfz']
                pe_devices = [d for d in devices if d.get('category') == 'pe']
                print(f"VFZ devices: {len(vfz_devices)}")
                print(f"PE devices: {len(pe_devices)}")
                if vfz_devices:
                    print(f"Sample VFZ device: {vfz_devices[0]}")
                if pe_devices:
                    print(f"Sample PE device: {pe_devices[0]}")
                
                # If no devices from API, try database fallback
                if len(devices) == 0:
                    print("\nNo devices from API, testing database fallback...")
                    try:
                        fallback_devices = generator._get_devices_from_database_fallback()
                        print(f"Database fallback found {len(fallback_devices)} devices")
                        if fallback_devices:
                            vfz_fallback = [d for d in fallback_devices if d.get('category') == 'vfz']
                            pe_fallback = [d for d in fallback_devices if d.get('category') == 'pe']
                            print(f"VFZ devices from DB: {len(vfz_fallback)}")
                            print(f"PE devices from DB: {len(pe_fallback)}")
                            if vfz_fallback:
                                print(f"Sample VFZ from DB: {vfz_fallback[0]}")
                            if pe_fallback:
                                print(f"Sample PE from DB: {pe_fallback[0]}")
                    except Exception as e:
                        print(f"Database fallback failed: {e}")
            sys.exit(0 if success else 1)
        elif args.mode == 'vfz':
            success = generator.process_vfz_xml()
            sys.exit(0 if success else 1)
        elif args.mode == 'pe':
            success = generator.process_pe_xml()
            sys.exit(0 if success else 1)
        elif args.mode == 'both':
            vfz_success = generator.process_vfz_xml()
            pe_success = generator.process_pe_xml()
            sys.exit(0 if (vfz_success and pe_success) else 1)
        elif args.mode == 'cron':
            success = generator.run_cron_job()
            sys.exit(0 if success else 1)
        elif args.mode == 'upload':
            if not args.file:
                print("Error: --file argument is required for upload mode")
                print("Usage: python eve_li_xml_generator.py --mode upload --file path/to/file.xml [--type vfz|pe]")
                sys.exit(1)
            
            if not os.path.exists(args.file):
                print(f"Error: File not found: {args.file}")
                sys.exit(1)
                
            print(f"Uploading {args.file} as {args.type} XML...")
            success, message = generator.upload_file(args.file, args.type)
            
            if success:
                print("Upload successful!")
                print(f"Response: {message}")
            else:
                print("Upload failed!")
                print(f"Error: {message}")
                
            sys.exit(0 if success else 1)
        elif args.mode == 'schedule':
            generator.run_scheduler()
        
    except KeyboardInterrupt:
        generator.logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        generator.logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
