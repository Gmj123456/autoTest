#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试报告相关异步任务
"""

import json
from datetime import datetime, timedelta
from loguru import logger
from celery import current_task
from app.tasks import celery
from app.models import db, TestReport, TestExecution, TestCase, Bug, Project
from app.services.report_service import ReportService
from app.services.ai_service import AIService
from app.utils.data_processor import DataProcessor

@celery.task(bind=True)
def generate_test_report(self, project_id, report_config=None):
    """生成测试报告任务
    
    Args:
        project_id: 项目ID
        report_config: 报告配置
    
    Returns:
        报告生成结果
    """
    try:
        logger.info(f"开始生成测试报告任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '获取项目信息'})
        
        # 获取项目
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        # 解析报告配置
        config = report_config or {}
        report_type = config.get('type', 'comprehensive')  # comprehensive, execution, bug, coverage
        time_range = config.get('time_range', 30)  # 默认30天
        include_ai_analysis = config.get('include_ai_analysis', True)
        
        # 创建测试报告记录
        test_report = TestReport(
            project_id=project_id,
            report_type=report_type,
            status='generating',
            task_id=self.request.id,
            config=json.dumps(config, ensure_ascii=False)
        )
        db.session.add(test_report)
        db.session.commit()
        
        self.update_state(state='PROGRESS', meta={
            'progress': 20, 
            'message': '收集报告数据',
            'report_id': test_report.id
        })
        
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_range)
        
        # 收集数据
        test_cases = TestCase.query.filter_by(project_id=project_id).all()
        
        executions = TestExecution.query.join(TestCase).filter(
            TestCase.project_id == project_id,
            TestExecution.created_at >= start_date,
            TestExecution.created_at <= end_date
        ).all()
        
        bugs = Bug.query.filter(
            Bug.project_id == project_id,
            Bug.created_at >= start_date,
            Bug.created_at <= end_date
        ).all()
        
        self.update_state(state='PROGRESS', meta={
            'progress': 40, 
            'message': '初始化报告服务',
            'report_id': test_report.id
        })
        
        # 初始化服务
        from app import create_app
        app = create_app()
        report_service = ReportService(app.config)
        data_processor = DataProcessor()
        
        self.update_state(state='PROGRESS', meta={
            'progress': 60, 
            'message': '生成报告内容',
            'report_id': test_report.id
        })
        
        # 准备报告数据
        report_data = {
            'project': project.to_dict(),
            'test_cases': [case.to_dict() for case in test_cases],
            'executions': [execution.to_dict() for execution in executions],
            'bugs': [bug.to_dict() for bug in bugs],
            'time_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': time_range
            }
        }
        
        # 生成报告
        if report_type == 'comprehensive':
            result = report_service.generate_comprehensive_report(report_data)
        elif report_type == 'execution':
            result = report_service.generate_execution_report(report_data)
        elif report_type == 'bug':
            result = report_service.generate_bug_report(report_data)
        elif report_type == 'coverage':
            result = report_service.generate_coverage_report(report_data)
        else:
            raise ValueError(f"不支持的报告类型: {report_type}")
        
        self.update_state(state='PROGRESS', meta={
            'progress': 80, 
            'message': 'AI分析报告',
            'report_id': test_report.id
        })
        
        # AI分析报告（如果启用）
        ai_analysis_result = None
        if include_ai_analysis:
            try:
                ai_service = AIService(app.config.get('AI', {}))
                ai_analysis_result = ai_service.analyze_test_report(result)
                
                if ai_analysis_result.get('success'):
                    result['ai_analysis'] = ai_analysis_result
            except Exception as e:
                logger.warning(f"AI分析报告失败: {e}")
        
        self.update_state(state='PROGRESS', meta={
            'progress': 90, 
            'message': '保存报告',
            'report_id': test_report.id
        })
        
        # 更新报告记录
        test_report.status = 'completed'
        test_report.content = json.dumps(result, ensure_ascii=False)
        test_report.file_path = result.get('file_path', '')
        test_report.summary = json.dumps(result.get('summary', {}), ensure_ascii=False)
        
        if ai_analysis_result:
            test_report.ai_analysis_result = json.dumps(ai_analysis_result, ensure_ascii=False)
        
        test_report.completed_at = datetime.now()
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '报告生成完成',
            'report_id': test_report.id,
            'result': {
                'report_id': test_report.id,
                'file_path': result.get('file_path'),
                'summary': result.get('summary')
            }
        })
        
        logger.info(f"测试报告生成任务完成: {self.request.id}, 报告ID: {test_report.id}")
        
        return {
            'success': True,
            'report_id': test_report.id,
            'file_path': result.get('file_path'),
            'summary': result.get('summary'),
            'ai_analysis': ai_analysis_result
        }
        
    except Exception as e:
        logger.error(f"测试报告生成任务失败: {e}")
        
        # 更新报告状态
        try:
            test_report = TestReport.query.filter_by(task_id=self.request.id).first()
            if test_report:
                test_report.status = 'failed'
                test_report.error_message = str(e)
                test_report.completed_at = datetime.now()
                db.session.commit()
        except:
            pass
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'报告生成失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def generate_daily_report(self, project_id=None):
    """生成日报任务
    
    Args:
        project_id: 项目ID，如果为None则生成所有项目的日报
    
    Returns:
        日报生成结果
    """
    try:
        logger.info(f"开始生成日报任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '获取项目列表'})
        
        # 获取项目列表
        if project_id:
            projects = [Project.query.get(project_id)]
            if not projects[0]:
                raise ValueError(f"项目不存在: {project_id}")
        else:
            projects = Project.query.filter_by(status='active').all()
        
        if not projects:
            return {
                'success': True,
                'message': '没有找到活跃的项目',
                'reports': []
            }
        
        self.update_state(state='PROGRESS', meta={
            'progress': 20, 
            'message': f'准备生成 {len(projects)} 个项目的日报'
        })
        
        # 初始化服务
        from app import create_app
        app = create_app()
        data_processor = DataProcessor()
        
        # 计算昨天的时间范围
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        start_time = datetime.combine(yesterday, datetime.min.time())
        end_time = datetime.combine(yesterday, datetime.max.time())
        
        daily_reports = []
        
        for i, project in enumerate(projects):
            try:
                self.update_state(state='PROGRESS', meta={
                    'progress': 20 + (i / len(projects)) * 60,
                    'message': f'生成项目 {project.name} 的日报'
                })
                
                # 收集昨天的数据
                executions = TestExecution.query.join(TestCase).filter(
                    TestCase.project_id == project.id,
                    TestExecution.created_at >= start_time,
                    TestExecution.created_at <= end_time
                ).all()
                
                bugs = Bug.query.filter(
                    Bug.project_id == project.id,
                    Bug.created_at >= start_time,
                    Bug.created_at <= end_time
                ).all()
                
                # 生成日报数据
                execution_metrics = data_processor.extract_execution_metrics(
                    [execution.to_dict() for execution in executions]
                )
                
                bug_metrics = data_processor.analyze_bug_patterns(
                    [bug.to_dict() for bug in bugs]
                )
                
                # 计算趋势（与前一天对比）
                prev_start = start_time - timedelta(days=1)
                prev_end = end_time - timedelta(days=1)
                
                prev_executions = TestExecution.query.join(TestCase).filter(
                    TestCase.project_id == project.id,
                    TestExecution.created_at >= prev_start,
                    TestExecution.created_at <= prev_end
                ).count()
                
                prev_bugs = Bug.query.filter(
                    Bug.project_id == project.id,
                    Bug.created_at >= prev_start,
                    Bug.created_at <= prev_end
                ).count()
                
                # 计算变化趋势
                execution_trend = len(executions) - prev_executions
                bug_trend = len(bugs) - prev_bugs
                
                daily_report = {
                    'project_id': project.id,
                    'project_name': project.name,
                    'date': yesterday.isoformat(),
                    'execution_metrics': execution_metrics,
                    'bug_metrics': bug_metrics,
                    'trends': {
                        'execution_change': execution_trend,
                        'bug_change': bug_trend
                    },
                    'summary': {
                        'total_executions': len(executions),
                        'total_bugs': len(bugs),
                        'pass_rate': execution_metrics.get('pass_rate', 0),
                        'critical_bugs': len([b for b in bugs if b.severity == 'critical'])
                    }
                }
                
                daily_reports.append(daily_report)
                
            except Exception as e:
                logger.error(f"生成项目 {project.name} 日报失败: {e}")
                daily_reports.append({
                    'project_id': project.id,
                    'project_name': project.name,
                    'date': yesterday.isoformat(),
                    'error': str(e)
                })
        
        self.update_state(state='PROGRESS', meta={
            'progress': 90, 
            'message': '保存日报数据'
        })
        
        # 保存日报（可以存储到数据库或文件）
        daily_report_summary = {
            'date': yesterday.isoformat(),
            'total_projects': len(projects),
            'successful_reports': len([r for r in daily_reports if 'error' not in r]),
            'failed_reports': len([r for r in daily_reports if 'error' in r]),
            'reports': daily_reports,
            'generated_at': datetime.now().isoformat()
        }
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '日报生成完成',
            'result': daily_report_summary
        })
        
        logger.info(f"日报生成任务完成: {self.request.id}, 成功: {daily_report_summary['successful_reports']}, 失败: {daily_report_summary['failed_reports']}")
        
        return {
            'success': True,
            'summary': daily_report_summary
        }
        
    except Exception as e:
        logger.error(f"日报生成任务失败: {e}")
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'日报生成失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def generate_weekly_report(self, project_id=None):
    """生成周报任务
    
    Args:
        project_id: 项目ID，如果为None则生成所有项目的周报
    
    Returns:
        周报生成结果
    """
    try:
        logger.info(f"开始生成周报任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '获取项目列表'})
        
        # 获取项目列表
        if project_id:
            projects = [Project.query.get(project_id)]
            if not projects[0]:
                raise ValueError(f"项目不存在: {project_id}")
        else:
            projects = Project.query.filter_by(status='active').all()
        
        if not projects:
            return {
                'success': True,
                'message': '没有找到活跃的项目',
                'reports': []
            }
        
        # 计算上周的时间范围
        today = datetime.now().date()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        
        start_time = datetime.combine(last_monday, datetime.min.time())
        end_time = datetime.combine(last_sunday, datetime.max.time())
        
        self.update_state(state='PROGRESS', meta={
            'progress': 20, 
            'message': f'生成 {len(projects)} 个项目的周报 ({last_monday} 至 {last_sunday})'
        })
        
        # 为每个项目生成周报
        weekly_reports = []
        
        for i, project in enumerate(projects):
            try:
                self.update_state(state='PROGRESS', meta={
                    'progress': 20 + (i / len(projects)) * 70,
                    'message': f'生成项目 {project.name} 的周报'
                })
                
                # 生成项目周报
                report_config = {
                    'type': 'comprehensive',
                    'time_range': 7,
                    'include_ai_analysis': True,
                    'start_date': start_time.isoformat(),
                    'end_date': end_time.isoformat()
                }
                
                # 调用报告生成任务
                report_result = generate_test_report.apply(
                    args=[project.id, report_config],
                    task_id=f"{self.request.id}_weekly_{project.id}"
                )
                
                # 等待报告生成完成
                result = report_result.get()
                
                weekly_reports.append({
                    'project_id': project.id,
                    'project_name': project.name,
                    'week_start': last_monday.isoformat(),
                    'week_end': last_sunday.isoformat(),
                    'report_id': result.get('report_id'),
                    'file_path': result.get('file_path'),
                    'summary': result.get('summary')
                })
                
            except Exception as e:
                logger.error(f"生成项目 {project.name} 周报失败: {e}")
                weekly_reports.append({
                    'project_id': project.id,
                    'project_name': project.name,
                    'week_start': last_monday.isoformat(),
                    'week_end': last_sunday.isoformat(),
                    'error': str(e)
                })
        
        self.update_state(state='PROGRESS', meta={
            'progress': 95, 
            'message': '整理周报汇总'
        })
        
        # 生成周报汇总
        weekly_summary = {
            'week_start': last_monday.isoformat(),
            'week_end': last_sunday.isoformat(),
            'total_projects': len(projects),
            'successful_reports': len([r for r in weekly_reports if 'error' not in r]),
            'failed_reports': len([r for r in weekly_reports if 'error' in r]),
            'reports': weekly_reports,
            'generated_at': datetime.now().isoformat()
        }
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '周报生成完成',
            'result': weekly_summary
        })
        
        logger.info(f"周报生成任务完成: {self.request.id}, 成功: {weekly_summary['successful_reports']}, 失败: {weekly_summary['failed_reports']}")
        
        return {
            'success': True,
            'summary': weekly_summary
        }
        
    except Exception as e:
        logger.error(f"周报生成任务失败: {e}")
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'周报生成失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def export_test_data(self, project_id, export_config=None):
    """导出测试数据任务
    
    Args:
        project_id: 项目ID
        export_config: 导出配置
    
    Returns:
        导出结果
    """
    try:
        logger.info(f"开始导出测试数据任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '获取项目信息'})
        
        # 获取项目
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        # 解析导出配置
        config = export_config or {}
        export_format = config.get('format', 'excel')  # excel, csv, json
        data_types = config.get('data_types', ['test_cases', 'executions', 'bugs'])  # 要导出的数据类型
        time_range = config.get('time_range', 30)  # 时间范围（天）
        
        self.update_state(state='PROGRESS', meta={'progress': 20, 'message': '收集导出数据'})
        
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_range)
        
        export_data = {}
        
        # 收集测试用例数据
        if 'test_cases' in data_types:
            test_cases = TestCase.query.filter_by(project_id=project_id).all()
            export_data['test_cases'] = [case.to_dict() for case in test_cases]
        
        # 收集执行记录数据
        if 'executions' in data_types:
            executions = TestExecution.query.join(TestCase).filter(
                TestCase.project_id == project_id,
                TestExecution.created_at >= start_date,
                TestExecution.created_at <= end_date
            ).all()
            export_data['executions'] = [execution.to_dict() for execution in executions]
        
        # 收集Bug数据
        if 'bugs' in data_types:
            bugs = Bug.query.filter(
                Bug.project_id == project_id,
                Bug.created_at >= start_date,
                Bug.created_at <= end_date
            ).all()
            export_data['bugs'] = [bug.to_dict() for bug in bugs]
        
        self.update_state(state='PROGRESS', meta={'progress': 60, 'message': f'生成{export_format.upper()}文件'})
        
        # 生成导出文件
        import os
        from app import create_app
        app = create_app()
        
        export_dir = app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{project.name}_export_{timestamp}"
        
        if export_format == 'excel':
            file_path = self._export_to_excel(export_data, export_dir, filename)
        elif export_format == 'csv':
            file_path = self._export_to_csv(export_data, export_dir, filename)
        elif export_format == 'json':
            file_path = self._export_to_json(export_data, export_dir, filename)
        else:
            raise ValueError(f"不支持的导出格式: {export_format}")
        
        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': '完成导出'})
        
        # 计算导出统计
        export_stats = {
            'total_test_cases': len(export_data.get('test_cases', [])),
            'total_executions': len(export_data.get('executions', [])),
            'total_bugs': len(export_data.get('bugs', [])),
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
        
        result = {
            'success': True,
            'project_id': project_id,
            'project_name': project.name,
            'export_format': export_format,
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'export_stats': export_stats,
            'time_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': time_range
            }
        }
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '数据导出完成',
            'result': result
        })
        
        logger.info(f"测试数据导出任务完成: {self.request.id}, 文件: {file_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"测试数据导出任务失败: {e}")
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'数据导出失败: {str(e)}',
            'error': str(e)
        })
        
        raise

    def _export_to_excel(self, data, export_dir, filename):
        """导出为Excel文件"""
        try:
            import pandas as pd
            
            file_path = os.path.join(export_dir, f"{filename}.xlsx")
            
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for sheet_name, sheet_data in data.items():
                    if sheet_data:
                        df = pd.DataFrame(sheet_data)
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            return file_path
        except Exception as e:
            logger.error(f"导出Excel文件失败: {e}")
            raise
    
    def _export_to_csv(self, data, export_dir, filename):
        """导出为CSV文件"""
        try:
            import pandas as pd
            import zipfile
            
            zip_path = os.path.join(export_dir, f"{filename}.zip")
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for sheet_name, sheet_data in data.items():
                    if sheet_data:
                        df = pd.DataFrame(sheet_data)
                        csv_content = df.to_csv(index=False)
                        zipf.writestr(f"{sheet_name}.csv", csv_content)
            
            return zip_path
        except Exception as e:
            logger.error(f"导出CSV文件失败: {e}")
            raise
    
    def _export_to_json(self, data, export_dir, filename):
        """导出为JSON文件"""
        try:
            file_path = os.path.join(export_dir, f"{filename}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            return file_path
        except Exception as e:
            logger.error(f"导出JSON文件失败: {e}")
            raise