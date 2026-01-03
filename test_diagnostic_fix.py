#!/usr/bin/env python3
"""Test if diagnostic loading works for AL-RC0263-CCAP001"""
import json
from netshot_api import NetshotAPI

# Initialize API
api = NetshotAPI()

# Get all CMTS devices
devices = api.get_cmts_devices()
device = next((d for d in devices if d['name'] == 'AL-RC0263-CCAP001'), None)

if not device:
    print('❌ Device AL-RC0263-CCAP001 not found')
    exit(1)

device_id = device['id']
print(f'✅ Found device: {device["name"]} (ID: {device_id})')

# Test get_device_subnets (this is what the web app uses)
print('\n--- Testing get_device_subnets() ---')
subnets = api.get_device_subnets(device_id, device['name'])
print(f'Subnets returned: {subnets}')

if subnets:
    print(f'✅ SUCCESS: Found {len(subnets)} subnets')
    for subnet in subnets:
        print(f'  - {subnet}')
else:
    print('❌ FAILED: No subnets returned')
    
    # Debug: Get diagnostics directly
    print('\n--- Debug: Getting diagnostics directly ---')
    response = api._make_request(f'devices/{device_id}/diagnostics')
    
    if response:
        diagnostics = response if isinstance(response, list) else response.get('diagnostics', [])
        print(f'Found {len(diagnostics)} diagnostics total:')
        
        for diag in diagnostics[:5]:  # Show first 5
            print(f'  - {diag.get("diagnosticName", "N/A")}')
        
        # Look specifically for CMTS_LI_SUBNETS
        cmts_diag = next((d for d in diagnostics if d.get('diagnosticName') == 'CMTS_LI_SUBNETS'), None)
        
        if cmts_diag:
            print(f'\n✅ Found CMTS_LI_SUBNETS diagnostic')
            text = cmts_diag.get('text', '')
            print(f'Text field length: {len(text)} chars')
            
            if text:
                try:
                    data = json.loads(text)
                    print(f'✅ Successfully parsed JSON')
                    print(f'Data: {json.dumps(data, indent=2)}')
                except Exception as e:
                    print(f'❌ Failed to parse JSON: {e}')
                    print(f'Raw text: {text[:500]}')
            else:
                print('❌ Text field is empty')
        else:
            print('❌ CMTS_LI_SUBNETS diagnostic not found')
    else:
        print('❌ Failed to get diagnostics from API')
