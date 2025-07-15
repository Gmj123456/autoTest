#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI功能视图模块
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from app.models import db, Project, Module, TestCase, TestExecution, Bug, AITask
from app.services.ai_service import AIService
from datetime import datetime
from loguru import logger
import json

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/')
def index():
    """AI功能主页"""
    try:
        # 获取AI任务统计
        stats = get_ai_statistics()
        
        # 获取最近的AI任务
        recent_tasks = AITask.query.order_by(
            AITask.created_at.desc()
        ).limit(10).all()
        
        return render_template('ai/index.html',
                             stats=stats,
                             recent_tasks=recent_tasks)
    except Exception as e:
        logger.error(f"AI功能主页加载失败: {e}")
        flash('AI功能主页加载失败', 'error')
        return render_template('ai/index.html', stats={}, recent_tasks=[])

@ai_bp.route('/generate-testcase', methods=['GET', 'POST'])
def generate_testcase():
    """AI生成测试用例"""
    if request.method == 'GET':
        project_id = request.args.get('project_id', type=int)
        module_id = request.args.get('module_id', type=int)
        
        projects = Project.query.filter_by(status='active').all()
        modules = []
        
        if project_id:
            modules = Module.query.filter_by(
                project_id=project_id,
                status='active'
            ).all()
        
        return render_template('ai/generate_testcase.html',
                             projects=projects,
                             modules=modules,
                             selected_project_id=project_id,
                             selected_module_id=module_id)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('project_id'):
            return jsonify({'success': False, 'message': '请选择项目'}), 400
        
        if not data.get('requirement'):
            return jsonify({'success': False, 'message': '请输入需求描述'}), 400
        
        # 调用AI服务生成测试用例
        ai_service = AIService()
        result = ai_service.generate_test_cases(
            project_id=data['project_id'],
            module_id=data.get('module_id'),
            requirement=data['requirement'],
            test_type=data.get('test_type', 'functional'),
            priority=data.get('priority', 'medium'),
            count=data.get('count', 5)
        )
        
        if result['success']:
            logger.info(f"AI生成测试用例成功: 项目ID {data['project_id']}")
            
            return jsonify({
                'success': True,
                'message': 'AI生成测试用例成功',
                'data': {
                    'task_id': result['task_id'],
                    'test_cases': result.get('test_cases', [])
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI生成测试用例失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI生成测试用例失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ai_bp.route('/enhance-testcase', methods=['POST'])
def enhance_testcase():
    """AI增强测试用例"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('testcase_id'):
            return jsonify({'success': False, 'message': '请选择测试用例'}), 400
        
        testcase = TestCase.query.get_or_404(data['testcase_id'])
        
        # 调用AI服务增强测试用例
        ai_service = AIService()
        result = ai_service.enhance_test_case(
            testcase=testcase,
            enhancement_type=data.get('enhancement_type', 'steps'),
            context=data.get('context', '')
        )
        
        if result['success']:
            logger.info(f"AI增强测试用例成功: {testcase.title}")
            
            return jsonify({
                'success': True,
                'message': 'AI增强测试用例成功',
                'data': {
                    'task_id': result['task_id'],
                    'enhanced_content': result.get('enhanced_content', {})
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI增强测试用例失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI增强测试用例失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ai_bp.route('/analyze-execution', methods=['POST'])
def analyze_execution():
    """AI分析测试执行结果"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('execution_id'):
            return jsonify({'success': False, 'message': '请选择测试执行'}), 400
        
        execution = TestExecution.query.get_or_404(data['execution_id'])
        
        # 调用AI服务分析执行结果
        ai_service = AIService()
        result = ai_service.analyze_execution_result(
            execution=execution,
            analysis_type=data.get('analysis_type', 'failure')
        )
        
        if result['success']:
            # 保存分析结果
            analysis = result['analysis']
            execution.set_ai_analysis_result(analysis)
            execution.save()
            
            logger.info(f"AI分析测试执行成功: {execution.id}")
            
            return jsonify({
                'success': True,
                'message': 'AI分析测试执行成功',
                'data': {
                    'task_id': result['task_id'],
                    'analysis': analysis
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI分析测试执行失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI分析测试执行失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ai_bp.route('/analyze-bug', methods=['POST'])
def analyze_bug():
    """AI分析Bug根因"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('bug_id'):
            return jsonify({'success': False, 'message': '请选择Bug'}), 400
        
        bug = Bug.query.get_or_404(data['bug_id'])
        
        # 调用AI服务分析Bug根因
        ai_service = AIService()
        result = ai_service.analyze_bug_root_cause(
            bug=bug,
            include_similar=data.get('include_similar', True)
        )
        
        if result['success']:
            # 保存分析结果
            analysis = result['analysis']
            bug.set_ai_root_cause_analysis(analysis.get('root_cause', ''))
            
            if analysis.get('similar_bugs'):
                bug.set_ai_similar_bugs(analysis['similar_bugs'])
            
            bug.save()
            
            logger.info(f"AI分析Bug根因成功: {bug.title}")
            
            return jsonify({
                'success': True,
                'message': 'AI分析Bug根因成功',
                'data': {
                    'task_id': result['task_id'],
                    'analysis': analysis
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI分析Bug根因失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI分析Bug根因失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ai_bp.route('/find-similar-bugs', methods=['POST'])
def find_similar_bugs():
    """AI查找相似Bug"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('bug_id'):
            return jsonify({'success': False, 'message': '请选择Bug'}), 400
        
        bug = Bug.query.get_or_404(data['bug_id'])
        
        # 调用AI服务查找相似Bug
        ai_service = AIService()
        result = ai_service.find_similar_bugs(
            bug=bug,
            similarity_threshold=data.get('similarity_threshold', 0.7),
            max_results=data.get('max_results', 10)
        )
        
        if result['success']:
            logger.info(f"AI查找相似Bug成功: {bug.title}")
            
            return jsonify({
                'success': True,
                'message': 'AI查找相似Bug成功',
                'data': {
                    'task_id': result['task_id'],
                    'similar_bugs': result.get('similar_bugs', [])
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI查找相似Bug失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI查找相似Bug失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ai_bp.route('/risk-assessment', methods=['POST'])
def risk_assessment():
    """AI风险评估"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('project_id'):
            return jsonify({'success': False, 'message': '请选择项目'}), 400
        
        # 调用AI服务进行风险评估
        ai_service = AIService()
        result = ai_service.assess_project_risk(
            project_id=data['project_id'],
            assessment_type=data.get('assessment_type', 'comprehensive'),
            time_range=data.get('time_range', 30)  # 天数
        )
        
        if result['success']:
            logger.info(f"AI风险评估成功: 项目ID {data['project_id']}")
            
            return jsonify({
                'success': True,
                'message': 'AI风险评估成功',
                'data': {
                    'task_id': result['task_id'],
                    'assessment': result.get('assessment', {})
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI风险评估失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI风险评估失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ai_bp.route('/tasks')
def tasks():
    """AI任务列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        task_type = request.args.get('task_type', '')
        status = request.args.get('status', '')
        
        query = AITask.query
        
        # 任务类型过滤
        if task_type:
            query = query.filter_by(task_type=task_type)
        
        # 状态过滤
        if status:
            query = query.filter_by(status=status)
        
        # 分页
        tasks = query.order_by(AITask.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('ai/tasks.html',
                             tasks=tasks,
                             task_type=task_type,
                             status=status)
    except Exception as e:
        logger.error(f"AI任务列表加载失败: {e}")
        flash('AI任务列表加载失败', 'error')
        return render_template('ai/tasks.html', tasks=None)

@ai_bp.route('/tasks/<int:id>')
def task_detail(id):
    """AI任务详情"""
    try:
        task = AITask.query.get_or_404(id)
        
        # 解析任务结果
        result = task.get_result()
        parameters = task.get_parameters()
        
        return render_template('ai/task_detail.html',
                             task=task,
                             result=result,
                             parameters=parameters)
    except Exception as e:
        logger.error(f"AI任务详情加载失败: {e}")
        flash('AI任务详情加载失败', 'error')
        return redirect(url_for('ai.tasks'))

@ai_bp.route('/tasks/<int:id>/status')
def task_status(id):
    """获取AI任务状态"""
    try:
        task = AITask.query.get_or_404(id)
        
        return jsonify({
            'success': True,
            'data': {
                'id': task.id,
                'status': task.status,
                'progress': task.progress,
                'result': task.get_result() if task.status == 'completed' else None,
                'error_message': task.error_message
            }
        })
    except Exception as e:
        logger.error(f"获取AI任务状态失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ai_bp.route('/tasks/<int:id>/cancel', methods=['POST'])
def cancel_task(id):
    """取消AI任务"""
    try:
        task = AITask.query.get_or_404(id)
        
        if task.status in ['pending', 'running']:
            task.status = 'cancelled'
            task.save()
            
            logger.info(f"AI任务取消成功: {task.id}")
            
            return jsonify({
                'success': True,
                'message': 'AI任务取消成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务状态不允许取消'
            }), 400
            
    except Exception as e:
        logger.error(f"取消AI任务失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ai_bp.route('/api/statistics')
def api_statistics():
    """获取AI统计数据API"""
    try:
        stats = get_ai_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取AI统计数据失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ai_bp.route('/api/modules/<int:project_id>')
def api_modules(project_id):
    """获取项目模块API"""
    try:
        modules = Module.query.filter_by(
            project_id=project_id,
            status='active'
        ).all()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': module.id,
                'name': module.name,
                'description': module.description
            } for module in modules]
        })
    except Exception as e:
        logger.error(f"获取项目模块失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def get_ai_statistics():
    """获取AI统计数据"""
    try:
        # 任务统计
        total_tasks = AITask.query.count()
        completed_tasks = AITask.query.filter_by(status='completed').count()
        running_tasks = AITask.query.filter_by(status='running').count()
        failed_tasks = AITask.query.filter_by(status='failed').count()
        
        # 按类型统计
        task_type_stats = db.session.query(
            AITask.task_type,
            func.count(AITask.id).label('count')
        ).group_by(AITask.task_type).all()
        
        # 最近7天的任务趋势
        from datetime import timedelta
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_tasks = AITask.query.filter(
            AITask.created_at >= seven_days_ago
        ).count()
        
        # AI功能使用统计
        ai_enhanced_testcases = TestCase.query.filter(
            TestCase.ai_generated == True
        ).count()
        
        ai_analyzed_executions = TestExecution.query.filter(
            TestExecution.ai_analysis_result.isnot(None)
        ).count()
        
        ai_analyzed_bugs = Bug.query.filter(
            Bug.ai_root_cause_analysis.isnot(None)
        ).count()
        
        return {
            'tasks': {
                'total': total_tasks,
                'completed': completed_tasks,
                'running': running_tasks,
                'failed': failed_tasks,
                'recent': recent_tasks
            },
            'task_types': [{
                'type': item[0],
                'count': item[1]
            } for item in task_type_stats],
            'usage': {
                'ai_testcases': ai_enhanced_testcases,
                'ai_executions': ai_analyzed_executions,
                'ai_bugs': ai_analyzed_bugs
            }
        }
    except Exception as e:
        logger.error(f"获取AI统计数据失败: {e}")
        return {}