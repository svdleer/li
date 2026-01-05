#!/usr/bin/env python3
"""
Email Notification Service
===========================

Sends HTML formatted email notifications for XML upload status

Author: Silvester van der Leer
Version: 1.0
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Email notification service"""
    
    def __init__(self):
        """Initialize email notifier with SMTP settings"""
        self.enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        
        self.from_email = os.getenv('EMAIL_FROM', self.smtp_user)
        self.to_emails = os.getenv('EMAIL_TO', '').split(',')
        self.to_emails = [e.strip() for e in self.to_emails if e.strip()]
        
        self.web_url = os.getenv('WEB_URL', 'http://localhost:8080')
        
        logger.info(f"Email notifier initialized (enabled: {self.enabled})")
    
    def send_email(self, subject: str, html_body: str, text_body: str = None):
        """Send HTML email"""
        if not self.enabled:
            logger.info("Email notifications disabled, skipping")
            return False
        
        if not self.to_emails:
            logger.warning("No recipient emails configured")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Add plain text version as fallback
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            
            # Add HTML version
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {len(self.to_emails)} recipient(s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


def send_upload_status_email(
    success: bool,
    files_uploaded: List[str] = None,
    error_message: str = None,
    stats: dict = None
):
    """
    Send upload status email
    
    Args:
        success: Whether upload was successful
        files_uploaded: List of uploaded file names
        error_message: Error message if failed
        stats: Optional statistics dict
    """
    notifier = EmailNotifier()
    
    if not notifier.enabled:
        return
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if success:
        subject = f"✅ EVE LI XML Upload Successful - {timestamp}"
        status_color = "#28a745"
        status_icon = "✅"
        status_text = "SUCCESS"
    else:
        subject = f"❌ EVE LI XML Upload Failed - {timestamp}"
        status_color = "#dc3545"
        status_icon = "❌"
        status_text = "FAILED"
    
    files_uploaded = files_uploaded or []
    stats = stats or {}
    
    # Build HTML email
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: {status_color};
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f8f9fa;
                padding: 20px;
                border: 1px solid #dee2e6;
                border-top: none;
                border-radius: 0 0 5px 5px;
            }}
            .status {{
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .file-list {{
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
            }}
            .file-item {{
                padding: 5px 0;
                border-bottom: 1px solid #e9ecef;
            }}
            .file-item:last-child {{
                border-bottom: none;
            }}
            .stats {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin: 15px 0;
            }}
            .stat-box {{
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 28px;
                font-weight: bold;
                color: {status_color};
            }}
            .stat-label {{
                font-size: 12px;
                color: #6c757d;
                text-transform: uppercase;
            }}
            .error {{
                background-color: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border: 1px solid #f5c6cb;
            }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 0;
            }}
            .footer {{
                text-align: center;
                color: #6c757d;
                font-size: 12px;
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #dee2e6;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="status">{status_icon} {status_text}</div>
            <div>EVE LI XML Upload Report</div>
        </div>
        
        <div class="content">
            <p><strong>Timestamp:</strong> {timestamp}</p>
            
            {"".join([f'<div class="error"><strong>Error:</strong><br>{error_message}</div>' if error_message else ""])}
            
            {f'''
            <div class="file-list">
                <strong>📁 Files Uploaded ({len(files_uploaded)}):</strong>
                {"".join([f'<div class="file-item">✓ {file}</div>' for file in files_uploaded])}
            </div>
            ''' if files_uploaded else ''}
            
            {f'''
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{stats.get('cmts_count', 0)}</div>
                    <div class="stat-label">CMTS Devices</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{stats.get('pe_count', 0)}</div>
                    <div class="stat-label">PE Devices</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{stats.get('public_subnets', 0)}</div>
                    <div class="stat-label">Public Subnets</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{stats.get('total_devices', 0)}</div>
                    <div class="stat-label">Total Devices</div>
                </div>
            </div>
            ''' if stats else ''}
            
            <p style="text-align: center;">
                <a href="{notifier.web_url}/dashboard" class="button">View Dashboard</a>
            </p>
        </div>
        
        <div class="footer">
            <p>EVE LI XML Generator - Automated Report</p>
            <p>VodafoneZiggo Network Operations</p>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_body = f"""
    EVE LI XML Upload Report
    ========================
    
    Status: {status_text}
    Timestamp: {timestamp}
    
    {'Error: ' + error_message if error_message else ''}
    
    Files Uploaded: {len(files_uploaded)}
    {chr(10).join(['  - ' + f for f in files_uploaded])}
    
    View full report: {notifier.web_url}/dashboard
    """
    
    notifier.send_email(subject, html_body, text_body)


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test success email
    send_upload_status_email(
        success=True,
        files_uploaded=['EVE-LI-CMTS.xml.gz', 'EVE-LI-PE.xml.gz'],
        stats={
            'cmts_count': 142,
            'pe_count': 28,
            'public_subnets': 1247,
            'total_devices': 170
        }
    )
    
    # Test failure email
    send_upload_status_email(
        success=False,
        error_message="Connection timeout to upload server"
    )
