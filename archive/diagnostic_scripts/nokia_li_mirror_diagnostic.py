"""
Extract LI Mirror Configuration from NOKIA 7750 SR-2s Router
Extracts: configure mirror mirror-dest "LI_MIRROR" encap layer-3-encap gateway ip-address source
Python Diagnostic - Uses cached running config

Author  : Silvester van der Leer
Version : 1.0 
Date    : 07-01-2026

"""
import re
import json

def diagnose(cli, device, diagnostic):
    try:
        # Nokia devices use configurationAsfc
        currentConfig = device.get('configurationAsfc')
        
        result = {
            "LI_LOOPBACK": None
        }
        
        if not currentConfig:
            diagnostic.set(json.dumps(result, indent=2))
            return
        
        # Pattern: /configure mirror mirror-dest "LI_MIRROR" ... gateway ip-address source <IP>
        pattern = r'mirror-dest\s+"LI_MIRROR".*?gateway\s+ip-address\s+source\s+(\d+\.\d+\.\d+\.\d+)'
        match = re.search(pattern, currentConfig, re.IGNORECASE | re.DOTALL)
        if match:
            result["LI_LOOPBACK"] = match.group(1)
        
        # Set the diagnostic result as JSON
        diagnostic.set(json.dumps(result, indent=2))
        
    except Exception as e:
        error_result = {
            "LI_LOOPBACK": None,
            "error": str(e)
        }
        diagnostic.set(json.dumps(error_result, indent=2))
