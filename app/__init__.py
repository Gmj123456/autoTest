#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask应用初始化模块
"""

import os
import sys
import yaml
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from loguru import logger

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()

def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"加载YAML配置文件失败: {e}，使用默认配置")
        # 如果YAML配置不存在，尝试使用config.py
        try:
            from config import get_config
            config_class = get_config()
            return config_class.__dict__
        except Exception as e2:
            logger.error(f"加载配置失败: {e2}")
            return {}

def create_app(config_name=None):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    config = load_config()
    
    # 设置Flask配置
    app.config['SECRET_KEY'] = config.get('app', {}).get('secret_key', 'dev-secret-key')
    app.config['DEBUG'] = config.get('app', {}).get('debug', True)
    app.config['HOST'] = config.get('app', {}).get('host', '127.0.0.1')
    app.config['PORT'] = config.get('app', {}).get('port', 5000)
    
    # 数据库配置
    db_config = config.get('database', {})
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{db_config.get('username', 'root')}:"
        f"{db_config.get('password', 'password')}@"
        f"{db_config.get('host', 'localhost')}:"
        f"{db_config.get('port', 3306)}/"
        f"{db_config.get('database', 'autotest_db')}?"
        f"charset={db_config.get('charset', 'utf8mb4')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Redis配置
    redis_config = config.get('redis', {})
    app.config['REDIS_URL'] = (
        f"redis://:{redis_config.get('password', '')}@"
        f"{redis_config.get('host', 'localhost')}:"
        f"{redis_config.get('port', 6379)}/"
        f"{redis_config.get('db', 0)}"
    )
    
    # Celery配置
    app.config['CELERY_BROKER_URL'] = app.config['REDIS_URL']
    app.config['CELERY_RESULT_BACKEND'] = app.config['REDIS_URL']
    
    # 文件上传配置
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    
    # 存储配置
    storage_config = config.get('storage', {})
    app.config['SCREENSHOTS_PATH'] = storage_config.get('screenshots_path', './screenshots')
    app.config['REPORTS_PATH'] = storage_config.get('reports_path', './reports')
    app.config['LOGS_PATH'] = storage_config.get('logs_path', './logs')
    
    # 保存完整配置到app.config
    app.config['YAML_CONFIG'] = config
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    
    # CORS
    if config.get('api', {}).get('enable_cors', True):
        CORS(app, origins=config.get('api', {}).get('cors_origins', ['*']))
    
    # 创建必要的目录
    create_directories(app)
    
    # 配置日志
    setup_logging(app, config.get('logging', {}))
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册模板过滤器
    register_template_filters(app)
    
    # 注册CLI命令
    register_cli_commands(app)
    
    # 创建数据库表
    with app.app_context():
        try:
            db.create_all()
            logger.info("数据库表创建成功")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
    
    logger.info("Flask应用初始化完成")
    return app

def create_directories(app):
    """创建必要的目录"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['SCREENSHOTS_PATH'],
        app.config['REPORTS_PATH'],
        app.config['LOGS_PATH'],
        './temp'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def setup_logging(app, logging_config):
    """配置日志"""
    log_level = logging_config.get('level', 'INFO')
    log_format = logging_config.get('format', '{time} - {name} - {level} - {message}')
    log_file = os.path.join(app.config['LOGS_PATH'], 'app.log')
    
    # 配置loguru
    logger.remove()  # 移除默认处理器
    
    # 控制台输出
    if logging_config.get('console_output', True):
        logger.add(
            sys.stderr,
            level=log_level,
            format=log_format,
            colorize=True
        )
    
    # 文件输出
    logger.add(
        log_file,
        level=log_level,
        format=log_format,
        rotation=logging_config.get('file_rotation', '10 MB'),
        retention=logging_config.get('retention', '30 days'),
        encoding='utf-8'
    )

def register_blueprints(app):
    """注册蓝图"""
    from app.views.main import main_bp
    from app.views.project import project_bp
    from app.views.testcase import testcase_bp
    from app.views.execution import execution_bp
    from app.views.bug import bug_bp
    from app.views.report import report_bp
    from app.views.ai import ai_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(project_bp, url_prefix='/project')
    app.register_blueprint(testcase_bp, url_prefix='/testcase')
    app.register_blueprint(execution_bp, url_prefix='/execution')
    app.register_blueprint(bug_bp, url_prefix='/bug')
    app.register_blueprint(report_bp, url_prefix='/report')
    app.register_blueprint(ai_bp, url_prefix='/ai')

def register_error_handlers(app):
    """注册错误处理器"""
    from flask import render_template, jsonify
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

def register_template_filters(app):
    """注册模板过滤器"""
    from datetime import datetime
    
    @app.template_filter('datetime')
    def datetime_filter(value, format='%Y-%m-%d %H:%M:%S'):
        if isinstance(value, str):
            return value
        return value.strftime(format) if value else ''
    
    @app.template_filter('status_badge')
    def status_badge_filter(status):
        badge_map = {
            '通过': 'success',
            '失败': 'danger',
            '跳过': 'warning',
            '运行中': 'info',
            '新建': 'secondary',
            '已分配': 'info',
            '处理中': 'warning',
            '已解决': 'success',
            '已关闭': 'dark'
        }
        return badge_map.get(status, 'secondary')

def register_cli_commands(app):
    """注册CLI命令"""
    
    @app.cli.command()
    def init_db():
        """初始化数据库"""
        db.create_all()
        logger.info("数据库初始化完成")
    
    @app.cli.command()
    def drop_db():
        """删除数据库"""
        db.drop_all()
        logger.info("数据库删除完成")
    
    @app.cli.command()
    def reset_db():
        """重置数据库"""
        db.drop_all()
        db.create_all()
        logger.info("数据库重置完成")
    
    @app.cli.command()
    def create_sample_data():
        """创建示例数据"""
        from app.models import Project, Module, TestCase
        
        # 创建示例项目
        project = Project(
            name='示例项目',
            description='这是一个示例项目，用于演示系统功能',
            status='active'
        )
        db.session.add(project)
        db.session.flush()
        
        # 创建示例模块
        module = Module(
            name='用户管理',
            description='用户注册、登录、个人信息管理等功能',
            project_id=project.id
        )
        db.session.add(module)
        db.session.flush()
        
        # 创建示例测试用例
        test_case = TestCase(
            title='用户登录功能测试',
            description='测试用户使用正确的用户名和密码登录系统',
            project_id=project.id,
            module_id=module.id,
            type='functional',
            priority='high',
            status='active',
            steps=[
                {'step': 1, 'action': '打开登录页面', 'expected': '显示登录表单'},
                {'step': 2, 'action': '输入用户名和密码', 'expected': '输入框显示内容'},
                {'step': 3, 'action': '点击登录按钮', 'expected': '跳转到首页'}
            ],
            test_data={'username': 'testuser', 'password': 'testpass'}
        )
        db.session.add(test_case)
        
        db.session.commit()
        logger.info("示例数据创建完成")

# 自定义异常类
class ValidationError(Exception):
    """数据验证错误"""
    pass

class BusinessError(Exception):
    """业务逻辑错误"""
    pass

class AIServiceError(Exception):
    """AI服务错误"""
    pass

class TestExecutionError(Exception):
    """测试执行错误"""
    pass

# 导入模型以确保它们被注册
from app.models import *