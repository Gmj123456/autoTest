#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库模型模块
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

# 基础模型类
class BaseModel(db.Model):
    """基础模型类"""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def to_dict(self):
        """转换为字典"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                result[column.name] = value
        return result
    
    def save(self):
        """保存到数据库"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """从数据库删除"""
        db.session.delete(self)
        db.session.commit()

# 项目模型
class Project(BaseModel):
    """项目模型"""
    __tablename__ = 'projects'
    
    name = db.Column(db.String(100), nullable=False, comment='项目名称')
    description = db.Column(db.Text, comment='项目描述')
    status = db.Column(db.String(20), default='active', comment='项目状态')
    owner = db.Column(db.String(50), comment='项目负责人')
    environment = db.Column(db.String(50), default='test', comment='测试环境')
    base_url = db.Column(db.String(200), comment='基础URL')
    api_base_url = db.Column(db.String(200), comment='API基础URL')
    
    # 关联关系
    modules = db.relationship('Module', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    testcases = db.relationship('TestCase', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    executions = db.relationship('TestExecution', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    bugs = db.relationship('Bug', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'

# 模块模型
class Module(BaseModel):
    """模块模型"""
    __tablename__ = 'modules'
    
    name = db.Column(db.String(100), nullable=False, comment='模块名称')
    description = db.Column(db.Text, comment='模块描述')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, comment='项目ID')
    parent_id = db.Column(db.Integer, db.ForeignKey('modules.id'), comment='父模块ID')
    
    # 关联关系
    children = db.relationship('Module', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    testcases = db.relationship('TestCase', backref='module', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Module {self.name}>'

# 测试用例模型
class TestCase(BaseModel):
    """测试用例模型"""
    __tablename__ = 'testcases'
    
    title = db.Column(db.String(200), nullable=False, comment='用例标题')
    description = db.Column(db.Text, comment='用例描述')
    precondition = db.Column(db.Text, comment='前置条件')
    steps = db.Column(db.Text, comment='测试步骤(JSON格式)')
    expected_result = db.Column(db.Text, comment='预期结果')
    priority = db.Column(db.String(20), default='medium', comment='优先级')
    type = db.Column(db.String(20), default='functional', comment='用例类型')
    status = db.Column(db.String(20), default='active', comment='用例状态')
    tags = db.Column(db.String(200), comment='标签')
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, comment='项目ID')
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), comment='模块ID')
    creator = db.Column(db.String(50), comment='创建人')
    
    # AI相关字段
    ai_generated = db.Column(db.Boolean, default=False, comment='是否AI生成')
    ai_confidence = db.Column(db.Float, comment='AI置信度')
    risk_level = db.Column(db.String(20), comment='风险等级')
    
    # 关联关系
    executions = db.relationship('TestExecution', backref='testcase', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_steps(self):
        """获取测试步骤"""
        try:
            return json.loads(self.steps) if self.steps else []
        except:
            return []
    
    def set_steps(self, steps_list):
        """设置测试步骤"""
        self.steps = json.dumps(steps_list, ensure_ascii=False)
    
    def __repr__(self):
        return f'<TestCase {self.title}>'

# 公共操作模型
class CommonAction(BaseModel):
    """公共操作模型"""
    __tablename__ = 'common_actions'
    
    name = db.Column(db.String(100), nullable=False, comment='操作名称')
    description = db.Column(db.Text, comment='操作描述')
    action_type = db.Column(db.String(50), comment='操作类型')
    parameters = db.Column(db.Text, comment='参数配置(JSON格式)')
    code = db.Column(db.Text, comment='操作代码')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), comment='项目ID')
    
    def get_parameters(self):
        """获取参数配置"""
        try:
            return json.loads(self.parameters) if self.parameters else {}
        except:
            return {}
    
    def set_parameters(self, params_dict):
        """设置参数配置"""
        self.parameters = json.dumps(params_dict, ensure_ascii=False)
    
    def __repr__(self):
        return f'<CommonAction {self.name}>'

# 测试执行模型
class TestExecution(BaseModel):
    """测试执行模型"""
    __tablename__ = 'test_executions'
    
    name = db.Column(db.String(200), nullable=False, comment='执行名称')
    description = db.Column(db.Text, comment='执行描述')
    status = db.Column(db.String(20), default='pending', comment='执行状态')
    result = db.Column(db.String(20), comment='执行结果')
    start_time = db.Column(db.DateTime, comment='开始时间')
    end_time = db.Column(db.DateTime, comment='结束时间')
    duration = db.Column(db.Integer, comment='执行时长(秒)')
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, comment='项目ID')
    testcase_id = db.Column(db.Integer, db.ForeignKey('testcases.id'), comment='测试用例ID')
    executor = db.Column(db.String(50), comment='执行人')
    
    # 执行配置
    browser = db.Column(db.String(20), comment='浏览器')
    environment = db.Column(db.String(50), comment='执行环境')
    
    # 结果数据
    logs = db.Column(db.Text, comment='执行日志')
    screenshots = db.Column(db.Text, comment='截图路径(JSON格式)')
    error_message = db.Column(db.Text, comment='错误信息')
    
    # AI分析结果
    ai_analysis = db.Column(db.Text, comment='AI分析结果(JSON格式)')
    
    def get_screenshots(self):
        """获取截图列表"""
        try:
            return json.loads(self.screenshots) if self.screenshots else []
        except:
            return []
    
    def add_screenshot(self, screenshot_path):
        """添加截图"""
        screenshots = self.get_screenshots()
        screenshots.append(screenshot_path)
        self.screenshots = json.dumps(screenshots, ensure_ascii=False)
    
    def get_ai_analysis(self):
        """获取AI分析结果"""
        try:
            return json.loads(self.ai_analysis) if self.ai_analysis else {}
        except:
            return {}
    
    def set_ai_analysis(self, analysis_dict):
        """设置AI分析结果"""
        self.ai_analysis = json.dumps(analysis_dict, ensure_ascii=False)
    
    def __repr__(self):
        return f'<TestExecution {self.name}>'

# Bug模型
class Bug(BaseModel):
    """Bug模型"""
    __tablename__ = 'bugs'
    
    title = db.Column(db.String(200), nullable=False, comment='Bug标题')
    description = db.Column(db.Text, comment='Bug描述')
    severity = db.Column(db.String(20), default='medium', comment='严重程度')
    priority = db.Column(db.String(20), default='medium', comment='优先级')
    status = db.Column(db.String(20), default='new', comment='Bug状态')
    type = db.Column(db.String(50), comment='Bug类型')
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, comment='项目ID')
    testcase_id = db.Column(db.Integer, db.ForeignKey('testcases.id'), comment='关联测试用例ID')
    execution_id = db.Column(db.Integer, db.ForeignKey('test_executions.id'), comment='关联执行ID')
    
    reporter = db.Column(db.String(50), comment='报告人')
    assignee = db.Column(db.String(50), comment='指派人')
    
    # 复现信息
    steps_to_reproduce = db.Column(db.Text, comment='复现步骤')
    environment_info = db.Column(db.Text, comment='环境信息')
    attachments = db.Column(db.Text, comment='附件路径(JSON格式)')
    
    # AI分析结果
    ai_root_cause = db.Column(db.Text, comment='AI根因分析')
    ai_fix_suggestion = db.Column(db.Text, comment='AI修复建议')
    ai_similarity_score = db.Column(db.Float, comment='相似度评分')
    similar_bugs = db.Column(db.Text, comment='相似Bug列表(JSON格式)')
    
    def get_attachments(self):
        """获取附件列表"""
        try:
            return json.loads(self.attachments) if self.attachments else []
        except:
            return []
    
    def add_attachment(self, attachment_path):
        """添加附件"""
        attachments = self.get_attachments()
        attachments.append(attachment_path)
        self.attachments = json.dumps(attachments, ensure_ascii=False)
    
    def get_similar_bugs(self):
        """获取相似Bug列表"""
        try:
            return json.loads(self.similar_bugs) if self.similar_bugs else []
        except:
            return []
    
    def set_similar_bugs(self, bugs_list):
        """设置相似Bug列表"""
        self.similar_bugs = json.dumps(bugs_list, ensure_ascii=False)
    
    def __repr__(self):
        return f'<Bug {self.title}>'

# 测试报告模型
class TestReport(BaseModel):
    """测试报告模型"""
    __tablename__ = 'test_reports'
    
    name = db.Column(db.String(200), nullable=False, comment='报告名称')
    description = db.Column(db.Text, comment='报告描述')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, comment='项目ID')
    
    # 统计数据
    total_cases = db.Column(db.Integer, default=0, comment='总用例数')
    passed_cases = db.Column(db.Integer, default=0, comment='通过用例数')
    failed_cases = db.Column(db.Integer, default=0, comment='失败用例数')
    skipped_cases = db.Column(db.Integer, default=0, comment='跳过用例数')
    pass_rate = db.Column(db.Float, default=0.0, comment='通过率')
    
    # 执行信息
    start_time = db.Column(db.DateTime, comment='开始时间')
    end_time = db.Column(db.DateTime, comment='结束时间')
    duration = db.Column(db.Integer, comment='执行时长(秒)')
    environment = db.Column(db.String(50), comment='执行环境')
    
    # 报告文件
    report_path = db.Column(db.String(500), comment='报告文件路径')
    
    # AI分析结果
    ai_coverage_analysis = db.Column(db.Text, comment='AI覆盖度分析(JSON格式)')
    ai_quality_assessment = db.Column(db.Text, comment='AI质量评估(JSON格式)')
    ai_recommendations = db.Column(db.Text, comment='AI改进建议(JSON格式)')
    
    def get_ai_coverage_analysis(self):
        """获取AI覆盖度分析"""
        try:
            return json.loads(self.ai_coverage_analysis) if self.ai_coverage_analysis else {}
        except:
            return {}
    
    def set_ai_coverage_analysis(self, analysis_dict):
        """设置AI覆盖度分析"""
        self.ai_coverage_analysis = json.dumps(analysis_dict, ensure_ascii=False)
    
    def get_ai_quality_assessment(self):
        """获取AI质量评估"""
        try:
            return json.loads(self.ai_quality_assessment) if self.ai_quality_assessment else {}
        except:
            return {}
    
    def set_ai_quality_assessment(self, assessment_dict):
        """设置AI质量评估"""
        self.ai_quality_assessment = json.dumps(assessment_dict, ensure_ascii=False)
    
    def get_ai_recommendations(self):
        """获取AI改进建议"""
        try:
            return json.loads(self.ai_recommendations) if self.ai_recommendations else []
        except:
            return []
    
    def set_ai_recommendations(self, recommendations_list):
        """设置AI改进建议"""
        self.ai_recommendations = json.dumps(recommendations_list, ensure_ascii=False)
    
    def __repr__(self):
        return f'<TestReport {self.name}>'

# AI任务模型
class AITask(BaseModel):
    """AI任务模型"""
    __tablename__ = 'ai_tasks'
    
    task_type = db.Column(db.String(50), nullable=False, comment='任务类型')
    status = db.Column(db.String(20), default='pending', comment='任务状态')
    input_data = db.Column(db.Text, comment='输入数据(JSON格式)')
    output_data = db.Column(db.Text, comment='输出数据(JSON格式)')
    error_message = db.Column(db.Text, comment='错误信息')
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), comment='项目ID')
    related_id = db.Column(db.Integer, comment='关联对象ID')
    related_type = db.Column(db.String(50), comment='关联对象类型')
    
    start_time = db.Column(db.DateTime, comment='开始时间')
    end_time = db.Column(db.DateTime, comment='结束时间')
    duration = db.Column(db.Integer, comment='执行时长(秒)')
    
    def get_input_data(self):
        """获取输入数据"""
        try:
            return json.loads(self.input_data) if self.input_data else {}
        except:
            return {}
    
    def set_input_data(self, data_dict):
        """设置输入数据"""
        self.input_data = json.dumps(data_dict, ensure_ascii=False)
    
    def get_output_data(self):
        """获取输出数据"""
        try:
            return json.loads(self.output_data) if self.output_data else {}
        except:
            return {}
    
    def set_output_data(self, data_dict):
        """设置输出数据"""
        self.output_data = json.dumps(data_dict, ensure_ascii=False)
    
    def __repr__(self):
        return f'<AITask {self.task_type}>'