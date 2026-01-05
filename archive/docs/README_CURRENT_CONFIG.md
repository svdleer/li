# EVE LI XML Generator - Current Configuration

## Data Sources Configuration

### VFZ Devices (CMTS)
- **Devices**: Retrieved from **API** (https://appdb.oss.local/isw/api)
- **Networks**: Retrieved from **Database** (scopes table)
- **Reason**: API provides device list, but network scopes are better maintained in database

### PE Devices (Routers)  
- **Devices**: Retrieved from **Database** (tblB2B_PE_Routers table)
- **Networks**: Retrieved from **Database** (tblB2B_PE_IP_Blocks table)
- **Reason**: API for PE devices is not fully ready yet

## Verification Mode

**UPLOADS ARE DISABLED** for verification purposes:
- `verification_mode = true` in config.ini
- Files are generated and compressed but not actually uploaded
- Upload is simulated and logged for verification
- To enable actual uploads, set `verification_mode = false`

## Configuration Files

### config.ini.template
Contains the template configuration with:
- API settings (for VFZ devices)
- Database settings (for PE devices and all networks)
- Upload settings (with verification mode enabled)
- Email notification settings

### Database Tables Used
- `devicesnew` - VFZ device information
- `scopes` - VFZ network scopes (IPv4 and IPv6)
- `tblB2B_PE_Routers` - PE device information
- `tblB2B_PE_IP_Blocks` - PE network blocks

## Processing Flow

1. **VFZ Processing**:
   - Get devices from API
   - For each device, get networks from database
   - Generate XML with IPv4 and IPv6 scopes
   - Validate, compress, and simulate upload

2. **PE Processing**:
   - Get devices from database
   - For each device, get networks from database  
   - Generate XML with device-specific attributes
   - Validate, compress, and simulate upload

## IPv6 Validation

Enhanced IP validation supports:
- IPv4 addresses and networks (192.168.1.1, 10.0.0.0/8)
- IPv6 addresses and networks (2001:db8::1, 2001:db8::/32)
- Automatic version detection and normalization
- Detailed logging for validation failures

## Testing

Use the following commands to test:

```bash
# Test API connection and data retrieval
python eve_li_xml_generator.py --mode test

# Generate VFZ XML only (verification mode)
python eve_li_xml_generator.py --mode vfz

# Generate PE XML only (verification mode)  
python eve_li_xml_generator.py --mode pe

# Generate both XMLs (verification mode)
python eve_li_xml_generator.py --mode both

# Test IPv6 validation
python test_ipv6.py
```

## Next Steps

1. **Verify database connection** - Update config.ini with correct database credentials
2. **Test VFZ device retrieval** - Ensure API access to appdb.oss.local
3. **Test PE device retrieval** - Verify database queries work correctly
4. **Check XML output** - Review generated XML files in output/ directory
5. **Validate networks** - Ensure IP address validation works for your data
6. **Enable uploads** - Set `verification_mode = false` when ready for production

## Files Generated

- `output/EVE_NL_Infra_CMTS-YYYYMMDD.xml` - VFZ devices XML
- `output/EVE_NL_Infra_CMTS-YYYYMMDD.xml.gz` - Compressed VFZ XML
- `output/EVE_NL_SOHO-YYYYMMDD.xml` - PE devices XML  
- `output/EVE_NL_SOHO-YYYYMMDD.xml.gz` - Compressed PE XML
- `logs/eve_xml_YYYYMMDD.log` - Detailed processing logs
