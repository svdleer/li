#!/usr/bin/env python3
"""
Test script for Nokia LI Mirror diagnostic
"""
import re
import json

# Sample Nokia 7750 SR config
sample_config = """
/configure mirror mirror-dest "LI_MIRROR" encap layer-3-encap gateway ip-address source 213.51.63.1
/configure router "Base" interface "system" address 10.1.1.1/32
"""

# Simulate device object
device = {
    'name': 'test-nokia-device',
    'configuration': sample_config
}

# Simulate diagnostic object
class MockDiagnostic:
    def __init__(self):
        self.result = None
    
    def set(self, value):
        self.result = value
        print("Diagnostic Result:")
        print(value)

# Run the diagnostic
diagnostic = MockDiagnostic()

try:
    device_name = device.get('name', 'unknown')
    config = device.get('configuration', '') or device.get('runningConfig', '') or device.get('currentConfig', '')
    
    result = {
        "LI_LOOPBACK": None,
        "debug_config_length": len(config) if config else 0,
        "debug_has_mirror": "LI_MIRROR" in config if config else False
    }
    
    if not config:
        diagnostic.set(json.dumps(result, indent=2))
    else:
        # Pattern: /configure mirror mirror-dest "LI_MIRROR" ... gateway ip-address source <IP>
        pattern = r'mirror-dest\s+"LI_MIRROR".*?gateway\s+ip-address\s+source\s+(\d+\.\d+\.\d+\.\d+)'
        match = re.search(pattern, config, re.IGNORECASE | re.DOTALL)
        if match:
            result["LI_LOOPBACK"] = match.group(1)
            print(f"\nFound IP: {match.group(1)}")
        else:
            print("\nPattern did not match. Testing individual parts:")
            if 'LI_MIRROR' in config:
                print("✓ LI_MIRROR found in config")
            if 'gateway' in config:
                print("✓ gateway found in config")
            if 'ip-address' in config:
                print("✓ ip-address found in config")
            if 'source' in config:
                print("✓ source found in config")
        
        diagnostic.set(json.dumps(result, indent=2))
        
except Exception as e:
    error_result = {
        "LI_LOOPBACK": None,
        "error": str(e)
    }
    diagnostic.set(json.dumps(error_result, indent=2))
