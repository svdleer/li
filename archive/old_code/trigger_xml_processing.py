#!/usr/bin/env python3
"""
External Trigger Script for EVE LI XML Generator
================================================

This script can be called by external systems to trigger
XML processing immediately without waiting for scheduled runs.

Usage:
    python trigger_xml_processing.py [--config config.ini]
"""

import argparse
import os
import sys
import time
from pathlib import Path
import configparser


def trigger_processing(config_file: str = "config.ini") -> bool:
    """Trigger XML processing by creating trigger file"""
    
    try:
        # Load configuration
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Get trigger file path
        trigger_file = config.get('TRIGGERS', 'trigger_file', fallback='trigger.txt')
        
        # Create trigger file
        with open(trigger_file, 'w') as f:
            f.write(f"Triggered at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
        print(f"Trigger file created: {trigger_file}")
        print("EVE LI XML processing will start within 1 minute if scheduler is running.")
        
        return True
        
    except Exception as e:
        print(f"Error creating trigger file: {e}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Trigger EVE LI XML processing')
    parser.add_argument('--config', default='config.ini', 
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.config):
        print(f"Configuration file not found: {args.config}")
        sys.exit(1)
        
    success = trigger_processing(args.config)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
