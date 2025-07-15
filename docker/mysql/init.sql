-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS autotest_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE autotest_db;

-- 设置时区
SET time_zone = '+08:00';

-- 创建用户（如果不存在）
CREATE USER IF NOT EXISTS 'autotest'@'%' IDENTIFIED BY 'autotest123';

-- 授权
GRANT ALL PRIVILEGES ON autotest_db.* TO 'autotest'@'%';
GRANT ALL PRIVILEGES ON autotest_db.* TO 'root'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 创建示例配置表（可选）
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认配置
INSERT IGNORE INTO system_config (config_key, config_value, description) VALUES
('app_name', 'AutoTest Platform', '应用名称'),
('app_version', '1.0.0', '应用版本'),
('default_language', 'zh-CN', '默认语言'),
('max_upload_size', '16777216', '最大上传文件大小（字节）'),
('session_timeout', '3600', '会话超时时间（秒）'),
('enable_registration', 'true', '是否允许用户注册'),
('default_test_timeout', '300', '默认测试超时时间（秒）'),
('max_parallel_executions', '5', '最大并行执行数'),
('enable_ai_features', 'true', '是否启用AI功能'),
('report_retention_days', '90', '报告保留天数');