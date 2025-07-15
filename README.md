# AI增强自动化测试平台

## 项目简介

这是一个基于AI技术的自动化测试平台，集成了智能测试用例生成、执行结果分析、Bug根因分析等功能。平台采用现代化的技术架构，提供完整的测试生命周期管理解决方案。

## 主要功能

### 🎯 项目管理
- 多项目支持和管理
- 模块化组织结构
- 团队协作和权限控制
- 项目统计和监控

### 📝 测试用例管理
- 手动创建和编辑测试用例
- **AI智能生成测试用例**
- **AI增强现有测试用例**
- 用例分类、标签和优先级管理
- 测试数据管理
- 公共操作库

### 🚀 测试执行
- 支持多种测试类型（Web UI、API、移动端、性能、安全）
- 并行和批量执行
- 实时执行监控
- 详细执行日志
- 截图和视频录制
- **AI执行结果分析**

### 🤖 AI增强功能
- **智能测试用例生成** - 基于需求描述自动生成测试用例
- **执行结果智能分析** - AI分析失败原因和改进建议
- **Bug根因分析** - 智能分析Bug产生的根本原因
- **相似Bug检测** - 自动发现相似的历史Bug
- **项目风险评估** - 基于历史数据评估项目质量风险
- **测试报告AI分析** - 智能分析测试覆盖度和质量指标

### 📊 报告系统
- 自动生成多种类型测试报告
- 丰富的数据可视化图表
- 趋势分析和对比
- 支持导出Excel、PDF、HTML格式
- 定时报告生成
- **AI质量评估和建议**

### 🐛 Bug管理
- 完整的Bug生命周期管理
- 智能Bug分类和优先级
- **AI根因分析和修复建议**
- Bug趋势分析
- 附件和截图支持

### 📈 数据分析
- 测试执行趋势分析
- 质量指标监控
- 覆盖率统计
- 性能指标追踪
- 自定义仪表板

## 技术架构

### 后端技术栈
- **Web框架**: Flask 2.3.3
- **数据库**: MySQL 8.0 + SQLAlchemy ORM
- **缓存**: Redis 6.0+
- **任务队列**: Celery + Redis
- **AI集成**: OpenAI GPT API
- **数据处理**: Pandas, NumPy, Scikit-learn
- **图表生成**: Matplotlib, Plotly

### 前端技术栈
- **UI框架**: Bootstrap 5
- **JavaScript**: jQuery, Chart.js
- **模板引擎**: Jinja2
- **图标**: Font Awesome

### 测试引擎
- **Web UI测试**: Selenium WebDriver
- **API测试**: Requests, HTTPx
- **性能测试**: 集成第三方工具
- **移动端测试**: Appium（可扩展）

## 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+ 或 8.0+
- Redis 6.0+
- Chrome/Firefox 浏览器（用于Web UI测试）

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd autoTest
```

2. **创建虚拟环境**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置数据库**
```bash
# 创建MySQL数据库
mysql -u root -p
CREATE DATABASE autotest_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

5. **配置文件**

编辑 `config/config.yaml` 或使用环境变量：
```yaml
database:
  host: localhost
  port: 3306
  username: root
  password: your_password
  database: autotest_db

redis:
  host: localhost
  port: 6379
  password: ""
  db: 0

ai:
  api_key: your_openai_api_key
  model: gpt-3.5-turbo
```

6. **初始化数据库**
```bash
flask init-db
# 或者创建示例数据
flask create-sample-data
```

7. **启动Redis服务**
```bash
# Windows (如果使用WSL)
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:6-alpine
```

8. **启动Celery Worker（新终端）**
```bash
celery -A app.tasks.celery worker --loglevel=info
```

9. **启动应用**
```bash
python run.py
```

10. **访问应用**

打开浏览器访问: http://127.0.0.1:5000

### Docker快速部署

```bash
# 构建和启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 配置说明

### 主配置文件 `config/config.yaml`

```yaml
# 应用配置
app:
  secret_key: "your-secret-key"
  debug: true
  host: "127.0.0.1"
  port: 5000

