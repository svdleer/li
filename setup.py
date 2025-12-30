#!/usr/bin/env python3
"""
Setup Script for EVE LI XML Generator
=====================================

This script helps set up the EVE LI XML Generator by:
1. Creating necessary directories
2. Copying configuration template
3. Setting up initial configuration
"""

import os
import shutil
from pathlib import Path
import configparser


def setup_directories():
    """Create necessary directories"""
    directories = ['output', 'logs']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"Created directory: {directory}")


def setup_config():
    """Set up configuration file"""
    config_file = 'config.ini'
    template_file = 'config.ini.template'
    
    if os.path.exists(config_file):
        print(f"Configuration file already exists: {config_file}")
        return
        
    if os.path.exists(template_file):
        shutil.copy(template_file, config_file)
        print(f"Copied configuration template to: {config_file}")
        print("Please edit config.ini with your specific settings.")
    else:
        print(f"Configuration template not found: {template_file}")
        print("Creating basic configuration file...")
        
        config = configparser.ConfigParser()
        
        config['DATABASE'] = {
            'host': 'localhost',
            'database': 'your_database',
            'user': 'your_user',
            'password': 'your_password',
            'port': '3306'
        }
        
        config['EMAIL'] = {
            'smtp_server': 'localhost',
            'smtp_port': '587',
            'from_email': 'sender@domain.com',
            'to_email': 'recipient@domain.com',
            'username': '',
            'password': ''
        }
        
        config['UPLOAD'] = {
            'endpoint': 'https://your-upload-endpoint.com/upload',
            'username': 'upload_user',
            'password': 'upload_password',
            'timeout': '60'
        }
        
        config['PATHS'] = {
            'output_dir': 'output',
            'schema_file': 'EVE_IAP_Import.xsd'
        }
        
        config['TRIGGERS'] = {
            'trigger_file': 'trigger.txt',
            'schedule_time': '02:00'
        }
        
        with open(config_file, 'w') as f:
            config.write(f)
            
        print(f"Created basic configuration file: {config_file}")


def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'mysql.connector',
        'lxml',
        'requests',
        'schedule'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nPlease install missing packages using:")
        print("pip install -r requirements.txt")
        return False
    else:
        print("All required packages are installed.")
        return True


def main():
    """Main setup function"""
    print("EVE LI XML Generator Setup")
    print("=" * 30)
    print()
    
    # Create directories
    print("Setting up directories...")
    setup_directories()
    print()
    
    # Setup configuration
    print("Setting up configuration...")
    setup_config()
    print()
    
    # Check dependencies
    print("Checking dependencies...")
    deps_ok = check_dependencies()
    print()
    
    if deps_ok:
        print("Setup completed successfully!")
        print()
        print("Next steps:")
        print("1. Edit config.ini with your database and email settings")
        print("2. Place your EVE_IAP_Import.xsd schema file in the current directory")
        print("3. Test the script: python eve_li_xml_generator.py --mode both")
        print("4. Set up scheduler: python eve_li_xml_generator.py --mode schedule")
    else:
        print("Setup incomplete. Please install missing dependencies first.")


if __name__ == "__main__":
    main()
