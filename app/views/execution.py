#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试执行视图模块
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from app.models import db, Project, TestCase, TestExecution, Bug
from app.services.execution_service import ExecutionService
from app.services.ai_service import AIService
from datetime import datetime
from loguru import logger
import json

execution_bp = Blueprint('execution', __name__)

@execution_bp.route('/')
def index():
    """测试执行列表页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        project_id = request.args.get('project_id', type=int)
        status = request.args.get('status', '')
        result = request.args.get('result', '')
        
        query = TestExecution.query
        
        # 项目过滤
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        # 搜索过滤
        if search:
            query = query.filter(
                db.or_(
                    TestExecution.name.contains(search),
                    TestExecution.description.contains(search)
                )
            )
        
        # 状态过滤
        if status:
            query = query.filter_by(status=status)
        
        # 结果过滤
        if result:
            query = query.filter_by(result=result)
        
        # 分页
        executions = query.order_by(TestExecution.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取项目列表用于过滤
        projects = Project.query.filter_by(status='active').all()
        
        return render_template('execution/index.html',
                             executions=executions,
                             projects=projects,
                             search=search,
                             project_id=project_id,
                             status=status,
                             result=result)
    except Exception as e:
        logger.error(f"测试执行列表加载失败: {e}")
        flash('测试执行列表加载失败', 'error')
        return render_template('execution/index.html', executions=None)

@execution_bp.route('/create', methods=['GET', 'POST'])
def create():
    """创建测试执行"""
    if request.method == 'GET':
        project_id = request.args.get('project_id', type=int)
        testcase_id = request.args.get('testcase_id', type=int)
        
        projects = Project.query.filter_by(status='active').all()
        testcases = TestCase.query.filter_by(project_id=project_id, status='active').all() if project_id else []
        
        # 获取配置信息
        config = current_app.config.get('YAML_CONFIG', {})
        browser_config = config.get('browser', {})
        environment_config = config.get('environment', {})
        
        return render_template('execution/create.html',
                             projects=projects,
                             testcases=testcases,
                             selected_project_id=project_id,
                             selected_testcase_id=testcase_id,
                             browser_config=browser_config,
                             environment_config=environment_config)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({'success': False, 'message': '执行名称不能为空'}), 400
        
        if not data.get('project_id'):
            return jsonify({'success': False, 'message': '请选择项目'}), 400
        
        # 创建测试执行
        execution = TestExecution(
            name=data['name'],
            description=data.get('description', ''),
            project_id=data['project_id'],
            testcase_id=data.get('testcase_id'),
            executor=data.get('executor', ''),
            browser=data.get('browser', 'chrome'),
            environment=data.get('environment', 'test'),
            status='pending'
        )
        
        execution.save()
        
        logger.info(f"测试执行创建成功: {execution.name}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': '测试执行创建成功',
                'data': execution.to_dict()
            })
        else:
            flash('测试执行创建成功', 'success')
            return redirect(url_for('execution.detail', id=execution.id))
            
    except Exception as e:
        logger.error(f"测试执行创建失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('测试执行创建失败', 'error')
            return redirect(url_for('execution.create'))

@execution_bp.route('/<int:id>')
def detail(id):
    """测试执行详情页面"""
    try:
        execution = TestExecution.query.get_or_404(id)
        
        # 获取截图列表
        screenshots = execution.get_screenshots()
        
        # 获取AI分析结果
        ai_analysis = execution.get_ai_analysis()
        
        # 获取相关Bug
        related_bugs = Bug.query.filter_by(execution_id=id).all()
        
        return render_template('execution/detail.html',
                             execution=execution,
                             screenshots=screenshots,
                             ai_analysis=ai_analysis,
                             related_bugs=related_bugs)
    except Exception as e:
        logger.error(f"测试执行详情加载失败: {e}")
        flash('测试执行详情加载失败', 'error')
        return redirect(url_for('execution.index'))

@execution_bp.route('/<int:id>/run', methods=['POST'])
def run(id):
    """运行测试执行"""
    try:
        execution = TestExecution.query.get_or_404(id)
        
        if execution.status == 'running':
            return jsonify({'success': False, 'message': '测试正在运行中'}), 400
        
        # 更新状态
        execution.status = 'running'
        execution.start_time = datetime.utcnow()
        execution.save()
        
        # 异步执行测试
        execution_service = ExecutionService()
        task = execution_service.run_execution_async(execution.id)
        
        logger.info(f"测试执行开始: {execution.name}")
        
        return jsonify({
            'success': True,
            'message': '测试执行已开始',
            'task_id': task.id if task else None
        })
        
    except Exception as e:
        logger.error(f"测试执行启动失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@execution_bp.route('/<int:id>/stop', methods=['POST'])
def stop(id):
    """停止测试执行"""
    try:
        execution = TestExecution.query.get_or_404(id)
        
        if execution.status != 'running':
            return jsonify({'success': False, 'message': '测试未在运行中'}), 400
        
        # 停止执行
        execution_service = ExecutionService()
        execution_service.stop_execution(execution.id)
        
        # 更新状态
        execution.status = 'stopped'
        execution.end_time = datetime.utcnow()
        if execution.start_time:
            duration = (execution.end_time - execution.start_time).total_seconds()
            execution.duration = int(duration)
        execution.save()
        
        logger.info(f"测试执行停止: {execution.name}")
        
        return jsonify({
            'success': True,
            'message': '测试执行已停止'
        })
        
    except Exception as e:
        logger.error(f"测试执行停止失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@execution_bp.route('/<int:id>/status')
def status(id):
    """获取测试执行状态"""
    try:
        execution = TestExecution.query.get_or_404(id)
        
        return jsonify({
            'success': True,
            'data': {
                'id': execution.id,
                'status': execution.status,
                'result': execution.result,
                'start_time': execution.start_time.isoformat() if execution.start_time else None,
                'end_time': execution.end_time.isoformat() if execution.end_time else None,
                'duration': execution.duration,
                'error_message': execution.error_message
            }
        })
        
    except Exception as e:
        logger.error(f"获取测试执行状态失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@execution_bp.route('/<int:id>/logs')
def logs(id):
    """获取测试执行日志"""
    try:
        execution = TestExecution.query.get_or_404(id)
        
        return jsonify({
            'success': True,
            'data': {
                'logs': execution.logs or '',
                'error_message': execution.error_message or ''
            }
        })
        
    except Exception as e:
        logger.error(f"获取测试执行日志失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@execution_bp.route('/<int:id>/ai-analyze', methods=['POST'])
def ai_analyze(id):
    """AI分析测试执行结果"""
    try:
        execution = TestExecution.query.get_or_404(id)
        
        if execution.status == 'running':
            return jsonify({'success': False, 'message': '测试正在运行中，无法分析'}), 400
        
        # 调用AI服务分析
        ai_service = AIService()
        result = ai_service.analyze_execution_result(execution)
        
        if result['success']:
            # 保存分析结果
            execution.set_ai_analysis(result['analysis'])
            execution.save()
            
            logger.info(f"AI分析测试执行完成: {execution.name}")
            
            return jsonify({
                'success': True,
                'message': 'AI分析完成',
                'data': result['analysis']
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI分析失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI分析测试执行失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@execution_bp.route('/<int:id>/create-bug', methods=['POST'])
def create_bug(id):
    """从测试执行创建Bug"""
    try:
        execution = TestExecution.query.get_or_404(id)
        data = request.get_json()
        
        if execution.result != 'failed':
            return jsonify({'success': False, 'message': '只能从失败的测试执行创建Bug'}), 400
        
        # 创建Bug
        bug = Bug(
            title=data.get('title', f"测试执行失败: {execution.name}"),
            description=data.get('description', execution.error_message or ''),
            severity=data.get('severity', 'medium'),
            priority=data.get('priority', 'medium'),
            status='new',
            type='execution_failure',
            project_id=execution.project_id,
            testcase_id=execution.testcase_id,
            execution_id=execution.id,
            reporter=data.get('reporter', ''),
            steps_to_reproduce=execution.logs or '',
            environment_info=json.dumps({
                'browser': execution.browser,
                'environment': execution.environment,
                'execution_time': execution.start_time.isoformat() if execution.start_time else None
            })
        )
        
        # 添加截图作为附件
        screenshots = execution.get_screenshots()
        for screenshot in screenshots:
            bug.add_attachment(screenshot)
        
        bug.save()
        
        logger.info(f"从测试执行创建Bug成功: {bug.title}")
        
        return jsonify({
            'success': True,
            'message': 'Bug创建成功',
            'data': bug.to_dict()
        })
        
    except Exception as e:
        logger.error(f"从测试执行创建Bug失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@execution_bp.route('/batch', methods=['POST'])
def batch_execute():
    """批量执行测试用例"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({'success': False, 'message': '批量执行名称不能为空'}), 400
        
        if not data.get('project_id'):
            return jsonify({'success': False, 'message': '请选择项目'}), 400
        
        if not data.get('testcase_ids'):
            return jsonify({'success': False, 'message': '请选择测试用例'}), 400
        
        # 创建批量执行任务
        execution_service = ExecutionService()
        result = execution_service.create_batch_execution(
            name=data['name'],
            description=data.get('description', ''),
            project_id=data['project_id'],
            testcase_ids=data['testcase_ids'],
            executor=data.get('executor', ''),
            browser=data.get('browser', 'chrome'),
            environment=data.get('environment', 'test')
        )
        
        if result['success']:
            logger.info(f"批量执行创建成功: {data['name']}")
            
            return jsonify({
                'success': True,
                'message': '批量执行创建成功',
                'data': result['executions']
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '批量执行创建失败')
            }), 500
            
    except Exception as e:
        logger.error(f"批量执行创建失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@execution_bp.route('/api/testcases/<int:project_id>')
def api_get_testcases(project_id):
    """获取项目下的测试用例列表API"""
    try:
        testcases = TestCase.query.filter_by(
            project_id=project_id,
            status='active'
        ).all()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': tc.id,
                'title': tc.title,
                'priority': tc.priority,
                'type': tc.type,
                'module_name': tc.module.name if tc.module else ''
            } for tc in testcases]
        })
    except Exception as e:
        logger.error(f"获取测试用例列表失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500