# 数据库配置
database:
  host: "localhost"
  port: 3306
  username: "root"
  password: "password"
  database: "autotest_db"
  charset: "utf8mb4"

# Redis配置
redis:
  host: "localhost"
  port: 6379
  password: ""
  db: 0

# AI服务配置
ai:
  api_key: "your-openai-api-key"
  api_base: "https://api.openai.com/v1"
  model: "gpt-3.5-turbo"
  max_tokens: 2000
  temperature: 0.7

# 存储配置
storage:
  screenshots_path: "./screenshots"
  reports_path: "./reports"
  logs_path: "./logs"

# 日志配置
logging:
  level: "INFO"
  console_output: true
  file_rotation: "10 MB"
  retention: "30 days"
```

### 环境变量配置

创建 `.env` 文件：
```bash
# 数据库
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/autotest_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI服务
AI_API_KEY=your_openai_api_key
AI_MODEL=gpt-3.5-turbo

# 应用
SECRET_KEY=your-secret-key
FLASK_ENV=development
```

## 使用指南

### 1. 创建第一个项目

1. 访问系统首页
2. 点击"新建项目"按钮
3. 填写项目基本信息：
   - 项目名称
   - 项目描述
   - 项目状态
4. 创建项目模块来组织测试用例

### 2. AI生成测试用例

1. 进入项目的测试用例页面
2. 点击"AI生成测试用例"
3. 输入需求描述，例如：
   ```
   用户登录功能：用户可以使用用户名和密码登录系统，
   登录成功后跳转到首页，登录失败显示错误信息。
   ```
4. 选择生成数量和测试类型
5. AI将自动生成详细的测试用例

### 3. 执行测试用例

1. 在测试用例列表中选择要执行的用例
2. 点击"执行测试"或"批量执行"
3. 配置执行参数（浏览器类型、并发数等）
4. 监控执行进度和实时日志
5. 查看执行结果和AI分析报告

### 4. Bug管理和AI分析

1. 测试失败时可以直接创建Bug
2. 填写Bug基本信息
3. 使用"AI根因分析"功能获取智能分析
4. 查看相似Bug检测结果
5. 跟踪Bug修复进度

### 5. 生成测试报告

1. 进入"测试报告"页面
2. 选择报告类型：
   - 综合报告
   - 执行报告
   - Bug报告
   - 覆盖率报告
3. 设置时间范围和过滤条件
4. 生成报告并查看AI分析结果
5. 导出报告（Excel/PDF/HTML）

## API文档

系统提供完整的RESTful API接口，支持：

- 项目管理API
- 测试用例管理API
- 测试执行API
- Bug管理API
- 报告生成API
- AI功能API

详细API文档请访问：`http://localhost:5000/api/docs`

## 开发指南

### 项目结构

```
autoTest/
├── app/                    # 应用主目录
│   ├── __init__.py        # 应用工厂函数
│   ├── models/            # 数据模型
│   │   └── __init__.py    # 数据库模型定义
│   ├── views/             # 视图控制器
│   │   ├── main.py        # 主页视图
│   │   ├── project.py     # 项目管理
│   │   ├── testcase.py    # 测试用例管理
│   │   ├── execution.py   # 测试执行
│   │   ├── bug.py         # Bug管理
│   │   ├── report.py      # 报告管理
│   │   └── ai.py          # AI功能
│   ├── services/          # 业务服务层
│   │   ├── ai_service.py  # AI服务
│   │   ├── test_executor.py # 测试执行器
│   │   └── report_service.py # 报告服务
│   ├── tasks/             # Celery异步任务
│   │   ├── ai_tasks.py    # AI相关任务
│   │   ├── execution_tasks.py # 执行任务
│   │   └── report_tasks.py # 报告任务
│   └── utils/             # 工具类
│       ├── text_similarity.py # 文本相似度
│       └── data_processor.py  # 数据处理
├── config/                # 配置文件目录
│   └── config.yaml        # 主配置文件
├── config.py              # Python配置类
├── templates/             # Jinja2模板文件
├── static/                # 静态资源
├── tests/                 # 测试文件
├── uploads/               # 上传文件目录
├── reports/               # 生成的报告
├── logs/                  # 日志文件
├── requirements.txt       # Python依赖
├── docker-compose.yml     # Docker编排
├── Dockerfile            # Docker镜像
└── run.py                # 应用启动入口
```

