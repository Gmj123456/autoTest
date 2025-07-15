#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主页视图模块
"""

from flask import Blueprint, render_template, jsonify, current_app
from app.models import db, Project, TestCase, TestExecution, Bug, TestReport
from sqlalchemy import func
from datetime import datetime, timedelta
from loguru import logger

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """首页"""
    try:
        # 获取统计数据
        stats = get_dashboard_stats()
        
        # 获取最近的项目
        recent_projects = Project.query.order_by(Project.updated_at.desc()).limit(5).all()
        
        # 获取最近的测试执行
        recent_executions = TestExecution.query.order_by(TestExecution.created_at.desc()).limit(10).all()
        
        # 获取最近的Bug
        recent_bugs = Bug.query.filter(Bug.status.in_(['new', 'assigned', 'in_progress'])).order_by(Bug.created_at.desc()).limit(10).all()
        
        return render_template('main/index.html',
                             stats=stats,
                             recent_projects=recent_projects,
                             recent_executions=recent_executions,
                             recent_bugs=recent_bugs)
    except Exception as e:
        logger.error(f"首页加载失败: {e}")
        return render_template('main/index.html',
                             stats={},
                             recent_projects=[],
                             recent_executions=[],
                             recent_bugs=[])

@main_bp.route('/api/dashboard/stats')
def api_dashboard_stats():
    """获取仪表板统计数据API"""
    try:
        stats = get_dashboard_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@main_bp.route('/api/dashboard/charts')
def api_dashboard_charts():
    """获取仪表板图表数据API"""
    try:
        # 获取最近7天的测试执行趋势
        execution_trend = get_execution_trend()
        
        # 获取测试结果分布
        result_distribution = get_result_distribution()
        
        # 获取Bug状态分布
        bug_distribution = get_bug_distribution()
        
        # 获取项目测试覆盖率
        coverage_data = get_coverage_data()
        
        return jsonify({
            'success': True,
            'data': {
                'execution_trend': execution_trend,
                'result_distribution': result_distribution,
                'bug_distribution': bug_distribution,
                'coverage_data': coverage_data
            }
        })
    except Exception as e:
        logger.error(f"获取图表数据失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def get_dashboard_stats():
    """获取仪表板统计数据"""
    # 项目统计
    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(status='active').count()
    
    # 测试用例统计
    total_testcases = TestCase.query.count()
    active_testcases = TestCase.query.filter_by(status='active').count()
    ai_generated_cases = TestCase.query.filter_by(ai_generated=True).count()
    
    # 测试执行统计
    total_executions = TestExecution.query.count()
    today_executions = TestExecution.query.filter(
        func.date(TestExecution.created_at) == datetime.now().date()
    ).count()
    
    # 最近7天的执行统计
    week_ago = datetime.now() - timedelta(days=7)
    week_executions = TestExecution.query.filter(
        TestExecution.created_at >= week_ago
    ).count()
    
    # 测试结果统计
    passed_executions = TestExecution.query.filter_by(result='passed').count()
    failed_executions = TestExecution.query.filter_by(result='failed').count()
    
    # 计算通过率
    total_completed = passed_executions + failed_executions
    pass_rate = (passed_executions / total_completed * 100) if total_completed > 0 else 0
    
    # Bug统计
    total_bugs = Bug.query.count()
    open_bugs = Bug.query.filter(Bug.status.in_(['new', 'assigned', 'in_progress'])).count()
    resolved_bugs = Bug.query.filter_by(status='resolved').count()
    
    # AI功能统计
    ai_tasks_today = 0  # 这里可以添加AI任务的统计
    
    return {
        'projects': {
            'total': total_projects,
            'active': active_projects
        },
        'testcases': {
            'total': total_testcases,
            'active': active_testcases,
            'ai_generated': ai_generated_cases
        },
        'executions': {
            'total': total_executions,
            'today': today_executions,
            'week': week_executions,
            'passed': passed_executions,
            'failed': failed_executions,
            'pass_rate': round(pass_rate, 2)
        },
        'bugs': {
            'total': total_bugs,
            'open': open_bugs,
            'resolved': resolved_bugs
        },
        'ai': {
            'tasks_today': ai_tasks_today
        }
    }

def get_execution_trend():
    """获取最近7天的测试执行趋势"""
    trend_data = []
    for i in range(7):
        date = datetime.now().date() - timedelta(days=i)
        executions = TestExecution.query.filter(
            func.date(TestExecution.created_at) == date
        ).count()
        
        passed = TestExecution.query.filter(
            func.date(TestExecution.created_at) == date,
            TestExecution.result == 'passed'
        ).count()
        
        failed = TestExecution.query.filter(
            func.date(TestExecution.created_at) == date,
            TestExecution.result == 'failed'
        ).count()
        
        trend_data.append({
            'date': date.strftime('%m-%d'),
            'total': executions,
            'passed': passed,
            'failed': failed
        })
    
    return list(reversed(trend_data))

def get_result_distribution():
    """获取测试结果分布"""
    results = db.session.query(
        TestExecution.result,
        func.count(TestExecution.id).label('count')
    ).filter(
        TestExecution.result.isnot(None)
    ).group_by(TestExecution.result).all()
    
    return [{
        'name': result[0] or '未知',
        'value': result[1]
    } for result in results]

def get_bug_distribution():
    """获取Bug状态分布"""
    bugs = db.session.query(
        Bug.status,
        func.count(Bug.id).label('count')
    ).group_by(Bug.status).all()
    
    return [{
        'name': bug[0],
        'value': bug[1]
    } for bug in bugs]

def get_coverage_data():
    """获取项目测试覆盖率数据"""
    projects = Project.query.all()
    coverage_data = []
    
    for project in projects:
        total_cases = project.testcases.count()
        executed_cases = TestExecution.query.filter_by(project_id=project.id).distinct(TestExecution.testcase_id).count()
        
        coverage = (executed_cases / total_cases * 100) if total_cases > 0 else 0
        
        coverage_data.append({
            'project': project.name,
            'coverage': round(coverage, 2),
            'total_cases': total_cases,
            'executed_cases': executed_cases
        })
    
    return coverage_data

@main_bp.route('/health')
def health_check():
    """健康检查接口"""
    try:
        # 检查数据库连接
        db.session.execute('SELECT 1')
        
        # 检查配置
        config = current_app.config.get('YAML_CONFIG', {})
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'ai_enabled': bool(config.get('ai', {}).get('provider'))
        })
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500