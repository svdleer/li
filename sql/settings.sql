-- Settings table for application configuration
-- Stores key-value configuration that can be updated via UI

CREATE TABLE IF NOT EXISTS settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    setting_type ENUM('string', 'integer', 'boolean', 'password') DEFAULT 'string',
    description TEXT,
    is_required BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    INDEX idx_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default settings
INSERT INTO settings (setting_key, setting_value, setting_type, description, is_required) VALUES
    ('mysql_host', '', 'string', 'MySQL database host', TRUE),
    ('mysql_port', '3306', 'integer', 'MySQL database port', TRUE),
    ('mysql_user', '', 'string', 'MySQL database username', TRUE),
    ('mysql_password', '', 'password', 'MySQL database password', TRUE),
    ('mysql_database', '', 'string', 'MySQL database name', TRUE),
    ('netshot_url', '', 'string', 'Netshot API URL (e.g., https://netshot.oss.local/api)', TRUE),
    ('netshot_api_key', '', 'password', 'Netshot API authentication key', TRUE),
    ('netshot_cmts_group', '', 'string', 'Netshot device group name for CMTS devices', TRUE),
    ('netshot_pe_group', '', 'string', 'Netshot device group name for PE devices', TRUE),
    ('app_initialized', 'false', 'boolean', 'Whether initial setup has been completed', TRUE)
ON DUPLICATE KEY UPDATE setting_key=setting_key;
