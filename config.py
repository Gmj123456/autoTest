#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用配置文件
"""

import os
from datetime import timedelta

class Config:
    """基础配置类"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///autotest.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Redis配置（用于Celery）
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Celery配置
    CELERY = {
        'broker_url': REDIS_URL,
        'result_backend': REDIS_URL,
        'task_ignore_result': False,
        'task_store_eager_result': True,
        'result_expires': 3600,
        'timezone': 'Asia/Shanghai',
        'enable_utc': True,
        'task_serializer': 'json',
        'result_serializer': 'json',
        'accept_content': ['json'],
        'task_routes': {
            'app.tasks.ai_tasks.*': {'queue': 'ai'},
            'app.tasks.execution_tasks.*': {'queue': 'execution'},
            'app.tasks.report_tasks.*': {'queue': 'report'},
        },
        'worker_prefetch_multiplier': 1,
        'task_acks_late': True,
        'worker_max_tasks_per_child': 1000,
    }
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/autotest.log'
    
    # AI配置
    AI = {
        'provider': os.environ.get('AI_PROVIDER') or 'openai',  # openai, azure, local
        'api_key': os.environ.get('AI_API_KEY') or '',
        'api_base': os.environ.get('AI_API_BASE') or 'https://api.openai.com/v1',
        'model': os.environ.get('AI_MODEL') or 'gpt-3.5-turbo',
        'max_tokens': int(os.environ.get('AI_MAX_TOKENS', '2000')),
        'temperature': float(os.environ.get('AI_TEMPERATURE', '0.7')),
        'timeout': int(os.environ.get('AI_TIMEOUT', '30')),
        'retry_times': int(os.environ.get('AI_RETRY_TIMES', '3')),
        'enable_fallback': os.environ.get('AI_ENABLE_FALLBACK', 'true').lower() == 'true',
        'fallback_model': os.environ.get('AI_FALLBACK_MODEL') or 'gpt-3.5-turbo',
    }
    
    # 测试执行配置
    TEST_EXECUTION = {
        'max_parallel_executions': int(os.environ.get('MAX_PARALLEL_EXECUTIONS', '5')),
        'execution_timeout': int(os.environ.get('EXECUTION_TIMEOUT', '300')),  # 5分钟
        'retry_times': int(os.environ.get('TEST_RETRY_TIMES', '2')),
        'screenshot_on_failure': os.environ.get('SCREENSHOT_ON_FAILURE', 'true').lower() == 'true',
        'video_recording': os.environ.get('VIDEO_RECORDING', 'false').lower() == 'true',
        'browser_options': {
            'headless': os.environ.get('BROWSER_HEADLESS', 'true').lower() == 'true',
            'window_size': os.environ.get('BROWSER_WINDOW_SIZE') or '1920,1080',
            'user_agent': os.environ.get('BROWSER_USER_AGENT') or '',
        }
    }
    
    # 报告配置
    REPORT = {
        'template_dir': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'templates', 'reports'),
        'output_dir': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports'),
        'include_screenshots': os.environ.get('REPORT_INCLUDE_SCREENSHOTS', 'true').lower() == 'true',
        'include_logs': os.environ.get('REPORT_INCLUDE_LOGS', 'true').lower() == 'true',
        'auto_generate_daily': os.environ.get('AUTO_GENERATE_DAILY_REPORT', 'false').lower() == 'true',
        'auto_generate_weekly': os.environ.get('AUTO_GENERATE_WEEKLY_REPORT', 'false').lower() == 'true',
    }
    
    # 邮件配置
    MAIL = {
        'server': os.environ.get('MAIL_SERVER') or 'localhost',
        'port': int(os.environ.get('MAIL_PORT', '587')),
        'use_tls': os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true',
        'username': os.environ.get('MAIL_USERNAME') or '',
        'password': os.environ.get('MAIL_PASSWORD') or '',
        'default_sender': os.environ.get('MAIL_DEFAULT_SENDER') or 'autotest@example.com',
    }
    
    # 安全配置
    SECURITY = {
        'password_hash_method': 'pbkdf2:sha256',
        'password_salt_length': 16,
        'session_timeout': timedelta(hours=24),
        'max_login_attempts': int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5')),
        'lockout_duration': timedelta(minutes=int(os.environ.get('LOCKOUT_DURATION_MINUTES', '30'))),
    }
    
    # API配置
    API = {
        'rate_limit': os.environ.get('API_RATE_LIMIT') or '100/hour',
        'enable_cors': os.environ.get('API_ENABLE_CORS', 'true').lower() == 'true',
        'cors_origins': os.environ.get('API_CORS_ORIGINS', '*').split(','),
        'api_key_required': os.environ.get('API_KEY_REQUIRED', 'false').lower() == 'true',
        'api_key': os.environ.get('API_KEY') or '',
    }
    
    # 缓存配置
    CACHE = {
        'type': os.environ.get('CACHE_TYPE') or 'redis',
        'redis_url': REDIS_URL,
        'default_timeout': int(os.environ.get('CACHE_DEFAULT_TIMEOUT', '300')),
        'key_prefix': os.environ.get('CACHE_KEY_PREFIX') or 'autotest:',
    }
    
    # 监控配置
    MONITORING = {
        'enable_metrics': os.environ.get('ENABLE_METRICS', 'true').lower() == 'true',
        'metrics_port': int(os.environ.get('METRICS_PORT', '9090')),
        'health_check_interval': int(os.environ.get('HEALTH_CHECK_INTERVAL', '60')),
    }
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建必要的目录
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['REPORT']['output_dir'], exist_ok=True)
        os.makedirs(os.path.dirname(app.config['LOG_FILE']), exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    
    # 开发环境数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'autotest_dev.db')
    
    # 开发环境日志
    LOG_LEVEL = 'DEBUG'
    
    # 开发环境AI配置（可能使用mock）
    AI = Config.AI.copy()
    AI.update({
        'enable_fallback': True,
        'timeout': 10,  # 更短的超时时间
    })
    
    # 开发环境测试执行配置
    TEST_EXECUTION = Config.TEST_EXECUTION.copy()
    TEST_EXECUTION.update({
        'max_parallel_executions': 2,  # 减少并发数
        'execution_timeout': 60,  # 更短的超时时间
    })

class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    
    # 测试数据库（内存数据库）
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # 禁用CSRF保护
    WTF_CSRF_ENABLED = False
    
    # 测试环境Redis（可以使用fakeredis）
    REDIS_URL = 'redis://localhost:6379/15'  # 使用不同的数据库
    
    # 测试环境AI配置（使用mock）
    AI = {
        'provider': 'mock',
        'api_key': 'test-key',
        'model': 'mock-model',
        'enable_fallback': False,
    }
    
    # 测试环境邮件配置（不发送真实邮件）
    MAIL = {
        'server': 'localhost',
        'port': 587,
        'use_tls': False,
        'username': '',
        'password': '',
        'default_sender': 'test@example.com',
        'suppress_send': True,  # 抑制邮件发送
    }

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境必须设置的环境变量
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("生产环境必须设置SECRET_KEY环境变量")
    
    # 生产环境数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("生产环境必须设置DATABASE_URL环境变量")
    
    # 生产环境Redis
    REDIS_URL = os.environ.get('REDIS_URL')
    if not REDIS_URL:
        raise ValueError("生产环境必须设置REDIS_URL环境变量")
    
    # 生产环境AI配置
    AI = Config.AI.copy()
    if not AI['api_key']:
        raise ValueError("生产环境必须设置AI_API_KEY环境变量")
    
    # 生产环境安全配置
    SECURITY = Config.SECURITY.copy()
    SECURITY.update({
        'session_timeout': timedelta(hours=8),  # 更短的会话超时
        'max_login_attempts': 3,  # 更严格的登录限制
    })
    
    # 生产环境监控
    MONITORING = Config.MONITORING.copy()
    MONITORING.update({
        'enable_metrics': True,
        'health_check_interval': 30,  # 更频繁的健康检查
    })
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # 生产环境特定的初始化
        import logging
        from logging.handlers import RotatingFileHandler
        
        # 设置日志轮转
        if not app.debug:
            file_handler = RotatingFileHandler(
                app.config['LOG_FILE'],
                maxBytes=10240000,  # 10MB
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('AutoTest startup')

# 配置字典
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# 获取当前配置
def get_config():
    """获取当前环境配置"""
    config_name = os.environ.get('FLASK_ENV') or 'default'
    return config.get(config_name, DevelopmentConfig)