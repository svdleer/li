# Codebase Audit - EVE LI XML Generator

**Date**: 5 January 2026  
**Status**: Cleaned and Optimized

## Production Files (14 Core Python Files)

### Core Application
1. **web_app.py** - Main Flask web application (2,200+ lines)
   - User authentication (Office 365 SSO)
   - Dashboard and device management UI
   - REST API endpoints
   - Scheduled task management
   - Configuration interface

2. **eve_li_xml_generator_v2.py** - XML generation engine (519 lines)
   - Generates EVE LI XML files
   - Processes CMTS and PE devices
   - Integrates with Netshot API and DHCP database
   - Validates subnets and IP addresses

3. **netshot_api.py** - Netshot REST API client (985 lines)
   - Fetches device data from Netshot
   - Retrieves loopback interfaces and subnets
   - Smart caching with file-based storage
   - Handles group 207 (CMTS) and 205 (PE)

4. **dhcp_integration.py** - DHCP database integration (391 lines)
   - Cross-references CMTS interfaces with DHCP data
   - Validates subnet assignments
   - MySQL database connectivity

### Configuration & Security
5. **config_manager.py** - Database-backed configuration (287 lines)
   - Stores settings in MySQL database
   - Environment variable fallbacks
   - Settings validation
   - Cache management

6. **rbac.py** - Role-based access control (547 lines)
   - User management (Admin, Operator, Viewer roles)
   - Permission checking
   - Password hashing with bcrypt
   - Session management

7. **audit_logger.py** - Audit trail logging (250+ lines)
   - Tracks all user actions
   - Records system events
   - MySQL-backed audit log
   - Compliance reporting

### Caching & Performance
8. **cache_manager.py** - File-based caching (200+ lines)
   - JSON file caching with TTL
   - Docker volume support
   - Cache invalidation

9. **app_cache.py** - MySQL cache backend (150+ lines)
   - Database-backed device cache
   - Validation data storage
   - Query optimization

### Background Jobs & Utilities
10. **cache_warmer.py** - Cache warming cron job
    - Pre-populates device cache
    - Runs every 15 minutes
    - Improves XML generation performance

11. **dhcp_cache_warmer.py** - DHCP validation cache
    - Keeps DHCP validation data fresh
    - Background processing
    - Scheduled execution

12. **refresh_cache.py** - Manual cache refresh
    - Callable script for cache updates
    - Used by administrators
    - Pre-generation warming

13. **subnet_utils.py** - Subnet validation utilities (129 lines)
    - IP address validation
    - Public/private subnet filtering
    - CIDR calculations

14. **email_notifier.py** - Email notifications (285 lines)
    - HTML email templates
    - Upload status notifications
    - SMTP integration

## Archived Files (Moved to archive/old_code/)

### Obsolete Versions
- **eve_li_xml_generator.py** - Original v1 (replaced by v2)
- **audit_log.py** - Old audit module (replaced by audit_logger)
- **dhcp_database.py** - Standalone interface (replaced by dhcp_integration)

### Debug & Diagnostic Tools
- **netshot_diagnostic.py** - Diagnostic tool for Netshot data
- **encode_credentials.py** - Base64 encoding utility (one-time use)
- **subnet_validator.py** - Standalone validator (now in dhcp_integration)
- **subnet_lookup.py** - Search tool (now in web UI)

### Legacy Scripts
- **setup.py** - Old CLI setup (replaced by web setup wizard)
- **trigger_xml_processing.py** - External trigger (not used in v2)

## Active Scripts (3 Shell Scripts)

1. **deploy-git.sh** - Main deployment script
   - Pulls latest code from Git
   - Builds Docker image
   - Starts/restarts container
   - Shows status and logs

2. **ssh-tunnel.sh** - SSH tunnel for remote access
   - Creates tunnel to remote MySQL/Netshot
   - Required for development/testing
   - Handles port forwarding

3. **refresh_cache.sh** - Cache refresh wrapper
   - Calls refresh_cache.py
   - Cron-compatible
   - Logging support

## Docker Configuration

- **Dockerfile** - Multi-stage Python image
- **docker-compose.yml** - Container orchestration
- **.dockerignore** - Build optimization

## Database Schema

- **sql/users.sql** - User authentication table
- **sql/settings.sql** - Configuration storage
- **sql/dhcp_validation_cache.sql** - DHCP cache table

## Templates (12 HTML files)

- base.html - Base template with navigation
- dashboard.html - Main dashboard
- devices.html - Device browser
- settings.html - Configuration page
- setup.html - Initial setup wizard
- login.html - Authentication
- user_management.html - User admin
- xml_status.html - XML generation status
- health.html - System health
- audit_log.html - Audit trail
- scheduled_tasks.html - Task scheduler
- error.html - Error pages

## Static Assets

- **static/css/style.css** - Custom styles
- **static/js/app.js** - JavaScript functionality
- **static/img/** - Logos and icons

## Dependencies

See **requirements.txt** for full list:
- Flask - Web framework
- requests - HTTP client
- mysql-connector-python - Database
- bcrypt - Password hashing
- python-dotenv - Environment variables
- msal - Microsoft authentication
- APScheduler - Task scheduling

## Total Lines of Code (Production)

- Python: ~6,500 lines
- HTML Templates: ~1,200 lines
- JavaScript: ~400 lines
- CSS: ~600 lines
- Shell Scripts: ~150 lines
- **Total: ~8,850 lines**

## Maintenance Notes

### Regular Tasks
- Review logs: `logs/web_app.log`
- Monitor cache: `.cache/` directory
- Check Docker: `docker logs eve-li-web`
- Review audit log via web UI

### Code Quality
- All production code has docstrings
- Type hints where applicable
- Error handling and logging throughout
- Database connections use context managers
- Environment variables for configuration

### Security
- Passwords hashed with bcrypt
- Role-based access control
- Session management with Flask-Session
- SQL injection prevention (parameterized queries)
- Audit logging for compliance

## Future Considerations

1. **Testing**: Add unit tests for core functions
2. **Monitoring**: Add Prometheus/Grafana metrics
3. **Performance**: Consider Redis for session storage
4. **Documentation**: Add API documentation (OpenAPI/Swagger)
5. **CI/CD**: Add GitHub Actions for automated testing

---

**Maintained by**: Silvester van der Leer  
**Last Updated**: 5 January 2026
