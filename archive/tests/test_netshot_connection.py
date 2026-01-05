#!/usr/bin/env python3
"""Quick test of Netshot API connection"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Show configuration
print("=" * 60)
print("Configuration:")
print(f"  NETSHOT_API_URL: {os.getenv('NETSHOT_API_URL')}")
print(f"  NETSHOT_API_KEY: {os.getenv('NETSHOT_API_KEY')[:10]}..." if os.getenv('NETSHOT_API_KEY') else "  NETSHOT_API_KEY: Not set")
print("=" * 60)

# Test connection
from netshot_api import get_netshot_client

client = get_netshot_client()
if client.test_connection():
    print("✓ Netshot API connection successful!")
else:
    print("✗ Netshot API connection failed!")
