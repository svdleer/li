# Email Notifications Setup Guide

## Feature Overview

Email notifications have been added to the EVE LI XML Generator. You will now receive email alerts when:
- ✅ XML generation completes successfully
- ❌ XML generation fails with error details

## Configuration

### Option 1: Web Interface (Recommended)

1. Login to the application
2. Go to **Settings** page
3. Scroll to **Email Notifications** section
4. Configure the following:

**Enable/Disable:**
- ☑️ Toggle "Enable Email Notifications" switch

**SMTP Server:**
- **SMTP Host**: `smtp.gmail.com` (or your mail server)
- **SMTP Port**: `587` (for TLS) or `465` (for SSL)
- **SMTP Username**: Your email address
- **SMTP Password**: Your email password or app password
- ☑️ **Use TLS**: Checked (recommended for port 587)

**Email Settings:**
- **From Email**: `noreply@vodafoneziggo.com`
- **From Name**: `EVE LI XML Generator`
- **Recipients**: `admin@vodafoneziggo.com, team@vodafoneziggo.com` (comma-separated)
- **Web URL**: `http://your-server:8080` (link in emails)

4. Click **Save Settings**

### Option 2: Environment Variables

Add to `.env` file:

```bash
# Enable email notifications
EMAIL_ENABLED=true

# SMTP Server
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@vodafoneziggo.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true

# Email Configuration
EMAIL_FROM=noreply@vodafoneziggo.com
EMAIL_FROM_NAME=EVE LI XML Generator
EMAIL_TO=admin@vodafoneziggo.com,team@vodafoneziggo.com
WEB_URL=http://localhost:8080
```

**Note:** Settings in the web interface override environment variables.

## Gmail Setup (if using Gmail)

Gmail requires an "App Password" instead of your regular password:

1. Go to https://myaccount.google.com/
2. Click **Security** (left menu)
3. Enable **2-Step Verification** (if not already enabled)
4. Click **App Passwords**
5. Generate new app password:
   - App: Mail
   - Device: Other (custom name) → "EVE LI XML"
6. Copy the 16-character password
7. Use this password in SMTP Password field

## Testing Email Configuration

Run the test script to verify your setup:

```bash
# Show current configuration
python test_email.py --config

# Test success notification
python test_email.py --success

# Test failure notification
python test_email.py --failure

# Test both
python test_email.py --both
```

**Expected output:**
```
INFO - Sending test email to: admin@vodafoneziggo.com
INFO - Email sent to 1 recipient(s)
INFO - ✅ SUCCESS notification email sent successfully!
```

## Email Format

### Success Email

**Subject:** ✅ EVE LI XML Generation Successful - CMTS (2026-01-10 04:30:15)

**Content:**
- ✅ Status: SUCCESS
- Device Type: CMTS or PE Router
- Timestamp
- Devices Processed: 157
- Generated File: EVE_NL_Infra_CMTS-20260110.xml
- Link to Dashboard

### Failure Email

**Subject:** ❌ EVE LI XML Generation Failed - CMTS (2026-01-10 04:30:15)

**Content:**
- ❌ Status: FAILED
- Device Type: CMTS or PE Router
- Timestamp
- Error Message (detailed error information)
- Link to Dashboard

## Troubleshooting

### No Emails Received

**Check 1: Is it enabled?**
```bash
python test_email.py --config
```
Should show: `Enabled: True`

**Check 2: SMTP credentials correct?**
- Verify username and password
- Gmail: Must use App Password
- Test with: `python test_email.py --success`

**Check 3: Firewall blocking?**
- Port 587 or 465 must be open
- Try: `telnet smtp.gmail.com 587`

**Check 4: Recipients configured?**
```bash
python test_email.py --config
```
Should show email addresses in "Recipients"

### SMTP Authentication Failed

**Gmail:**
- Enable 2-Step Verification
- Generate App Password
- Use App Password (not regular password)

**Corporate Email:**
- Check with IT for SMTP settings
- May require different port or authentication

### Emails Going to Spam

- Add sender email to safe senders list
- Use company domain for "From Email"
- Ask IT to whitelist the sender

### Common Error Messages

**"SMTP AUTH extension not supported"**
- Enable TLS: Check "Use TLS" box in settings

**"Connection refused"**
- Wrong port or SMTP host
- Firewall blocking connection

**"Username and Password not accepted"**
- Wrong credentials
- Gmail: Need App Password, not regular password

**"No recipient emails configured"**
- Add emails to "Recipients" field
- Separate multiple emails with commas

## Multiple Recipients

To send notifications to multiple people:

**In Settings:**
```
Recipients: admin@company.com, user1@company.com, team@company.com
```

**In .env:**
```bash
EMAIL_TO=admin@company.com,user1@company.com,team@company.com
```

## Disabling Notifications

### Temporary (keep settings):
1. Go to Settings
2. Uncheck "Enable Email Notifications"
3. Save Settings

### Permanent:
Remove or comment out in `.env`:
```bash
# EMAIL_ENABLED=true
EMAIL_ENABLED=false
```

## What Gets Notified

Email notifications are sent for:

1. **CMTS XML Generation**
   - Success: After XML file created successfully
   - Failure: If generation fails (Netshot connection, no devices, etc.)

2. **PE XML Generation**
   - Success: After XML file created successfully  
   - Failure: If generation fails

Notifications are sent **automatically** after:
- Scheduled daily generation (cron job)
- Manual generation from web UI
- Command-line generation

## Security Best Practices

1. **Use App Passwords** (Gmail) - Never use your main password
2. **Dedicated Email Account** - Create noreply@company.com for sending
3. **Secure SMTP Password** - Store in config database, not in code
4. **TLS/SSL Encryption** - Always enable TLS for port 587
5. **Limit Recipients** - Only send to necessary people

## Support

If you have issues:

1. Check configuration: `python test_email.py --config`
2. Test emails: `python test_email.py --both`
3. Check logs: `tail -f logs/web_app.log`
4. Verify SMTP settings with your email provider
5. Contact IT if using corporate email server

## Example Configurations

### Gmail
```
SMTP Host: smtp.gmail.com
SMTP Port: 587
Use TLS: ✓
Username: your-email@gmail.com
Password: (16-char app password)
```

### Office 365
```
SMTP Host: smtp.office365.com
SMTP Port: 587
Use TLS: ✓
Username: your-email@company.com
Password: (your O365 password)
```

### Custom SMTP Server
```
SMTP Host: mail.company.com
SMTP Port: 587 or 25
Use TLS: ✓ (if supported)
Username: smtp-user
Password: smtp-password
```

---

**Last Updated:** January 10, 2026  
**Feature Version:** 2.0
