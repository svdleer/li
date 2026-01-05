#!/usr/bin/env python3
"""
Simple API Test Script
======================

Test the API connection independently to see the actual response structure.
This helps with debugging and understanding the API data format.
"""

import requests
import json
import sys
import base64


def test_api(auth_token=None):
    """Test the API and show response"""
    
    # API configuration
    base_url = "https://appdb.oss.local/isw/api"
    auth_token = auth_token or "aXN3OlNweWVtX090R2hlYjQ="
    
    # Test endpoint
    url = f"{base_url}/search"
    params = {
        'type': 'hostname',
        'q': '*'
    }
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Basic {auth_token}'
    }
    
    # Decode token for display purposes only
    try:
        decoded = base64.b64decode(auth_token).decode('utf-8')
        username, password = decoded.split(':', 1)
    except:
        username, password = "unknown", "unknown"
    
    print(f"Testing API: {url}")
    print(f"Parameters: {params}")
    print(f"Auth Token: {auth_token}")
    print(f"Decoded credentials: {username}:{password}")
    print(f"Using curl equivalent: curl -H 'Authorization: Basic {auth_token}' '{url}?type=hostname&q=*'")
    print("-" * 50)
    
    try:
        # Make request using Authorization header with pre-encoded token
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30,
            verify=False  # Skip SSL verification for testing
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print("-" * 50)
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response Type: {type(data)}")
                
                if isinstance(data, list):
                    print(f"Number of items: {len(data)}")
                    if len(data) > 0:
                        print(f"First item structure:")
                        print(json.dumps(data[0], indent=2))
                        print("-" * 30)
                        print("All field names in first item:")
                        if isinstance(data[0], dict):
                            for key in sorted(data[0].keys()):
                                print(f"  {key}: {type(data[0][key])}")
                elif isinstance(data, dict):
                    print(f"Single object structure:")
                    print(json.dumps(data, indent=2))
                else:
                    print(f"Unexpected data type: {type(data)}")
                    print(f"Raw data: {data}")
                    
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                print(f"Raw response: {response.text[:1000]}...")
                
        elif response.status_code == 401:
            print(f"Authentication failed!")
            try:
                error_data = response.json()
                print("Error details:")
                print(json.dumps(error_data, indent=2))
                if "authentication" in error_data:
                    auth_info = error_data["authentication"]
                    print(f"\nRequired authentication type: {auth_info.get('type', 'Unknown')}")
                    print(f"Format: {auth_info.get('format', 'Unknown')}")
                    if "help" in auth_info:
                        print(f"Help: {auth_info['help']}")
            except json.JSONDecodeError:
                print(f"Raw error response: {response.text}")
        else:
            print(f"Request failed: {response.status_code}")
            try:
                error_data = response.json()
                print("Error response:")
                print(json.dumps(error_data, indent=2))
            except json.JSONDecodeError:
                print(f"Raw response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
        
    return response.status_code == 200


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test API connection')
    parser.add_argument('--token', '-t', help='Base64 encoded auth token')
    
    args = parser.parse_args()
    
    success = test_api(args.token)
    
    if not success:
        print("\n" + "="*50)
        print("AUTHENTICATION FAILED!")
        print("="*50)
        print("The API returned a 401 error. This means:")
        print("1. The username/password combination is incorrect")
        print("2. The account might be disabled or locked")
        print("3. The API might require different credentials")
        print("\nPlease verify:")
        print("- Correct username and password")
        print("- Account is active and has API access")
        print("- Network connectivity to appdb.oss.local")
        print("\nTry running with different auth token:")
        print("python test_api.py --token YOUR_BASE64_TOKEN")
    
    sys.exit(0 if success else 1)
