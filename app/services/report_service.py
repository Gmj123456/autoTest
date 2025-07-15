#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试报告服务模块
提供测试报告生成、统计分析等功能
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger
from flask import current_app, render_template_string
from app.models import db, Project, Module, TestCase, TestExecution, Bug, TestReport
from app.services.ai_service import AIService
from app.utils.chart_generator import ChartGenerator
from app.utils.file_utils import ensure_dir
import jinja2

class ReportService:
    """测试报告服务类"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.chart_generator = ChartGenerator()
    
    def generate_report(self, name: str, description: str, project_id: int,
                       start_date: datetime, end_date: datetime,
                       include_ai_analysis: bool = False) -> Dict[str, Any]:
        """生成测试报告"""
        try:
            # 创建报告记录
            report = TestReport(
                name=name,
                description=description,
                project_id=project_id,
                start_time=start_date,
                end_time=end_date,
                status='generating'
            )
            report.save()
            
            # 收集报告数据
            report_data = self._collect_report_data(project_id, start_date, end_date)
            
            # 计算统计指标
            statistics = self._calculate_statistics(report_data)
            
            # 更新报告统计信息
            report.total_cases = statistics['total_cases']
            report.executed_cases = statistics['executed_cases']
            report.passed_cases = statistics['passed_cases']
            report.failed_cases = statistics['failed_cases']
            report.pass_rate = statistics['pass_rate']
            report.bug_count = statistics['bug_count']
            
            # 生成图表
            charts = self._generate_charts(report_data, statistics)
            
            # 生成HTML报告
            report_html = self._generate_html_report(report, report_data, statistics, charts)
            
            # 保存报告文件
            report_path = self._save_report_file(report, report_html)
            report.report_path = report_path
            
            # AI分析（如果启用）
            if include_ai_analysis:
                self._add_ai_analysis(report, report_data)
            
            report.status = 'completed'
            report.save()
            
            logger.info(f"测试报告生成成功: {report.name}")
            
            return {
                'success': True,
                'report': report,
                'message': '测试报告生成成功'
            }
            
        except Exception as e:
            logger.error(f"生成测试报告失败: {e}")
            if 'report' in locals():
                report.status = 'failed'
                report.save()
            
            return {
                'success': False,
                'message': f'生成测试报告失败: {str(e)}'
            }
    
    def regenerate_report(self, report: TestReport) -> Dict[str, Any]:
        """重新生成测试报告"""
        try:
            # 重新收集数据并生成报告
            result = self.generate_report(
                name=report.name,
                description=report.description,
                project_id=report.project_id,
                start_date=report.start_time,
                end_date=report.end_time,
                include_ai_analysis=bool(report.ai_coverage_analysis)
            )
            
            if result['success']:
                # 删除旧报告文件
                if report.report_path and os.path.exists(report.report_path):
                    os.remove(report.report_path)
                
                # 更新报告记录
                new_report = result['report']
                report.total_cases = new_report.total_cases
                report.executed_cases = new_report.executed_cases
                report.passed_cases = new_report.passed_cases
                report.failed_cases = new_report.failed_cases
                report.pass_rate = new_report.pass_rate
                report.bug_count = new_report.bug_count
                report.report_path = new_report.report_path
                report.status = 'completed'
                report.updated_at = datetime.now()
                report.save()
                
                # 删除临时报告记录
                new_report.delete()
                
                logger.info(f"测试报告重新生成成功: {report.name}")
                
                return {
                    'success': True,
                    'message': '测试报告重新生成成功'
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"重新生成测试报告失败: {e}")
            return {
                'success': False,
                'message': f'重新生成测试报告失败: {str(e)}'
            }
    
    def _collect_report_data(self, project_id: int, start_date: datetime,
                           end_date: datetime) -> Dict[str, Any]:
        """收集报告数据"""
        try:
            # 获取项目信息
            project = Project.query.get(project_id)
            
            # 获取测试用例
            test_cases = TestCase.query.filter_by(project_id=project_id).all()
            
            # 获取测试执行记录
            executions = TestExecution.query.filter(
                TestExecution.project_id == project_id,
                TestExecution.created_at >= start_date,
                TestExecution.created_at <= end_date
            ).all()
            
            # 获取Bug记录
            bugs = Bug.query.filter(
                Bug.project_id == project_id,
                Bug.created_at >= start_date,
                Bug.created_at <= end_date
            ).all()
            
            # 获取模块信息
            modules = Module.query.filter_by(project_id=project_id).all()
            
            return {
                'project': project,
                'test_cases': test_cases,
                'executions': executions,
                'bugs': bugs,
                'modules': modules,
                'start_date': start_date,
                'end_date': end_date
            }
            
        except Exception as e:
            logger.error(f"收集报告数据失败: {e}")
            raise
    
    def _calculate_statistics(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算统计指标"""
        try:
            test_cases = report_data['test_cases']
            executions = report_data['executions']
            bugs = report_data['bugs']
            
            # 基本统计
            total_cases = len(test_cases)
            executed_cases = len(set(exec.test_case_id for exec in executions if exec.test_case_id))
            passed_cases = len([exec for exec in executions if exec.result == 'passed'])
            failed_cases = len([exec for exec in executions if exec.result == 'failed'])
            skipped_cases = len([exec for exec in executions if exec.result == 'skipped'])
            
            # 通过率计算
            pass_rate = round(passed_cases / executed_cases * 100, 2) if executed_cases > 0 else 0
            
            # Bug统计
            bug_count = len(bugs)
            open_bugs = len([bug for bug in bugs if bug.status in ['open', 'in_progress']])
            closed_bugs = len([bug for bug in bugs if bug.status == 'closed'])
            
            # 按优先级统计Bug
            bug_priority_stats = {
                'high': len([bug for bug in bugs if bug.priority == 'high']),
                'medium': len([bug for bug in bugs if bug.priority == 'medium']),
                'low': len([bug for bug in bugs if bug.priority == 'low'])
            }
            
            # 按模块统计
            module_stats = {}
            for module in report_data['modules']:
                module_cases = [case for case in test_cases if case.module_id == module.id]
                module_executions = [exec for exec in executions 
                                   if exec.test_case_id in [case.id for case in module_cases]]
                module_passed = len([exec for exec in module_executions if exec.result == 'passed'])
                module_total = len(module_executions)
                
                module_stats[module.name] = {
                    'total_cases': len(module_cases),
                    'executed_cases': module_total,
                    'passed_cases': module_passed,
                    'pass_rate': round(module_passed / module_total * 100, 2) if module_total > 0 else 0
                }
            
            # 按测试类型统计
            type_stats = {}
            for test_type in ['functional', 'ui', 'api', 'performance']:
                type_cases = [case for case in test_cases if case.test_type == test_type]
                type_executions = [exec for exec in executions 
                                 if exec.test_case_id in [case.id for case in type_cases]]
                type_passed = len([exec for exec in type_executions if exec.result == 'passed'])
                type_total = len(type_executions)
                
                type_stats[test_type] = {
                    'total_cases': len(type_cases),
                    'executed_cases': type_total,
                    'passed_cases': type_passed,
                    'pass_rate': round(type_passed / type_total * 100, 2) if type_total > 0 else 0
                }
            
            # 趋势数据
            daily_stats = self._calculate_daily_trends(executions, bugs, 
                                                     report_data['start_date'], 
                                                     report_data['end_date'])
            
            return {
                'total_cases': total_cases,
                'executed_cases': executed_cases,
                'passed_cases': passed_cases,
                'failed_cases': failed_cases,
                'skipped_cases': skipped_cases,
                'pass_rate': pass_rate,
                'bug_count': bug_count,
                'open_bugs': open_bugs,
                'closed_bugs': closed_bugs,
                'bug_priority_stats': bug_priority_stats,
                'module_stats': module_stats,
                'type_stats': type_stats,
                'daily_stats': daily_stats
            }
            
        except Exception as e:
            logger.error(f"计算统计指标失败: {e}")
            raise
    
    def _calculate_daily_trends(self, executions: List, bugs: List,
                              start_date: datetime, end_date: datetime) -> List[Dict]:
        """计算每日趋势数据"""
        daily_stats = []
        current_date = start_date.date()
        end_date = end_date.date()
        
        while current_date <= end_date:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            # 当天的执行统计
            day_executions = [exec for exec in executions 
                            if day_start <= exec.created_at <= day_end]
            
            day_passed = len([exec for exec in day_executions if exec.result == 'passed'])
            day_failed = len([exec for exec in day_executions if exec.result == 'failed'])
            day_total = len(day_executions)
            
            # 当天的Bug统计
            day_bugs = len([bug for bug in bugs 
                          if day_start <= bug.created_at <= day_end])
            
            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'total_executions': day_total,
                'passed_executions': day_passed,
                'failed_executions': day_failed,
                'pass_rate': round(day_passed / day_total * 100, 2) if day_total > 0 else 0,
                'new_bugs': day_bugs
            })
            
            current_date += timedelta(days=1)
        
        return daily_stats
    
    def _generate_charts(self, report_data: Dict[str, Any], 
                        statistics: Dict[str, Any]) -> Dict[str, str]:
        """生成图表"""
        try:
            charts = {}
            
            # 测试结果饼图
            charts['test_result_pie'] = self.chart_generator.create_pie_chart(
                labels=['通过', '失败', '跳过'],
                values=[
                    statistics['passed_cases'],
                    statistics['failed_cases'],
                    statistics['skipped_cases']
                ],
                title='测试结果分布'
            )
            
            # Bug优先级饼图
            charts['bug_priority_pie'] = self.chart_generator.create_pie_chart(
                labels=['高', '中', '低'],
                values=[
                    statistics['bug_priority_stats']['high'],
                    statistics['bug_priority_stats']['medium'],
                    statistics['bug_priority_stats']['low']
                ],
                title='Bug优先级分布'
            )
            
            # 每日趋势线图
            daily_stats = statistics['daily_stats']
            charts['daily_trend'] = self.chart_generator.create_line_chart(
                x_data=[item['date'] for item in daily_stats],
                y_data=[
                    [item['passed_executions'] for item in daily_stats],
                    [item['failed_executions'] for item in daily_stats]
                ],
                labels=['通过', '失败'],
                title='每日测试趋势'
            )
            
            # 模块通过率柱状图
            module_stats = statistics['module_stats']
            if module_stats:
                charts['module_pass_rate'] = self.chart_generator.create_bar_chart(
                    x_data=list(module_stats.keys()),
                    y_data=[stats['pass_rate'] for stats in module_stats.values()],
                    title='模块通过率'
                )
            
            return charts
            
        except Exception as e:
            logger.error(f"生成图表失败: {e}")
            return {}
    
    def _generate_html_report(self, report: TestReport, report_data: Dict[str, Any],
                            statistics: Dict[str, Any], charts: Dict[str, str]) -> str:
        """生成HTML报告"""
        try:
            # HTML模板
            template = """
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{{ report.name }} - 测试报告</title>
                <style>
                    body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #007bff; padding-bottom: 20px; }
                    .header h1 { color: #007bff; margin: 0; }
                    .header .meta { color: #666; margin-top: 10px; }
                    .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
                    .summary-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }
                    .summary-card h3 { margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; }
                    .summary-card .value { font-size: 28px; font-weight: bold; }
                    .section { margin-bottom: 30px; }
                    .section h2 { color: #333; border-left: 4px solid #007bff; padding-left: 15px; }
                    .chart-container { text-align: center; margin: 20px 0; }
                    .table { width: 100%; border-collapse: collapse; margin-top: 15px; }
                    .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                    .table th { background-color: #f8f9fa; font-weight: bold; }
                    .table tr:hover { background-color: #f5f5f5; }
                    .status-passed { color: #28a745; font-weight: bold; }
                    .status-failed { color: #dc3545; font-weight: bold; }
                    .status-skipped { color: #ffc107; font-weight: bold; }
                    .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }
                </style>
            </head>
            <body>
                <div class="container">
                    <!-- 报告头部 -->
                    <div class="header">
                        <h1>{{ report.name }}</h1>
                        <div class="meta">
                            <p>{{ report.description }}</p>
                            <p>项目: {{ project.name }} | 报告时间: {{ report.start_time.strftime('%Y-%m-%d') }} 至 {{ report.end_time.strftime('%Y-%m-%d') }}</p>
                            <p>生成时间: {{ report.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
                        </div>
                    </div>
                    
                    <!-- 概要统计 -->
                    <div class="summary">
                        <div class="summary-card">
                            <h3>总用例数</h3>
                            <div class="value">{{ statistics.total_cases }}</div>
                        </div>
                        <div class="summary-card">
                            <h3>执行用例数</h3>
                            <div class="value">{{ statistics.executed_cases }}</div>
                        </div>
                        <div class="summary-card">
                            <h3>通过率</h3>
                            <div class="value">{{ statistics.pass_rate }}%</div>
                        </div>
                        <div class="summary-card">
                            <h3>Bug数量</h3>
                            <div class="value">{{ statistics.bug_count }}</div>
                        </div>
                    </div>
                    
                    <!-- 测试结果分析 -->
                    <div class="section">
                        <h2>测试结果分析</h2>
                        <div class="chart-container">
                            {{ charts.test_result_pie | safe }}
                        </div>
                        
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>结果</th>
                                    <th>数量</th>
                                    <th>占比</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td class="status-passed">通过</td>
                                    <td>{{ statistics.passed_cases }}</td>
                                    <td>{{ '%.1f' | format(statistics.passed_cases / statistics.executed_cases * 100 if statistics.executed_cases > 0 else 0) }}%</td>
                                </tr>
                                <tr>
                                    <td class="status-failed">失败</td>
                                    <td>{{ statistics.failed_cases }}</td>
                                    <td>{{ '%.1f' | format(statistics.failed_cases / statistics.executed_cases * 100 if statistics.executed_cases > 0 else 0) }}%</td>
                                </tr>
                                <tr>
                                    <td class="status-skipped">跳过</td>
                                    <td>{{ statistics.skipped_cases }}</td>
                                    <td>{{ '%.1f' | format(statistics.skipped_cases / statistics.executed_cases * 100 if statistics.executed_cases > 0 else 0) }}%</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- 模块分析 -->
                    {% if statistics.module_stats %}
                    <div class="section">
                        <h2>模块分析</h2>
                        <div class="chart-container">
                            {{ charts.module_pass_rate | safe }}
                        </div>
                        
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>模块</th>
                                    <th>总用例</th>
                                    <th>执行用例</th>
                                    <th>通过用例</th>
                                    <th>通过率</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for module_name, stats in statistics.module_stats.items() %}
                                <tr>
                                    <td>{{ module_name }}</td>
                                    <td>{{ stats.total_cases }}</td>
                                    <td>{{ stats.executed_cases }}</td>
                                    <td>{{ stats.passed_cases }}</td>
                                    <td>{{ stats.pass_rate }}%</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    {% endif %}
                    
                    <!-- Bug分析 -->
                    {% if statistics.bug_count > 0 %}
                    <div class="section">
                        <h2>Bug分析</h2>
                        <div class="chart-container">
                            {{ charts.bug_priority_pie | safe }}
                        </div>
                        
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>优先级</th>
                                    <th>数量</th>
                                    <th>占比</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>高</td>
                                    <td>{{ statistics.bug_priority_stats.high }}</td>
                                    <td>{{ '%.1f' | format(statistics.bug_priority_stats.high / statistics.bug_count * 100 if statistics.bug_count > 0 else 0) }}%</td>
                                </tr>
                                <tr>
                                    <td>中</td>
                                    <td>{{ statistics.bug_priority_stats.medium }}</td>
                                    <td>{{ '%.1f' | format(statistics.bug_priority_stats.medium / statistics.bug_count * 100 if statistics.bug_count > 0 else 0) }}%</td>
                                </tr>
                                <tr>
                                    <td>低</td>
                                    <td>{{ statistics.bug_priority_stats.low }}</td>
                                    <td>{{ '%.1f' | format(statistics.bug_priority_stats.low / statistics.bug_count * 100 if statistics.bug_count > 0 else 0) }}%</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    {% endif %}
                    
                    <!-- 趋势分析 -->
                    <div class="section">
                        <h2>趋势分析</h2>
                        <div class="chart-container">
                            {{ charts.daily_trend | safe }}
                        </div>
                    </div>
                    
                    <!-- AI分析结果 -->
                    {% if report.ai_coverage_analysis %}
                    <div class="section">
                        <h2>AI分析结果</h2>
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
                            <h3>覆盖度分析</h3>
                            <p>{{ report.get_ai_coverage_analysis().get('summary', '暂无分析结果') }}</p>
                        </div>
                        
                        {% if report.ai_quality_assessment %}
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
                            <h3>质量评估</h3>
                            <p>{{ report.get_ai_quality_assessment().get('summary', '暂无评估结果') }}</p>
                        </div>
                        {% endif %}
                        
                        {% if report.ai_recommendations %}
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
                            <h3>改进建议</h3>
                            <ul>
                                {% for recommendation in report.get_ai_recommendations() %}
                                <li>{{ recommendation }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                        {% endif %}
                    </div>
                    {% endif %}
                    
                    <!-- 页脚 -->
                    <div class="footer">
                        <p>本报告由AI增强自动化测试平台生成</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # 渲染模板
            template_obj = jinja2.Template(template)
            html_content = template_obj.render(
                report=report,
                project=report_data['project'],
                statistics=statistics,
                charts=charts
            )
            
            return html_content
            
        except Exception as e:
            logger.error(f"生成HTML报告失败: {e}")
            raise
    
    def _save_report_file(self, report: TestReport, html_content: str) -> str:
        """保存报告文件"""
        try:
            # 创建报告目录
            reports_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reports')
            ensure_dir(reports_dir)
            
            # 生成文件名
            filename = f"report_{report.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            file_path = os.path.join(reports_dir, filename)
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"报告文件保存成功: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"保存报告文件失败: {e}")
            raise
    
    def _add_ai_analysis(self, report: TestReport, report_data: Dict[str, Any]):
        """添加AI分析"""
        try:
            # 调用AI服务分析报告
            result = self.ai_service.analyze_test_report(report)
            
            if result['success']:
                logger.info(f"AI分析报告任务已启动: 任务ID {result['task_id']}")
            else:
                logger.warning(f"AI分析报告启动失败: {result['message']}")
                
        except Exception as e:
            logger.error(f"添加AI分析失败: {e}")