### 开发环境设置

1. **安装开发工具**
```bash
pip install flake8 black pytest pytest-cov
```

2. **代码格式化**
```bash
# 格式化代码
black .

# 检查代码风格
flake8 .
```

3. **运行测试**
```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html
```

4. **数据库迁移**
```bash
# 生成迁移文件
flask db migrate -m "描述变更内容"

# 应用迁移
flask db upgrade
```

### 添加新功能

1. **添加数据模型**
   - 在 `app/models/__init__.py` 中定义新模型
   - 生成并应用数据库迁移

2. **添加API接口**
   - 在相应的视图文件中添加路由
   - 实现业务逻辑
   - 添加错误处理

3. **添加AI功能**
   - 在 `app/services/ai_service.py` 中添加AI方法
   - 在 `app/tasks/ai_tasks.py` 中添加异步任务
   - 在视图中调用AI功能

4. **添加测试**
   - 为新功能编写单元测试
   - 确保测试覆盖率

## 部署指南

### 生产环境部署

1. **环境配置**
```bash
export FLASK_ENV=production
export SECRET_KEY=your-production-secret-key
export DATABASE_URL=mysql+pymysql://user:pass@host:port/db
export REDIS_URL=redis://host:port/0
export AI_API_KEY=your-production-api-key
```

2. **使用Gunicorn部署**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

3. **使用Nginx反向代理**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static {
        alias /path/to/autoTest/static;
    }
}
```

4. **使用Supervisor管理进程**
```ini
[program:autotest]
command=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 run:app
directory=/path/to/autoTest
user=www-data
autostart=true
autorestart=true

[program:celery]
command=/path/to/venv/bin/celery -A app.tasks.celery worker --loglevel=info
directory=/path/to/autoTest
user=www-data
autostart=true
autorestart=true
```

### Docker部署

1. **构建镜像**
```bash
docker build -t autotest:latest .
```

2. **使用Docker Compose**
```bash
docker-compose up -d
```

3. **扩展服务**
```bash
# 扩展Web服务
docker-compose up -d --scale web=3

# 扩展Celery Worker
docker-compose up -d --scale worker=2
```

## 监控和维护

### 日志管理

- 应用日志：`logs/app.log`
- Celery日志：`logs/celery.log`
- 执行日志：`logs/execution/`

### 性能监控

- 使用 `psutil` 监控系统资源
- Redis监控：连接数、内存使用
- 数据库监控：连接池、查询性能

### 备份策略

1. **数据库备份**
```bash
mysqldump -u root -p autotest_db > backup_$(date +%Y%m%d).sql
```

2. **文件备份**
```bash
tar -czf backup_files_$(date +%Y%m%d).tar.gz uploads/ reports/ logs/
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务状态
   - 验证连接配置
   - 检查防火墙设置

2. **Redis连接失败**
   - 确认Redis服务运行
   - 检查端口和密码配置

3. **AI功能不可用**
   - 验证API密钥
   - 检查网络连接
   - 查看API配额限制

4. **Celery任务不执行**
   - 检查Worker进程状态
   - 验证Redis连接
   - 查看任务队列状态

### 调试技巧

1. **启用调试模式**
```python
app.config['DEBUG'] = True
```

2. **查看详细日志**
```bash
tail -f logs/app.log
```

3. **监控Celery任务**
```bash
celery -A app.tasks.celery flower
```

## 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

