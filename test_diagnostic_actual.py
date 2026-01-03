#!/usr/bin/env python3
"""Test if CMTS_LI_SUBNETS diagnostic actually exists"""
import json
from netshot_api import NetshotAPI

api = NetshotAPI()

# Get device
devices = api.get_cmts_devices()
device = next((d for d in devices if d['name'] == 'AL-RC0263-CCAP001'), None)

if not device:
    print('❌ Device not found')
    exit(1)

device_id = device['id']
print(f'Device: {device["name"]} (ID: {device_id})\n')

# Get diagnostics directly from API
print('=== Fetching diagnostics from Netshot API ===')
response = api._make_request(f'devices/{device_id}/diagnosticresults')

if not response:
    print('❌ No diagnostics response')
    exit(1)

diagnostics = response if isinstance(response, list) else response.get('diagnostics', [])
print(f'Total diagnostics found: {len(diagnostics)}\n')

# Look for CMTS_LI_SUBNETS
cmts_diag = None
for diag in diagnostics:
    diag_name = diag.get('diagnosticName', '')
    if diag_name == 'CMTS_LI_SUBNETS':
        cmts_diag = diag
        break

if cmts_diag:
    print('✅ CMTS_LI_SUBNETS diagnostic EXISTS')
    print(f'\nDiagnostic structure:')
    print(f'  - diagnosticName: {cmts_diag.get("diagnosticName")}')
    print(f'  - type: {cmts_diag.get("type")}')
    print(f'  - status: {cmts_diag.get("status")}')
    
    # Check for text field
    text = cmts_diag.get('text', '')
    print(f'  - text field exists: {bool(text)}')
    print(f'  - text length: {len(text)} chars')
    
    if text:
        print(f'\n--- First 500 chars of text ---')
        print(text[:500])
        print('\n--- Attempting JSON parse ---')
        try:
            data = json.loads(text)
            print('✅ JSON parsed successfully')
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f'❌ JSON parse failed: {e}')
    else:
        print('❌ Text field is empty')
else:
    print('❌ CMTS_LI_SUBNETS diagnostic NOT FOUND')
    print(f'\nAvailable diagnostics:')
    for diag in diagnostics[:10]:
        print(f'  - {diag.get("diagnosticName", "N/A")}')
