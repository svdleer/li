# EVE LI XML Upload System

## Overview

The Python script now includes the complete upload functionality that was previously handled by the separate Perl scripts:
- `infraxmlupload.pl` (Infrastructure/PE uploads)
- `sohoxmlupload.pl` (SOHO/VFZ uploads)

## Upload Types

### 1. VFZ (SOHO) Uploads
- **XML Type**: `vfz`
- **IAP Groups**: `[3]`
- **Source File**: `EVE_NL_SOHO-YYYYMMDD.xml`
- **Original Perl Script**: `sohoxmlupload.pl`

### 2. PE (Infrastructure) Uploads
- **XML Type**: `pe`
- **IAP Groups**: `[1, 4, 15]`
- **Source File**: `EVE_NL_Infra_CMTS-YYYYMMDD.xml`
- **Original Perl Script**: `infraxmlupload.pl`

## Upload Process

The upload process follows the exact same method as the original Perl scripts:

1. **Authentication**
   - POST to: `https://172.17.130.70:2305/api/1/accounts/actions/login/`
   - Credentials: `{"username": "xml_import", "password": "..."}`
   - Extract CSRF token from response cookies

2. **XML Upload**
   - POST to: `https://172.17.130.70:2305/api/1/iaps/actions/import_xml/`
   - Headers:
     - `Content-Type: application/json`
     - `X-CSRFToken: <extracted_token>`
     - `Referer: https://172.17.130.70:2305`
   - Payload:
     ```json
     {
       "iap_groups": [1,4,15],  // or [3] for VFZ
       "xml": "<escaped_xml_content>"
     }
     ```

## Configuration

### Environment Variables (.env file)
```bash
# Upload API Configuration
UPLOAD_API_BASE_URL=https://172.17.130.70:2305
UPLOAD_API_USERNAME=xml_import
UPLOAD_API_PASSWORD=your_actual_api_password_here
UPLOAD_TIMEOUT=600
UPLOAD_VERIFICATION_MODE=true
```

**Note**: All configuration is now stored in the `.env` file for security and simplicity.

## Security Features

- **SSL Verification**: Disabled (matches Perl scripts)
- **Cookie Handling**: Automatic session management
- **CSRF Protection**: Token extraction and inclusion
- **Timeout**: 600 seconds (10 minutes)
- **Error Handling**: Comprehensive logging and status tracking

## Logging

All upload activities are logged with:
- Authentication attempts and results
- CSRF token extraction
- Upload requests and responses
- Success/failure status
- Error messages and debugging information

## Migration from Perl

The Python implementation provides:
- **Identical Functionality**: Same API endpoints, headers, and payload structure
- **Enhanced Logging**: Better error tracking and debugging
- **Database Integration**: Status tracking in MySQL
- **Email Notifications**: Automatic reports on success/failure
- **Unified Processing**: Both upload types in single script

## Testing

Test the upload functionality:
```bash
# Run comprehensive tests
./test.sh

# Test specific XML type
python3 eve_li_xml_generator.py --process-vfz
python3 eve_li_xml_generator.py --process-pe
```

## Troubleshooting

Common issues:
1. **Authentication Failure**: Check credentials in .env file
2. **CSRF Token Missing**: Verify login response and cookie handling
3. **Upload Timeout**: Increase timeout value for large files
4. **SSL Errors**: Verification is disabled by design (matches Perl)

The script provides detailed logging to help diagnose any upload issues.
