#!/usr/bin/env python3
"""
Base64 Credential Encoder
========================

Simple utility to encode username:password for API authentication.
"""

import base64
import sys


def encode_credentials(username, password):
    """Encode username:password to base64"""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return encoded


def main():
    if len(sys.argv) == 3:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        username = input("Username: ")
        password = input("Password: ")
    
    encoded = encode_credentials(username, password)
    
    print(f"\nCredentials: {username}:{password}")
    print(f"Base64 auth_token: {encoded}")
    print(f"\nConfiguration entry:")
    print(f"auth_token = {encoded}")
    print(f"\nCurl command:")
    print(f"curl -H 'Authorization: Basic {encoded}' 'https://appdb.oss.local/isw/api/search?type=hostname&q=*'")
    print(f"\nAlternative curl command:")
    print(f"curl -u '{username}:{password}' 'https://appdb.oss.local/isw/api/search?type=hostname&q=*'")


if __name__ == "__main__":
    main()
