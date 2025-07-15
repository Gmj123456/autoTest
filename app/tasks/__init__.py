#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery异步任务模块
处理AI分析、测试执行、报告生成等异步任务
"""

from celery import Celery
from app import create_app
from app.models import db
import os

# 创建Celery实例
celery = Celery('autotest')

def make_celery(app):
    """创建Celery实例并配置"""
    celery.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Shanghai',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30分钟超时
        task_soft_time_limit=25 * 60,  # 25分钟软超时
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )
    
    class ContextTask(celery.Task):
        """在Flask应用上下文中执行任务"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# 导入任务模块
from .ai_tasks import *
from .execution_tasks import *
from .report_tasks import *