# EVE LI XML Generator

A Python script that replaces the original Perl scripts (`evexml.pl` and `shoxml.pl`) for generating EVE LI XML files with enhanced features.

## Features

- **REST API Int6. **Email Not Sent**
   - Verify SMTP server settings
   - Check authentication if required
   - Test SMTP connectivity

### Debug Mode

For debugging, check the daily log files in the `logs/` directory. The logs contain detailed information about each processing step, including API responses and any authentication issues.**: Gets device data from REST API
- **IP Address Validation**: Validates all IP addresses and subnets before adding them to XML
- **Gzip Compression**: Automatically compresses XML files before upload
- **External Triggers**: Supports external trigger files to initiate processing
- **Detailed Logging**: Comprehensive logging with server response messages
- **Email Notifications**: Sends detailed email reports with processing status
- **XML Schema Validation**: Validates generated XML against schema (requires xmllint)
- **Unified Script**: Handles both VFZ (Infrastructure) and PE (SOHO) device processing

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Copy the configuration template:
```bash
copy config.ini.template config.ini
```

3. Edit `config.ini` with your specific settings:
   - Database connection details
   - Email server settings
   - Upload endpoint configuration
   - File paths and scheduling options

## Configuration

### API Section
```ini
[API]
base_url = https://appdb.oss.local/isw/api
username = isw
password = SpyEm_OtGheb4
timeout = 30
```

### Email Section
```ini
[EMAIL]
smtp_server = localhost
smtp_port = 587
from_email = sender@domain.com
to_email = recipient@domain.com
username = smtp_username
password = smtp_password
```

### Upload Section
```ini
[UPLOAD]
endpoint = https://your-upload-server.com/upload
username = upload_user
password = upload_password
timeout = 60
```

### Paths Section
```ini
[PATHS]
output_dir = output
schema_file = EVE_IAP_Import.xsd
```

### Triggers Section
```ini
[TRIGGERS]
trigger_file = trigger.txt
schedule_time = 02:00
```

## Usage

### Command Line Options

Test API connection and show sample data:
```bash
python eve_li_xml_generator.py --mode test
```

Run VFZ (Infrastructure) processing only:
```bash
python eve_li_xml_generator.py --mode vfz
```

Run PE (SOHO) processing only:
```bash
python eve_li_xml_generator.py --mode pe
```

Run both VFZ and PE processing:
```bash
python eve_li_xml_generator.py --mode both
```

Run in scheduler mode (continuous operation):
```bash
python eve_li_xml_generator.py --mode schedule
```

Use custom configuration file:
```bash
python eve_li_xml_generator.py --config custom_config.ini
```

### External Triggers

To trigger processing externally, simply create the trigger file specified in your configuration:

```bash
echo "trigger" > trigger.txt
```

The script will detect this file (when running in scheduler mode), process the XML files, and automatically remove the trigger file.

### Scheduled Processing

When running in scheduler mode, the script will:
1. Run daily at the specified time (default: 02:00)
2. Check every minute for trigger files
3. Process both VFZ and PE XML files
4. Send email notifications with results

## Output Files

The script generates the following files:

### XML Files
- `EVE_NL_Infra_CMTS-YYYYMMDD.xml` - VFZ infrastructure devices
- `EVE_NL_SOHO-YYYYMMDD.xml` - PE SOHO devices

### Compressed Files
- `EVE_NL_Infra_CMTS-YYYYMMDD.xml.gz` - Compressed VFZ XML
- `EVE_NL_SOHO-YYYYMMDD.xml.gz` - Compressed PE XML

### Log Files
- `logs/eve_xml_YYYYMMDD.log` - Daily log files with detailed processing information

## Data Sources

The script uses REST API endpoints to retrieve device information:

### Primary Data Source: REST API
- **Endpoint**: `https://appdb.oss.local/isw/api/search?type=hostname&q=*`
- **Authentication**: Basic Auth (username: isw)
- **Response**: JSON array/object containing device information

### Device Categorization
Devices are automatically categorized as VFZ or PE based on:
- Hostname patterns (cmts, ccap, pe-, router, etc.)
- Device type fields
- Presence of specific attributes

## API Response Structure

The script expects the API to return device objects with these fields (adjust the `_process_api_device` method based on your actual API structure):

```json
{
  "hostname": "device-name",
  "loopbackip": "192.168.1.1",
  "management_ip": "192.168.1.1",  // alternative IP field
  "type": "cmts",  // or "router", "pe", etc.
  "device_type": "cisco-xr",
  "port": 830,
  "dtcp_version": 2,
  "list_flags": "some_flags",
  "ifindex": "GigabitEthernet0/0/0/1",
  "active": "1"
}
```

## Troubleshooting

### Common Issues

1. **API Authentication Failed**
   - Check API credentials in config.ini
   - Verify username and password are correct
   - Check if account has API access permissions

2. **API Connection Failed**
   - Verify API endpoint URL is correct
   - Check network connectivity to API server
   - Verify SSL/TLS certificates if required

3. **Schema Validation Skipped**
   - Install xmllint (libxml2-utils on Ubuntu/Debian)
   - Ensure schema file path is correct

3. **Upload Failed**
   - Verify upload endpoint URL
   - Check authentication credentials
   - Test network connectivity

4. **Email Not Sent**
   - Verify SMTP server settings
   - Check authentication if required
   - Test SMTP connectivity

### Debug Mode

For debugging, check the daily log files in the `logs/` directory. The logs contain detailed information about each processing step.

## License

GPL v2 - Same as original Perl scripts
