-- EVE LI XML Generator - Application Database Schema
-- Database: li_xml
-- Purpose: Application cache, device validation, audit logs

CREATE DATABASE IF NOT EXISTS li_xml CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE li_xml;

-- Generic cache table for all application data
CREATE TABLE IF NOT EXISTS cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    cache_type VARCHAR(50) NOT NULL,
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    INDEX idx_type (cache_type),
    INDEX idx_expires (expires_at),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Cache types:
-- 'device_list' - Cached CMTS device list from Netshot
-- 'device_validation' - DHCP validation results per device
-- 'device_subnets' - Device subnet data
-- 'device_loopback' - Device loopback interfaces

-- Audit log for user actions
CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR(100),
    action VARCHAR(100),
    details JSON,
    ip_address VARCHAR(45),
    INDEX idx_timestamp (timestamp),
    INDEX idx_username (username),
    INDEX idx_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Background job status tracking
CREATE TABLE IF NOT EXISTS job_status (
    job_name VARCHAR(100) PRIMARY KEY,
    last_run TIMESTAMP NULL,
    last_success TIMESTAMP NULL,
    last_error TIMESTAMP NULL,
    error_message TEXT,
    run_count INT DEFAULT 0,
    success_count INT DEFAULT 0,
    fail_count INT DEFAULT 0,
    is_running BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create application user (run manually with appropriate privileges)
-- CREATE USER IF NOT EXISTS 'li_xml_user'@'localhost' IDENTIFIED BY 'your_password_here';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON li_xml.* TO 'li_xml_user'@'localhost';
-- FLUSH PRIVILEGES;
