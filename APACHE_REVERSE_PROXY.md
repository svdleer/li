# Apache Reverse Proxy Configuration

## Setup for Subpath: https://domain.com/li-xml/

### 1. Apache Configuration

Add to your Apache VirtualHost config:

```apache
<VirtualHost *:443>
    ServerName domain.com
    
    SSLEngine on
    SSLCertificateFile /path/to/cert.pem
    SSLCertificateKeyFile /path/to/key.pem
    
    # Reverse proxy for LI XML application
    ProxyPreserveHost On
    
    # Location block handles both path matching and proxying
    <Location /li-xml>
        # Strip /li-xml prefix when forwarding to Flask
        ProxyPass http://localhost:8502/
        ProxyPassReverse http://localhost:8502/
        
        # Tell Flask the prefix for URL generation
        RequestHeader set SCRIPT_NAME "/li-xml"
        RequestHeader set X-Forwarded-Proto "https"
        RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"
    </Location>
</VirtualHost>
```

### Important: Path Rewriting

The `<Location>` block handles everything:
- User visits: `https://domain.com/li-xml/login`
- Apache forwards: `http://localhost:8502/login` (prefix stripped by Location)
- Flask processes: `/login` route
- Flask generates URLs: `/li-xml/login` (using SCRIPT_NAME)

Enable required Apache modules:
```bash
sudo a2enmod proxy proxy_http headers ssl
sudo systemctl restart apache2
```

### 2. Application Configuration

The app is already configured to work at `/li-xml` by default.

To change the subpath, set the `APPLICATION_ROOT` environment variable in `.env`:

```bash
APPLICATION_ROOT=/custom-path
```

Or in docker-compose.yml:
```yaml
environment:
  - APPLICATION_ROOT=/custom-path
```

### 3. Test the Setup

1. Access the application at: `https://domain.com/li-xml/`
2. Check that all links, forms, and static files work correctly
3. Verify login redirects work properly

### Troubleshooting

**Issue**: Static files not loading  
**Solution**: Make sure `ProxyPass` includes the full path without trailing slash

**Issue**: Redirects go to wrong URL  
**Solution**: Verify `ProxyPassReverse` is set correctly and `X-Forwarded-Prefix` header is sent

**Issue**: Session issues  
**Solution**: Check that cookies are being set with the correct path
