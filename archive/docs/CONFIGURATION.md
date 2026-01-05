# EVE LI XML Generator Configuration

## 🎯 Simple Configuration with .env Only

Following the KISS (Keep It Simple, Stupid) principle, all configuration is now stored in a single `.env` file. No more complex config.ini files!

## 📋 Setup Steps

1. **Copy the template**:
   ```bash
   cp .env.template .env
   ```

2. **Edit your credentials**:
   ```bash
   nano .env
   ```

3. **Update the following key values**:
   ```bash
   # Database (required for PE devices and logging)
   DB_HOST=your_database_host
   DB_DATABASE=your_database_name
   DB_USER=your_database_user
   DB_PASSWORD=your_database_password
   
   # Upload API (required for XML uploads)
   UPLOAD_API_PASSWORD=your_actual_api_password
   
   # Email (required for notifications)
   EMAIL_FROM=your_email@domain.com
   EMAIL_TO=admin@domain.com
   EMAIL_SMTP_SERVER=your_smtp_server
   ```

## 🔧 Complete Configuration Reference

### Database Configuration
```bash
DB_HOST=localhost                    # Database server
DB_DATABASE=your_database           # Database name
DB_USER=your_user                   # Database username
DB_PASSWORD=your_password           # Database password
DB_PORT=3306                        # Database port (default: 3306)
```

### API Configuration
```bash
API_BASE_URL=https://appdb.oss.local/isw/api    # Device API endpoint
API_AUTH_TOKEN=aXN3OlNweWVtX090R2hlYjQ=        # Base64 encoded credentials
API_TIMEOUT=30                                  # API timeout in seconds
```

### Email Configuration
```bash
EMAIL_SMTP_SERVER=localhost         # SMTP server
EMAIL_SMTP_PORT=587                 # SMTP port
EMAIL_FROM=your_email@domain.com    # Sender email
EMAIL_TO=recipient@domain.com       # Recipient email
EMAIL_USERNAME=                     # SMTP username (if required)
EMAIL_PASSWORD=                     # SMTP password (if required)
```

### Upload Configuration
```bash
UPLOAD_API_BASE_URL=https://172.17.130.70:2305    # EVE LI API server
UPLOAD_API_USERNAME=xml_import                     # API username
UPLOAD_API_PASSWORD=your_api_password_here         # API password
UPLOAD_TIMEOUT=600                                 # Upload timeout (10 minutes)
UPLOAD_VERIFICATION_MODE=true                      # true=test mode, false=real uploads
```

### Paths Configuration
```bash
OUTPUT_DIR=output                   # Directory for generated XML files
SCHEMA_FILE=EVE_IAP_Import.xsd     # XML schema file for validation
```

### Triggers Configuration
```bash
TRIGGER_FILE=trigger.txt            # File trigger for manual runs
SCHEDULE_TIME=09:00                 # Daily run time (HH:MM format)
WEEKDAYS_ONLY=true                  # true=weekdays only, false=daily
```

### Logging Configuration
```bash
LOG_TO_DATABASE=true                # Enable database logging
LOG_TABLE=eve_xml_log              # Log table name
STATUS_TABLE=eve_xml_status        # Status table name
```

## 🔒 Security Features

- **Git Safe**: `.env` file is automatically ignored by git
- **No Hardcoded Secrets**: All sensitive data in environment variables
- **Validation**: Script will fail safely if required credentials are missing
- **Environment Specific**: Each deployment can have unique configuration

## 🚀 Benefits of .env Only

- ✅ **Simple**: Single configuration file
- ✅ **Secure**: No credentials in code or version control
- ✅ **Standard**: Industry best practice
- ✅ **Portable**: Easy to deploy across environments
- ✅ **Maintainable**: No complex configuration parsing

## 🧪 Testing Configuration

Run the test script to verify your configuration:
```bash
./test.sh
```

This will check:
- ✅ Virtual environment setup
- ✅ Required dependencies
- ✅ .env file existence and basic validation
- ✅ Directory permissions
- ✅ Python script syntax

## 🔧 Troubleshooting

**"Configuration loaded from environment variables only"** - This is normal! No config.ini file is needed.

**"Environment variable X not found"** - Check your .env file and ensure all required variables are set.

**"Authentication failed"** - Verify your database and API credentials in the .env file.
