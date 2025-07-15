#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试报告视图模块
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, send_file
from app.models import db, Project, TestCase, TestExecution, Bug, TestReport
from app.services.report_service import ReportService
from app.services.ai_service import AIService
from datetime import datetime, timedelta
from loguru import logger
import os
import json

report_bp = Blueprint('report', __name__)

@report_bp.route('/')
def index():
    """测试报告列表页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        project_id = request.args.get('project_id', type=int)
        
        query = TestReport.query
        
        # 项目过滤
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        # 搜索过滤
        if search:
            query = query.filter(
                db.or_(
                    TestReport.name.contains(search),
                    TestReport.description.contains(search)
                )
            )
        
        # 分页
        reports = query.order_by(TestReport.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取项目列表用于过滤
        projects = Project.query.filter_by(status='active').all()
        
        return render_template('report/index.html',
                             reports=reports,
                             projects=projects,
                             search=search,
                             project_id=project_id)
    except Exception as e:
        logger.error(f"测试报告列表加载失败: {e}")
        flash('测试报告列表加载失败', 'error')
        return render_template('report/index.html', reports=None)

@report_bp.route('/create', methods=['GET', 'POST'])
def create():
    """创建测试报告"""
    if request.method == 'GET':
        project_id = request.args.get('project_id', type=int)
        projects = Project.query.filter_by(status='active').all()
        
        return render_template('report/create.html',
                             projects=projects,
                             selected_project_id=project_id)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({'success': False, 'message': '报告名称不能为空'}), 400
        
        if not data.get('project_id'):
            return jsonify({'success': False, 'message': '请选择项目'}), 400
        
        # 获取时间范围
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start_date = datetime.now() - timedelta(days=7)  # 默认最近7天
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end_date = datetime.now()
        
        # 生成测试报告
        report_service = ReportService()
        result = report_service.generate_report(
            name=data['name'],
            description=data.get('description', ''),
            project_id=data['project_id'],
            start_date=start_date,
            end_date=end_date,
            include_ai_analysis=data.get('include_ai_analysis', False)
        )
        
        if result['success']:
            logger.info(f"测试报告生成成功: {result['report'].name}")
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': '测试报告生成成功',
                    'data': result['report'].to_dict()
                })
            else:
                flash('测试报告生成成功', 'success')
                return redirect(url_for('report.detail', id=result['report'].id))
        else:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': result.get('message', '测试报告生成失败')
                }), 500
            else:
                flash('测试报告生成失败', 'error')
                return redirect(url_for('report.create'))
            
    except Exception as e:
        logger.error(f"测试报告生成失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('测试报告生成失败', 'error')
            return redirect(url_for('report.create'))

@report_bp.route('/<int:id>')
def detail(id):
    """测试报告详情页面"""
    try:
        report = TestReport.query.get_or_404(id)
        
        # 获取AI分析结果
        coverage_analysis = report.get_ai_coverage_analysis()
        quality_assessment = report.get_ai_quality_assessment()
        recommendations = report.get_ai_recommendations()
        
        # 获取报告期间的执行数据
        executions = TestExecution.query.filter(
            TestExecution.project_id == report.project_id,
            TestExecution.created_at >= report.start_time,
            TestExecution.created_at <= report.end_time
        ).order_by(TestExecution.created_at.desc()).all()
        
        # 获取报告期间的Bug数据
        bugs = Bug.query.filter(
            Bug.project_id == report.project_id,
            Bug.created_at >= report.start_time,
            Bug.created_at <= report.end_time
        ).order_by(Bug.created_at.desc()).all()
        
        # 计算趋势数据
        trend_data = calculate_trend_data(report)
        
        return render_template('report/detail.html',
                             report=report,
                             coverage_analysis=coverage_analysis,
                             quality_assessment=quality_assessment,
                             recommendations=recommendations,
                             executions=executions,
                             bugs=bugs,
                             trend_data=trend_data)
    except Exception as e:
        logger.error(f"测试报告详情加载失败: {e}")
        flash('测试报告详情加载失败', 'error')
        return redirect(url_for('report.index'))

@report_bp.route('/<int:id>/download')
def download(id):
    """下载测试报告"""
    try:
        report = TestReport.query.get_or_404(id)
        
        if not report.report_path or not os.path.exists(report.report_path):
            flash('报告文件不存在', 'error')
            return redirect(url_for('report.detail', id=id))
        
        return send_file(
            report.report_path,
            as_attachment=True,
            download_name=f"{report.name}.html"
        )
        
    except Exception as e:
        logger.error(f"测试报告下载失败: {e}")
        flash('测试报告下载失败', 'error')
        return redirect(url_for('report.detail', id=id))

@report_bp.route('/<int:id>/regenerate', methods=['POST'])
def regenerate(id):
    """重新生成测试报告"""
    try:
        report = TestReport.query.get_or_404(id)
        
        # 重新生成报告
        report_service = ReportService()
        result = report_service.regenerate_report(report)
        
        if result['success']:
            logger.info(f"测试报告重新生成成功: {report.name}")
            
            return jsonify({
                'success': True,
                'message': '测试报告重新生成成功',
                'data': report.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '测试报告重新生成失败')
            }), 500
            
    except Exception as e:
        logger.error(f"测试报告重新生成失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@report_bp.route('/<int:id>/ai-analyze', methods=['POST'])
def ai_analyze(id):
    """AI分析测试报告"""
    try:
        report = TestReport.query.get_or_404(id)
        
        # 调用AI服务分析报告
        ai_service = AIService()
        result = ai_service.analyze_test_report(report)
        
        if result['success']:
            # 保存分析结果
            analysis = result['analysis']
            
            if analysis.get('coverage_analysis'):
                report.set_ai_coverage_analysis(analysis['coverage_analysis'])
            
            if analysis.get('quality_assessment'):
                report.set_ai_quality_assessment(analysis['quality_assessment'])
            
            if analysis.get('recommendations'):
                report.set_ai_recommendations(analysis['recommendations'])
            
            report.save()
            
            logger.info(f"AI分析测试报告完成: {report.name}")
            
            return jsonify({
                'success': True,
                'message': 'AI分析完成',
                'data': analysis
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI分析失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI分析测试报告失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@report_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """删除测试报告"""
    try:
        report = TestReport.query.get_or_404(id)
        report_name = report.name
        
        # 删除报告文件
        if report.report_path and os.path.exists(report.report_path):
            os.remove(report.report_path)
        
        # 删除数据库记录
        report.delete()
        
        logger.info(f"测试报告删除成功: {report_name}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': '测试报告删除成功'
            })
        else:
            flash('测试报告删除成功', 'success')
            return redirect(url_for('report.index'))
            
    except Exception as e:
        logger.error(f"测试报告删除失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('测试报告删除失败', 'error')
            return redirect(url_for('report.index'))

@report_bp.route('/dashboard')
def dashboard():
    """测试报告仪表板"""
    try:
        # 获取最近的报告
        recent_reports = TestReport.query.order_by(
            TestReport.created_at.desc()
        ).limit(10).all()
        
        # 获取统计数据
        stats = get_report_statistics()
        
        # 获取趋势数据
        trend_data = get_trend_statistics()
        
        return render_template('report/dashboard.html',
                             recent_reports=recent_reports,
                             stats=stats,
                             trend_data=trend_data)
    except Exception as e:
        logger.error(f"测试报告仪表板加载失败: {e}")
        flash('测试报告仪表板加载失败', 'error')
        return redirect(url_for('report.index'))

@report_bp.route('/api/statistics')
def api_statistics():
    """获取报告统计数据API"""
    try:
        stats = get_report_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取报告统计数据失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def calculate_trend_data(report):
    """计算报告的趋势数据"""
    try:
        # 按天统计执行数据
        daily_stats = []
        current_date = report.start_time.date()
        end_date = report.end_time.date()
        
        while current_date <= end_date:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            # 当天的执行统计
            total_executions = TestExecution.query.filter(
                TestExecution.project_id == report.project_id,
                TestExecution.created_at >= day_start,
                TestExecution.created_at <= day_end
            ).count()
            
            passed_executions = TestExecution.query.filter(
                TestExecution.project_id == report.project_id,
                TestExecution.created_at >= day_start,
                TestExecution.created_at <= day_end,
                TestExecution.result == 'passed'
            ).count()
            
            failed_executions = TestExecution.query.filter(
                TestExecution.project_id == report.project_id,
                TestExecution.created_at >= day_start,
                TestExecution.created_at <= day_end,
                TestExecution.result == 'failed'
            ).count()
            
            # 当天的Bug统计
            new_bugs = Bug.query.filter(
                Bug.project_id == report.project_id,
                Bug.created_at >= day_start,
                Bug.created_at <= day_end
            ).count()
            
            daily_stats.append({
                'date': current_date.strftime('%m-%d'),
                'total_executions': total_executions,
                'passed_executions': passed_executions,
                'failed_executions': failed_executions,
                'new_bugs': new_bugs,
                'pass_rate': round(passed_executions / total_executions * 100, 2) if total_executions > 0 else 0
            })
            
            current_date += timedelta(days=1)
        
        return daily_stats
    except Exception as e:
        logger.error(f"计算趋势数据失败: {e}")
        return []

def get_report_statistics():
    """获取报告统计数据"""
    try:
        # 总体统计
        total_reports = TestReport.query.count()
        
        # 最近30天的报告
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_reports = TestReport.query.filter(
            TestReport.created_at >= thirty_days_ago
        ).count()
        
        # 按项目统计
        project_stats = db.session.query(
            Project.name,
            func.count(TestReport.id).label('count'),
            func.avg(TestReport.pass_rate).label('avg_pass_rate')
        ).join(TestReport).group_by(Project.name).all()
        
        # 通过率趋势（最近12个月）
        monthly_pass_rate = db.session.query(
            func.date_format(TestReport.created_at, '%Y-%m').label('month'),
            func.avg(TestReport.pass_rate).label('avg_pass_rate')
        ).filter(
            TestReport.created_at >= func.date_sub(func.now(), text('INTERVAL 12 MONTH'))
        ).group_by('month').order_by('month').all()
        
        return {
            'total': {
                'total_reports': total_reports,
                'recent_reports': recent_reports
            },
            'project': [{
                'name': item[0],
                'count': item[1],
                'avg_pass_rate': round(item[2] or 0, 2)
            } for item in project_stats],
            'monthly_pass_rate': [{
                'month': item[0],
                'pass_rate': round(item[1] or 0, 2)
            } for item in monthly_pass_rate]
        }
    except Exception as e:
        logger.error(f"获取报告统计数据失败: {e}")
        return {}

def get_trend_statistics():
    """获取趋势统计数据"""
    try:
        # 最近7天的报告生成趋势
        trend_data = []
        for i in range(7):
            date = datetime.now().date() - timedelta(days=i)
            reports_count = TestReport.query.filter(
                func.date(TestReport.created_at) == date
            ).count()
            
            trend_data.append({
                'date': date.strftime('%m-%d'),
                'count': reports_count
            })
        
        return list(reversed(trend_data))
    except Exception as e:
        logger.error(f"获取趋势统计数据失败: {e}")
        return []