1. **Fork项目**
2. **创建特性分支**
```bash
git checkout -b feature/amazing-feature
```

3. **提交更改**
```bash
git commit -m 'Add some amazing feature'
```

4. **推送到分支**
```bash
git push origin feature/amazing-feature
```

5. **创建Pull Request**

### 代码规范

- 使用Black进行代码格式化
- 遵循PEP 8编码规范
- 编写清晰的注释和文档字符串
- 为新功能添加测试用例
- 更新相关文档

## 路线图

### v1.1.0 (计划中)
- [ ] 支持更多测试框架集成
- [ ] 增强AI模型训练能力
- [ ] 移动端测试支持
- [ ] 性能测试集成

### v1.2.0 (计划中)
- [ ] 多租户支持
- [ ] 高级权限管理
- [ ] 插件系统
- [ ] 国际化支持

### v2.0.0 (远期规划)
- [ ] 微服务架构重构
- [ ] 云原生部署
- [ ] 机器学习模型优化
- [ ] 实时协作功能

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- **项目维护者**: AutoTest Team
- **邮箱**: support@autotest.com
- **项目地址**: https://github.com/your-org/autotest
- **问题反馈**: https://github.com/your-org/autotest/issues
- **讨论区**: https://github.com/your-org/autotest/discussions

## 致谢

感谢以下开源项目和贡献者：

- Flask 和 Flask 生态系统
- OpenAI 提供的AI服务
- Selenium WebDriver
- 所有贡献代码和反馈的开发者

## 更新日志

### v1.0.0 (2024-01-01)
- ✨ 初始版本发布
- ✨ 完整的项目和测试用例管理
- ✨ AI智能测试用例生成
- ✨ 多类型测试执行支持
- ✨ AI增强的Bug分析
- ✨ 丰富的测试报告系统
- ✨ 异步任务处理
- ✨ Docker部署支持

---

**开始使用AutoTest，让AI为您的测试工作赋能！** 🚀

## 项目结构
```
autoTest/
├── app/                    # Flask应用主目录
│   ├── __init__.py        # 应用初始化
│   ├── models/            # 数据模型
│   ├── views/             # 视图控制器
│   ├── services/          # 业务逻辑服务
│   ├── ai/                # AI功能模块
│   ├── templates/         # HTML模板
│   └── static/            # 静态资源
├── tests/                  # 测试用例目录
├── migrations/            # 数据库迁移文件
├── logs/                  # 日志文件
├── reports/               # 测试报告
├── screenshots/           # 截图存储
├── uploads/               # 文件上传
├── config/                # 配置文件
├── requirements.txt       # Python依赖
├── run.py                 # 应用启动入口
└── celery_worker.py       # Celery任务处理器
```

## 安装部署

### 1. 环境准备
- Python 3.8+
- MySQL 8.0+
- Redis 6.0+
- Chrome浏览器

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 数据库配置
```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE autotest_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 初始化数据库
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. 启动服务
```bash
# 启动Web应用
python run.py

# 启动Celery任务处理器
celery -A celery_worker.celery worker --loglevel=info
```

### 5. 访问系统
打开浏览器访问：http://localhost:5000

## AI功能配置
在 `config/config.yaml` 中配置AI服务：
```yaml
ai:
  provider: "openai"  # openai, baidu, local
  api_key: "your_api_key"
  model: "gpt-4"
  base_url: "https://api.openai.com/v1"
```

## 使用说明
1. **创建项目**：在项目管理页面创建新项目和模块
2. **设计测试用例**：手动创建或使用AI生成测试用例
3. **配置公共操作**：创建可复用的操作组件
4. **执行测试**：选择环境和用例进行测试执行
5. **查看报告**：分析测试结果和AI智能建议

## 开发指南
- 遵循Flask应用结构和MVC模式
- 使用SQLAlchemy进行数据库操作
- AI功能通过服务层封装，支持多种AI提供商
- 前端使用Bootstrap响应式设计
- 异步任务使用Celery处理

## 许可证
MIT License