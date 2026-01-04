function diagnose(cli, device, diagnostic) {
	var device_driver = device.get('type');
	var local_accounts = []
    
    
	if (device_driver == 'Cisco IOS-XR'){
		var currentConfig = device.get('configuration');
        var pattern = /(BG_B2B_CEN|BG_B2B_INCA).*/gm;
		var match = currentConfig.match(pattern);
        if(match) {
            service_pe = "Yes"
        }
        else {
            service_pe = "???"
        }
	}
	
	else if (device_driver == 'Nokia_TimOS Model Driven'){
		var currentConfig = device.get('configurationAsfc');
        var pattern = /(BSOD|101100|BISF);
		var match = currentConfig.match(pattern);
        if(match) {
            service_pe = "Yes"
        }
        else {
            service_pe = "TBD"
        }
	}
	
	else {
	    service_pe = "No"
	}
	
	diagnostic.set(service_pe);
    
}