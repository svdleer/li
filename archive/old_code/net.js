            try {
                    var displayinterface = cli.command("show ip interface brief");
                    
                    // Pattern to match Loopback interfaces with NVRAM and up/up status
                    // Example: Loopback0              213.51.255.128  YES NVRAM  up                    up
                    var loopbackPattern = /^(Loopback\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+\S+\s+NVRAM\s+up\s+up/gmi;
                    var matchinterface;

                    while (matchinterface = loopbackPattern.exec(displayinterface)) {
                            var ipAddress = matchinterface[2];
                            
                            // Only process if IP address contains "213"
                            if (ipAddress.indexOf("213") !== -1) {
                                    var interface1 = {
                                            name: matchinterface[1],
                                            vrf: "",
                                            ip: [],
                                            mac: "0000.0000.0000"
                                    };

                                    interface1.ip.push({
                                            ip: ipAddress,
                                            mask: 32,  // Loopback interfaces are typically /32
                                    });

                                    device.add("networkInterface", interface1);
                            }
                    }
            }

            catch (e) {
                            device.set("networkInterface", "Error in Networkinterface");
                    }



