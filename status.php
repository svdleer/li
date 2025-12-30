<?php
/**
 * EVE LI XML Generator Status Page
 * 
 * Displays current status and logs for VFZ and PE XML processing
 * Shows progress, upload status, and allows manual trigger for VFZ
 * 
 * Configuration can be loaded from .env file or set directly below
 */

// Load environment variables from .env file if it exists
function loadEnv($path) {
    if (!file_exists($path)) {
        return;
    }
    
    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strpos(trim($line), '#') === 0) {
            continue; // Skip comments
        }
        
        list($name, $value) = explode('=', $line, 2);
        $name = trim($name);
        $value = trim($value);
        
        if (!array_key_exists($name, $_ENV)) {
            $_ENV[$name] = $value;
        }
    }
}

// Load .env file
loadEnv(__DIR__ . '/.env');

// Database configuration - tries .env first, then fallback
$db_config = [
    'host' => $_ENV['DB_HOST'] ?? 'localhost',
    'database' => $_ENV['DB_DATABASE'] ?? 'your_database',
    'username' => $_ENV['DB_USER'] ?? 'your_user',
    'password' => $_ENV['DB_PASSWORD'] ?? 'your_password'
];

// Connect to database
try {
    $pdo = new PDO(
        "mysql:host={$db_config['host']};dbname={$db_config['database']}", 
        $db_config['username'], 
        $db_config['password']
    );
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch(PDOException $e) {
    die("Connection failed: " . $e->getMessage());
}

// Handle manual trigger request
if ($_POST['action'] === 'trigger_vfz' && $_POST['confirm'] === 'yes') {
    try {
        $stmt = $pdo->prepare("INSERT INTO eve_xml_trigger (xml_type, triggered_by) VALUES ('vfz', ?)");
        $stmt->execute([$_POST['triggered_by'] ?: 'web_interface']);
        $trigger_success = true;
        $trigger_message = "VFZ processing trigger created successfully";
    } catch(PDOException $e) {
        $trigger_success = false;
        $trigger_message = "Failed to create trigger: " . $e->getMessage();
    }
}

// Get current status
$status_query = "SELECT * FROM eve_xml_status ORDER BY xml_type";
$status_result = $pdo->query($status_query);
$statuses = $status_result->fetchAll(PDO::FETCH_ASSOC);

// Get recent logs
$logs_query = "SELECT * FROM eve_xml_log WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR) ORDER BY timestamp DESC LIMIT 100";
$logs_result = $pdo->query($logs_query);
$logs = $logs_result->fetchAll(PDO::FETCH_ASSOC);

// Get pending triggers
$triggers_query = "SELECT * FROM eve_xml_trigger WHERE processed = 0 ORDER BY triggered_at DESC";
$triggers_result = $pdo->query($triggers_query);
$pending_triggers = $triggers_result->fetchAll(PDO::FETCH_ASSOC);

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EVE LI XML Generator Status</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .status-item { padding: 15px; border-radius: 5px; }
        .status-completed { background: #d4edda; border: 1px solid #c3e6cb; }
        .status-running { background: #fff3cd; border: 1px solid #ffeaa7; }
        .status-failed { background: #f8d7da; border: 1px solid #f5c6cb; }
        .status-idle { background: #e2e3e5; border: 1px solid #d6d8db; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .log-level-INFO { color: #0066cc; }
        .log-level-WARNING { color: #ff9900; }
        .log-level-ERROR { color: #cc0000; }
        .log-level-DEBUG { color: #666666; }
        .trigger-form { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .btn { padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }
        .btn-warning { background: #ffc107; color: #212529; }
        .btn-danger { background: #dc3545; color: white; }
        .alert { padding: 15px; margin: 10px 0; border-radius: 5px; }
        .alert-success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .alert-danger { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .refresh-info { text-align: right; color: #666; font-size: 0.9em; }
        .file-info { font-family: monospace; font-size: 0.9em; }
    </style>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(function() {
            window.location.reload();
        }, 30000);
        
        function confirmTrigger() {
            return confirm('Are you sure you want to trigger VFZ XML processing? This will run immediately.');
        }
        
        function formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>EVE LI XML Generator Status</h1>
        <div class="refresh-info">Last updated: <?= date('Y-m-d H:i:s') ?> | Auto-refresh: 30s</div>
        
        <?php if (isset($trigger_success)): ?>
            <div class="alert <?= $trigger_success ? 'alert-success' : 'alert-danger' ?>">
                <?= htmlspecialchars($trigger_message) ?>
            </div>
        <?php endif; ?>
        
        <div class="card">
            <h2>Current Status</h2>
            <div class="status-grid">
                <?php foreach ($statuses as $status): ?>
                    <?php
                    $status_class = 'status-idle';
                    switch($status['status']) {
                        case 'completed': $status_class = 'status-completed'; break;
                        case 'failed': 
                        case 'upload_failed': $status_class = 'status-failed'; break;
                        case 'starting':
                        case 'getting_devices':
                        case 'generating_xml':
                        case 'validating':
                        case 'compressing':
                        case 'uploading': $status_class = 'status-running'; break;
                    }
                    ?>
                    <div class="status-item <?= $status_class ?>">
                        <h3><?= strtoupper($status['xml_type']) ?> Processing</h3>
                        <p><strong>Status:</strong> <?= ucfirst(str_replace('_', ' ', $status['status'])) ?></p>
                        <?php if ($status['started_at']): ?>
                            <p><strong>Started:</strong> <?= $status['started_at'] ?></p>
                        <?php endif; ?>
                        <?php if ($status['completed_at']): ?>
                            <p><strong>Completed:</strong> <?= $status['completed_at'] ?></p>
                        <?php endif; ?>
                        <?php if ($status['device_count']): ?>
                            <p><strong>Devices:</strong> <?= $status['device_count'] ?></p>
                        <?php endif; ?>
                        <?php if ($status['file_path']): ?>
                            <p><strong>File:</strong> <span class="file-info"><?= basename($status['file_path']) ?></span></p>
                        <?php endif; ?>
                        <?php if ($status['file_size']): ?>
                            <p><strong>Size:</strong> <script>document.write(formatBytes(<?= $status['file_size'] ?>))</script></p>
                        <?php endif; ?>
                        <?php if ($status['upload_status']): ?>
                            <p><strong>Upload:</strong> <?= ucfirst($status['upload_status']) ?></p>
                        <?php endif; ?>
                        <?php if ($status['error_message']): ?>
                            <p><strong>Error:</strong> <span style="color: red;"><?= htmlspecialchars($status['error_message']) ?></span></p>
                        <?php endif; ?>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>
        
        <div class="card">
            <h2>Manual Trigger (VFZ Only)</h2>
            <div class="trigger-form">
                <p><strong>Note:</strong> This will trigger VFZ (CMTS) XML processing immediately, regardless of schedule.</p>
                
                <?php if (!empty($pending_triggers)): ?>
                    <div class="alert alert-warning">
                        <strong>Pending Triggers:</strong>
                        <?php foreach ($pending_triggers as $trigger): ?>
                            <br>• <?= $trigger['xml_type'] ?> triggered by <?= $trigger['triggered_by'] ?> at <?= $trigger['triggered_at'] ?>
                        <?php endforeach; ?>
                    </div>
                <?php endif; ?>
                
                <form method="post" onsubmit="return confirmTrigger()">
                    <input type="hidden" name="action" value="trigger_vfz">
                    <input type="hidden" name="confirm" value="yes">
                    <label for="triggered_by">Triggered by:</label>
                    <input type="text" name="triggered_by" placeholder="Your name" required style="margin: 0 10px;">
                    <button type="submit" class="btn btn-warning">Trigger VFZ Processing</button>
                </form>
            </div>
        </div>
        
        <div class="card">
            <h2>Recent Activity (Last 24 Hours)</h2>
            <div style="max-height: 400px; overflow-y: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Level</th>
                            <th>Type</th>
                            <th>Message</th>
                            <th>Host</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($logs as $log): ?>
                            <tr>
                                <td><?= $log['timestamp'] ?></td>
                                <td class="log-level-<?= $log['level'] ?>"><?= $log['level'] ?></td>
                                <td><?= $log['xml_type'] ?: '-' ?></td>
                                <td><?= htmlspecialchars($log['message']) ?></td>
                                <td><?= $log['hostname'] ?: '-' ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="card">
            <h2>Crontab Configuration</h2>
            <p>Add this line to your crontab to run every weekday at 9:00 AM:</p>
            <pre style="background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto;">
# EVE LI XML Generator - runs weekdays at 9:00 AM, checks for manual triggers
0 9 * * 1-5 /usr/bin/python3 /path/to/eve_li_xml_generator.py --mode cron

# Optional: Check for manual triggers every 15 minutes during business hours
*/15 8-18 * * 1-5 /usr/bin/python3 /path/to/eve_li_xml_generator.py --mode cron
            </pre>
        </div>
    </div>
</body>
</html>
