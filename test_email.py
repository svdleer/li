#!/usr/bin/env python3
"""
Email Notification Test Script
===============================

Test email notifications without running full XML generation.
Useful for verifying SMTP settings and email configuration.

Usage:
    python test_email.py --success    # Test success notification
    python test_email.py --failure    # Test failure notification
    python test_email.py --both       # Test both types
"""

import sys
import logging
import argparse
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from email_notifier import EmailNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_success_notification():
    """Test success email notification"""
    logger.info("Testing SUCCESS notification...")
    
    notifier = EmailNotifier()
    
    if not notifier.enabled:
        logger.warning("Email notifications are DISABLED")
        logger.info("Enable them in Settings or set EMAIL_ENABLED=true in .env")
        return False
    
    if not notifier.to_emails:
        logger.error("No recipient email addresses configured")
        logger.info("Add recipients in Settings or set EMAIL_TO in .env")
        return False
    
    logger.info(f"Sending test email to: {', '.join(notifier.to_emails)}")
    
    # Create test email content
    subject = "✅ Test: EVE LI XML Generation Successful"
    
    html_body = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .header { background-color: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px; }
            .content { background-color: #f8f9fa; padding: 20px; margin-top: 10px; border-radius: 5px; }
            .info-box { background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #28a745; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>✅ Test Email - Success Notification</h2>
        </div>
        <div class="content">
            <div class="info-box">
                <p><strong>This is a TEST email notification.</strong></p>
                <p>Device Type: CMTS</p>
                <p>Devices Processed: 157</p>
                <p>Generated File: EVE_NL_Infra_CMTS-20260110.xml</p>
            </div>
            <p>If you received this email, your email notifications are working correctly!</p>
            <p>Configure email settings in the application Settings page.</p>
        </div>
    </body>
    </html>
    """
    
    text_body = """
    Test Email - Success Notification
    ==================================
    
    This is a TEST email notification.
    
    Device Type: CMTS
    Devices Processed: 157
    Generated File: EVE_NL_Infra_CMTS-20260110.xml
    
    If you received this email, your email notifications are working correctly!
    """
    
    success = notifier.send_email(subject, html_body, text_body)
    
    if success:
        logger.info("✅ SUCCESS notification email sent successfully!")
        return True
    else:
        logger.error("❌ Failed to send SUCCESS notification email")
        return False


def test_failure_notification():
    """Test failure email notification"""
    logger.info("Testing FAILURE notification...")
    
    notifier = EmailNotifier()
    
    if not notifier.enabled:
        logger.warning("Email notifications are DISABLED")
        logger.info("Enable them in Settings or set EMAIL_ENABLED=true in .env")
        return False
    
    if not notifier.to_emails:
        logger.error("No recipient email addresses configured")
        logger.info("Add recipients in Settings or set EMAIL_TO in .env")
        return False
    
    logger.info(f"Sending test email to: {', '.join(notifier.to_emails)}")
    
    # Create test email content
    subject = "❌ Test: EVE LI XML Generation Failed"
    
    html_body = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .header { background-color: #dc3545; color: white; padding: 20px; text-align: center; border-radius: 5px; }
            .content { background-color: #f8f9fa; padding: 20px; margin-top: 10px; border-radius: 5px; }
            .error { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>❌ Test Email - Failure Notification</h2>
        </div>
        <div class="content">
            <div class="error">
                <strong>Error:</strong><br>
                This is a simulated error message for testing purposes. 
                Actual errors would show: "Connection timeout to Netshot API" or similar messages.
            </div>
            <p>If you received this email, your failure notifications are working correctly!</p>
            <p>You will receive these alerts when XML generation encounters errors.</p>
        </div>
    </body>
    </html>
    """
    
    text_body = """
    Test Email - Failure Notification
    ==================================
    
    This is a TEST email notification.
    
    Error: This is a simulated error message for testing purposes.
    
    If you received this email, your failure notifications are working correctly!
    """
    
    success = notifier.send_email(subject, html_body, text_body)
    
    if success:
        logger.info("✅ FAILURE notification email sent successfully!")
        return True
    else:
        logger.error("❌ Failed to send FAILURE notification email")
        return False


def show_config():
    """Display current email configuration"""
    logger.info("Current Email Configuration:")
    logger.info("=" * 60)
    
    notifier = EmailNotifier()
    
    logger.info(f"Enabled: {notifier.enabled}")
    logger.info(f"SMTP Host: {notifier.smtp_host}")
    logger.info(f"SMTP Port: {notifier.smtp_port}")
    logger.info(f"SMTP User: {notifier.smtp_user}")
    logger.info(f"SMTP Password: {'***' if notifier.smtp_password else '(not set)'}")
    logger.info(f"Use TLS: {notifier.smtp_use_tls}")
    logger.info(f"From Email: {notifier.from_email}")
    logger.info(f"From Name: {notifier.from_name}")
    logger.info(f"Recipients: {', '.join(notifier.to_emails) if notifier.to_emails else '(none)'}")
    logger.info(f"Web URL: {notifier.web_url}")
    logger.info("=" * 60)


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Test email notifications')
    parser.add_argument('--success', action='store_true', help='Test success notification')
    parser.add_argument('--failure', action='store_true', help='Test failure notification')
    parser.add_argument('--both', action='store_true', help='Test both notifications')
    parser.add_argument('--config', action='store_true', help='Show current configuration')
    
    args = parser.parse_args()
    
    # Show config if requested
    if args.config:
        show_config()
        return
    
    # If no specific test requested, show config and test both
    if not args.success and not args.failure and not args.both:
        show_config()
        args.both = True
        print()
        input("Press Enter to send test emails...")
        print()
    
    # Run tests
    success_count = 0
    failure_count = 0
    
    if args.success or args.both:
        if test_success_notification():
            success_count += 1
        else:
            failure_count += 1
        
        if args.both:
            print()
            import time
            time.sleep(2)  # Brief pause between emails
    
    if args.failure or args.both:
        if test_failure_notification():
            success_count += 1
        else:
            failure_count += 1
    
    # Summary
    print()
    logger.info("=" * 60)
    logger.info(f"Test Summary: {success_count} passed, {failure_count} failed")
    logger.info("=" * 60)
    
    if failure_count > 0:
        logger.error("Some tests failed. Check your email configuration.")
        logger.info("Common issues:")
        logger.info("  - SMTP credentials incorrect")
        logger.info("  - Gmail: Need to use App Password, not regular password")
        logger.info("  - Firewall blocking SMTP port")
        logger.info("  - EMAIL_ENABLED not set to 'true'")
        sys.exit(1)
    else:
        logger.info("✅ All tests passed! Email notifications are working.")
        sys.exit(0)


if __name__ == "__main__":
    main()
