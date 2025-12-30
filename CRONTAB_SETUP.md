# EVE LI XML Generator - Crontab and Manual Trigger Setup (Linux)

## Overview
The script now supports:
- **Crontab execution**: Runs automatically on weekdays at 9:00 AM
- **Manual triggers**: VFZ (CMTS) XML can be triggered manually via database flag
- **Progress tracking**: All activity logged to MySQL for PHP status page monitoring
- **Upload status**: Track success/failure of uploads with detailed responses
- **Virtual environment**: Uses `/home/svdleer/python/venv` for isolated Python environment

## Prerequisites

### Virtual Environment Setup
```bash
# Create virtual environment (if not exists)
python3 -m venv /home/svdleer/python/venv

# Activate virtual environment
source /home/svdleer/python/venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Installation
```bash
# Make scripts executable
chmod +x setup.sh run.sh test.sh eve_li_xml_generator.py

# Run setup
./setup.sh

# Test installation
./test.sh
```

## Crontab Configuration

### Basic Setup (Recommended)
```bash
# Edit crontab
crontab -e

# Add this line for weekday 9:00 AM runs
0 9 * * 1-5 /home/svdleer/eve_li_xml_generator/run.sh --mode cron
```

### Enhanced Setup (with frequent manual trigger checks)
```bash
# Main scheduled run at 9:00 AM on weekdays
0 9 * * 1-5 /home/svdleer/eve_li_xml_generator/run.sh --mode cron

# Check for manual triggers every 15 minutes during business hours
*/15 8-18 * * 1-5 /home/svdleer/eve_li_xml_generator/run.sh --mode cron
```

### Alternative (direct activation)
```bash
# If you prefer not to use the wrapper script
0 9 * * 1-5 source /home/svdleer/python/venv/bin/activate && python /home/svdleer/eve_li_xml_generator/eve_li_xml_generator.py --mode cron
```

### Verify Crontab
```bash
# List current crontab
crontab -l

# Check cron service status
systemctl status cron

# Monitor cron logs
tail -f /var/log/cron
# or
journalctl -u cron -f
```

## Manual Trigger System

### Database Tables Created Automatically:
1. **eve_xml_trigger** - Manual trigger requests
2. **eve_xml_status** - Current processing status  
3. **eve_xml_log** - Detailed activity logs

## Manual Trigger System

### Database Tables Created Automatically:
1. **eve_xml_trigger** - Manual trigger requests
2. **eve_xml_status** - Current processing status  
3. **eve_xml_log** - Detailed activity logs

### Trigger VFZ Processing Manually:

#### Via SQL:
```sql
INSERT INTO eve_xml_trigger (xml_type, triggered_by) VALUES ('vfz', 'your_name');
```

#### Via PHP Status Page:
- Open `status.php` in web browser
- Fill in "Triggered by" field
- Click "Trigger VFZ Processing"

#### Via Command Line:
```bash
# Direct run (bypasses schedule check)
./run.sh --mode vfz

# Or insert trigger and let cron pick it up
mysql -u user -p database -e "INSERT INTO eve_xml_trigger (xml_type, triggered_by) VALUES ('vfz', 'command_line');"
```

## Operation Modes

### Cron Mode (`--mode cron`)
- **Purpose**: Designed for crontab execution
- **Behavior**: 
  - Checks for manual VFZ triggers first
  - If manual trigger found: runs VFZ only
  - If scheduled time (weekdays 9:00 AM ±15 min): runs both VFZ and PE
  - Otherwise: exits silently
- **Logging**: All activity logged to database and files

### Other Modes
- `--mode vfz`: Force VFZ processing only
- `--mode pe`: Force PE processing only  
- `--mode both`: Force both VFZ and PE processing
- `--mode test`: Test API connections and show sample data
- `--mode schedule`: Legacy continuous scheduler (not recommended for cron)

## Status Monitoring

### PHP Status Page (status.php)
- **Real-time status**: Shows current processing status
- **Progress tracking**: Step-by-step progress (getting devices → generating XML → uploading)
- **Manual trigger**: Web interface to trigger VFZ processing
- **Recent logs**: Last 24 hours of activity
- **Auto-refresh**: Updates every 30 seconds

### Database Queries

#### Check Current Status:
```sql
SELECT xml_type, status, started_at, completed_at, device_count, upload_status 
FROM eve_xml_status;
```

#### Check Recent Activity:
```sql
SELECT timestamp, level, xml_type, message 
FROM eve_xml_log 
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR) 
ORDER BY timestamp DESC;
```

#### Check Pending Triggers:
```sql
SELECT xml_type, triggered_by, triggered_at 
FROM eve_xml_trigger 
WHERE processed = 0;
```

## File Locations

### Generated Files:
- **VFZ XML**: `output/EVE_NL_Infra_CMTS-YYYYMMDD.xml`
- **PE XML**: `output/EVE_NL_SOHO-YYYYMMDD.xml`
- **Compressed**: `*.xml.gz` files for upload
- **Logs**: `logs/eve_xml_YYYYMMDD.log`

### Configuration:
- **Main config**: `config.ini`
- **PHP config**: Update database credentials in `status.php`

## Troubleshooting

### Check if cron is working:
```bash
# Check cron service
systemctl status cron

# Check recent cron jobs
grep CRON /var/log/syslog | tail -20

# Check script logs
tail -50 logs/eve_xml_$(date +%Y%m%d).log
```

### Common Issues:
1. **Python path**: Use full path `/usr/bin/python3`
2. **Script path**: Use full path to script
3. **Permissions**: Ensure cron user can read config and write to output/logs
4. **Database access**: Verify database credentials in config.ini
5. **Time zone**: Cron uses system timezone

### Manual Testing:
```bash
# Test cron mode manually
./run.sh --mode cron

# Test with specific config
./run.sh --mode cron --config /full/path/config.ini

# Test API connections
./run.sh --mode test

# Run full test suite
./test.sh
```

### File Permissions:
```bash
# Make scripts executable
chmod +x setup.sh run.sh test.sh eve_li_xml_generator.py

# Check log directory permissions
ls -la logs/

# Check output directory permissions  
ls -la output/
```

## Security Notes

- Database credentials stored in config.ini
- PHP status page requires database access
- Consider restricting PHP page access via .htaccess
- Upload credentials can be verified in verification_mode before enabling
- All sensitive operations logged for audit trail
