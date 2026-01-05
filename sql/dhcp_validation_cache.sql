-- DHCP Validation Cache Table
-- Stores pre-computed DHCP validation results to avoid blocking page loads

CREATE TABLE IF NOT EXISTS dhcp_validation_cache (
    device_name VARCHAR(255) PRIMARY KEY,
    dhcp_hostname VARCHAR(255),
    has_dhcp BOOLEAN DEFAULT FALSE,
    dhcp_scopes_count INT DEFAULT 0,
    missing_in_dhcp JSON,
    matched JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- APScheduler Jobs Table
-- NOTE: This table is automatically created by APScheduler on first run
-- Stores scheduled task configurations (cron schedules, next run times, etc.)
-- No manual creation needed - just for documentation:
--
-- CREATE TABLE IF NOT EXISTS apscheduler_jobs (
--     id VARCHAR(191) PRIMARY KEY,
--     next_run_time DOUBLE,
--     job_state BLOB NOT NULL
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;