-- Users table for RBAC
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role ENUM('admin', 'operator', 'viewer') NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default users (only if not exists)
INSERT IGNORE INTO users (email, name, role) VALUES
('admin@example.com', 'Admin User', 'admin'),
('operator@example.com', 'Operator User', 'operator'),
('viewer@example.com', 'Viewer User', 'viewer'),
('demo.user@example.com', 'Demo User', 'operator');
