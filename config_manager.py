"""
Configuration Manager
Manages application settings stored in the database
"""
import os
import logging
from typing import Optional, Dict, Any
import mysql.connector
from mysql.connector import Error

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration settings from database"""
    
    def __init__(self):
        self.connection = None
        self._cache = {}
        self._initialized = False
    
    def _get_connection(self):
        """Get database connection using bootstrap credentials from environment"""
        if self.connection and self.connection.is_connected():
            return self.connection
        
        try:
            # Use bootstrap credentials from environment variables
            # These are the minimal credentials needed to access the settings table
            self.connection = mysql.connector.connect(
                host=os.getenv('BOOTSTRAP_MYSQL_HOST', 'localhost'),
                port=int(os.getenv('BOOTSTRAP_MYSQL_PORT', '3306')),
                user=os.getenv('BOOTSTRAP_MYSQL_USER', 'access'),
                password=os.getenv('BOOTSTRAP_MYSQL_PASSWORD', '44cC3sS'),
                database=os.getenv('BOOTSTRAP_MYSQL_DATABASE', 'li_xml'),
                autocommit=True
            )
            logger.info("ConfigManager connected to database")
            return self.connection
        except Error as e:
            logger.error(f"Error connecting to database: {e}")
            return None
    
    def _close_connection(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None
    
    def initialize_settings_table(self):
        """Create settings table if it doesn't exist"""
        conn = self._get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Read and execute the SQL schema
            sql_file = os.path.join(os.path.dirname(__file__), 'sql', 'settings.sql')
            with open(sql_file, 'r') as f:
                sql_commands = f.read()
            
            # Execute each statement
            for statement in sql_commands.split(';'):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            
            conn.commit()
            cursor.close()
            logger.info("Settings table initialized successfully")
            return True
        except Error as e:
            logger.error(f"Error initializing settings table: {e}")
            return False
        except FileNotFoundError:
            logger.error("settings.sql file not found")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Optional[str]:
        """
        Get a setting value by key
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        conn = self._get_connection()
        if not conn:
            return default
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT setting_value, setting_type FROM settings WHERE setting_key = %s",
                (key,)
            )
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                value = result['setting_value']
                setting_type = result['setting_type']
                
                # Convert based on type
                if setting_type == 'boolean':
                    value = value.lower() in ('true', '1', 'yes')
                elif setting_type == 'integer':
                    value = int(value) if value else default
                
                # Cache the value
                self._cache[key] = value
                return value
            
            return default
        except Error as e:
            logger.error(f"Error getting setting '{key}': {e}")
            return default
    
    def set_setting(self, key: str, value: Any, updated_by: str = None) -> bool:
        """
        Set a setting value
        
        Args:
            key: Setting key
            value: Setting value
            updated_by: Username of who updated the setting
            
        Returns:
            True if successful, False otherwise
        """
        conn = self._get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Convert boolean to string
            if isinstance(value, bool):
                value = 'true' if value else 'false'
            elif value is None:
                value = ''
            else:
                value = str(value)
            
            cursor.execute(
                """UPDATE settings 
                   SET setting_value = %s, updated_by = %s 
                   WHERE setting_key = %s""",
                (value, updated_by, key)
            )
            
            if cursor.rowcount > 0:
                # Update cache
                self._cache[key] = value
                cursor.close()
                logger.info(f"Setting '{key}' updated by {updated_by}")
                return True
            
            cursor.close()
            logger.warning(f"Setting '{key}' not found")
            return False
        except Error as e:
            logger.error(f"Error setting '{key}': {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all settings
        
        Returns:
            Dictionary of settings with their metadata
        """
        conn = self._get_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """SELECT setting_key, setting_value, setting_type, 
                          description, is_required, updated_at, updated_by 
                   FROM settings 
                   ORDER BY setting_key"""
            )
            results = cursor.fetchall()
            cursor.close()
            
            settings = {}
            for row in results:
                key = row['setting_key']
                value = row['setting_value']
                
                # Convert based on type
                if row['setting_type'] == 'boolean':
                    value = value.lower() in ('true', '1', 'yes') if value else False
                elif row['setting_type'] == 'integer':
                    value = int(value) if value else None
                
                settings[key] = {
                    'value': value,
                    'type': row['setting_type'],
                    'description': row['description'],
                    'is_required': bool(row['is_required']),
                    'updated_at': row['updated_at'],
                    'updated_by': row['updated_by']
                }
            
            return settings
        except Error as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    def is_app_initialized(self) -> bool:
        """Check if the app has been initialized (setup completed)"""
        value = self.get_setting('app_initialized', 'false')
        # Handle both string and boolean values
        if isinstance(value, bool):
            return value
        return str(value).lower() == 'true'
    
    def mark_app_initialized(self, updated_by: str = 'system') -> bool:
        """Mark the app as initialized"""
        return self.set_setting('app_initialized', True, updated_by)
    
    def validate_required_settings(self) -> Dict[str, bool]:
        """
        Validate that all required settings are configured
        
        Returns:
            Dictionary of setting keys and whether they are valid
        """
        conn = self._get_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """SELECT setting_key, setting_value, is_required 
                   FROM settings 
                   WHERE is_required = TRUE"""
            )
            results = cursor.fetchall()
            cursor.close()
            
            validation = {}
            for row in results:
                key = row['setting_key']
                value = row['setting_value']
                
                # A required setting is valid if it has a non-empty value
                # Exception: app_initialized can be false
                if key == 'app_initialized':
                    validation[key] = True
                else:
                    validation[key] = bool(value and value.strip())
            
            return validation
        except Error as e:
            logger.error(f"Error validating settings: {e}")
            return {}
    
    def clear_cache(self):
        """Clear the settings cache"""
        self._cache = {}
    
    def __del__(self):
        """Cleanup on deletion"""
        self._close_connection()


# Global instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global ConfigManager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
