#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化测试平台启动入口
"""

import os
import sys
from app import create_app
from app.models import db
from flask_migrate import Migrate

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 创建Flask应用实例
app = create_app()

# 初始化数据库迁移
migrate = Migrate(app, db)

# 创建应用上下文
with app.app_context():
    # 创建数据库表
    db.create_all()

if __name__ == '__main__':
    # 从配置文件读取主机和端口
    host = app.config.get('HOST', '127.0.0.1')
    port = app.config.get('PORT', 5000)
    debug = app.config.get('DEBUG', True)
    
    print(f"启动AI增强自动化测试平台...")
    print(f"访问地址: http://{host}:{port}")
    print(f"调试模式: {debug}")
    
    # 启动应用
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )