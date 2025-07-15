#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试执行相关异步任务
"""

import json
from datetime import datetime
from loguru import logger
from celery import current_task
from app.tasks import celery
from app.models import db, TestCase, TestExecution, Project
from app.services.test_executor import TestExecutor

@celery.task(bind=True)
def execute_single_test_case(self, test_case_id, execution_config=None):
    """执行单个测试用例任务
    
    Args:
        test_case_id: 测试用例ID
        execution_config: 执行配置
    
    Returns:
        执行结果
    """
    try:
        logger.info(f"开始执行测试用例任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '获取测试用例'})
        
        # 获取测试用例
        test_case = TestCase.query.get(test_case_id)
        if not test_case:
            raise ValueError(f"测试用例不存在: {test_case_id}")
        
        # 创建执行记录
        execution = TestExecution(
            test_case_id=test_case_id,
            status='running',
            result='pending',
            task_id=self.request.id
        )
        db.session.add(execution)
        db.session.commit()
        
        self.update_state(state='PROGRESS', meta={
            'progress': 20, 
            'message': '初始化测试执行器',
            'execution_id': execution.id
        })
        
        # 初始化测试执行器
        from app import create_app
        app = create_app()
        config = app.config
        
        test_executor = TestExecutor(config)
        
        self.update_state(state='PROGRESS', meta={
            'progress': 30, 
            'message': '开始执行测试',
            'execution_id': execution.id
        })
        
        # 定义进度回调
        def progress_callback(test_case_obj, partial_result):
            progress = partial_result.get('progress', 50)
            message = partial_result.get('message', '执行中...')
            self.update_state(state='PROGRESS', meta={
                'progress': min(progress, 90),
                'message': message,
                'execution_id': execution.id
            })
        
        # 执行测试用例
        result = test_executor.execute_test_case(
            test_case, 
            execution.id, 
            callback=progress_callback
        )
        
        self.update_state(state='PROGRESS', meta={
            'progress': 95, 
            'message': '保存执行结果',
            'execution_id': execution.id
        })
        
        # 更新执行记录
        execution.status = 'completed'
        execution.result = result.get('result', 'failed')
        execution.execution_time = result.get('execution_time', 0)
        execution.error_message = result.get('message', '')
        execution.execution_details = json.dumps(result.get('details', {}), ensure_ascii=False)
        execution.completed_at = datetime.now()
        
        # 保存AI分析结果
        if result.get('ai_analysis'):
            execution.ai_analysis_result = json.dumps(result['ai_analysis'], ensure_ascii=False)
        
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '测试执行完成',
            'execution_id': execution.id,
            'result': {
                'execution_id': execution.id,
                'test_case_id': test_case_id,
                'result': result.get('result'),
                'execution_time': result.get('execution_time'),
                'message': result.get('message')
            }
        })
        
        logger.info(f"测试用例执行任务完成: {self.request.id}, 结果: {result.get('result')}")
        
        return {
            'success': True,
            'execution_id': execution.id,
            'test_case_id': test_case_id,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"测试用例执行任务失败: {e}")
        
        # 更新执行记录状态
        try:
            execution = TestExecution.query.filter_by(task_id=self.request.id).first()
            if execution:
                execution.status = 'failed'
                execution.result = 'error'
                execution.error_message = str(e)
                execution.completed_at = datetime.now()
                db.session.commit()
        except:
            pass
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'执行失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def execute_test_cases_batch(self, test_case_ids, execution_config=None):
    """批量执行测试用例任务
    
    Args:
        test_case_ids: 测试用例ID列表
        execution_config: 执行配置
    
    Returns:
        批量执行结果
    """
    try:
        logger.info(f"开始批量执行测试用例任务: {self.request.id}, 共 {len(test_case_ids)} 个用例")
        
        self.update_state(state='PROGRESS', meta={
            'progress': 5, 
            'message': f'准备执行 {len(test_case_ids)} 个测试用例'
        })
        
        # 获取测试用例
        test_cases = TestCase.query.filter(TestCase.id.in_(test_case_ids)).all()
        if len(test_cases) != len(test_case_ids):
            missing_ids = set(test_case_ids) - {case.id for case in test_cases}
            logger.warning(f"部分测试用例不存在: {missing_ids}")
        
        self.update_state(state='PROGRESS', meta={
            'progress': 10, 
            'message': '初始化测试执行器'
        })
        
        # 初始化测试执行器
        from app import create_app
        app = create_app()
        config = app.config
        
        test_executor = TestExecutor(config)
        
        # 解析执行配置
        config = execution_config or {}
        parallel = config.get('parallel', False)
        max_workers = config.get('max_workers', 3)
        
        self.update_state(state='PROGRESS', meta={
            'progress': 15, 
            'message': f'开始批量执行 ({"并行" if parallel else "串行"})'
        })
        
        # 创建执行记录
        executions = []
        for test_case in test_cases:
            execution = TestExecution(
                test_case_id=test_case.id,
                status='pending',
                result='pending',
                task_id=self.request.id
            )
            db.session.add(execution)
            executions.append(execution)
        
        db.session.commit()
        
        # 定义进度回调
        completed_count = 0
        total_count = len(test_cases)
        
        def progress_callback(test_case_obj, result):
            nonlocal completed_count
            completed_count += 1
            progress = 15 + (completed_count / total_count) * 80
            self.update_state(state='PROGRESS', meta={
                'progress': int(progress),
                'message': f'已完成 {completed_count}/{total_count} 个测试用例',
                'completed': completed_count,
                'total': total_count
            })
        
        # 执行测试用例
        if parallel:
            # 并行执行
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading
            
            results = []
            lock = threading.Lock()
            
            def execute_with_callback(test_case, execution):
                try:
                    result = test_executor.execute_test_case(test_case, execution.id)
                    with lock:
                        progress_callback(test_case, result)
                    return {
                        'test_case_id': test_case.id,
                        'execution_id': execution.id,
                        'result': result
                    }
                except Exception as e:
                    logger.error(f"执行测试用例 {test_case.id} 失败: {e}")
                    with lock:
                        progress_callback(test_case, {'result': 'error', 'message': str(e)})
                    return {
                        'test_case_id': test_case.id,
                        'execution_id': execution.id,
                        'result': {'result': 'error', 'message': str(e)}
                    }
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_case = {
                    executor.submit(execute_with_callback, test_case, execution): (test_case, execution)
                    for test_case, execution in zip(test_cases, executions)
                }
                
                for future in as_completed(future_to_case):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        test_case, execution = future_to_case[future]
                        logger.error(f"获取执行结果失败: {e}")
                        results.append({
                            'test_case_id': test_case.id,
                            'execution_id': execution.id,
                            'result': {'result': 'error', 'message': str(e)}
                        })
        else:
            # 串行执行
            results = []
            for i, (test_case, execution) in enumerate(zip(test_cases, executions)):
                try:
                    result = test_executor.execute_test_case(test_case, execution.id)
                    progress_callback(test_case, result)
                    results.append({
                        'test_case_id': test_case.id,
                        'execution_id': execution.id,
                        'result': result
                    })
                except Exception as e:
                    logger.error(f"执行测试用例 {test_case.id} 失败: {e}")
                    progress_callback(test_case, {'result': 'error', 'message': str(e)})
                    results.append({
                        'test_case_id': test_case.id,
                        'execution_id': execution.id,
                        'result': {'result': 'error', 'message': str(e)}
                    })
        
        self.update_state(state='PROGRESS', meta={
            'progress': 95, 
            'message': '整理执行结果'
        })
        
        # 统计结果
        passed_count = len([r for r in results if r['result'].get('result') == 'passed'])
        failed_count = len([r for r in results if r['result'].get('result') == 'failed'])
        error_count = len([r for r in results if r['result'].get('result') == 'error'])
        skipped_count = len([r for r in results if r['result'].get('result') == 'skipped'])
        
        summary = {
            'total': len(results),
            'passed': passed_count,
            'failed': failed_count,
            'error': error_count,
            'skipped': skipped_count,
            'pass_rate': round((passed_count / len(results)) * 100, 2) if results else 0
        }
        
        final_result = {
            'success': True,
            'summary': summary,
            'results': results,
            'execution_config': execution_config
        }
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '批量执行完成',
            'summary': summary,
            'result': final_result
        })
        
        logger.info(f"批量执行测试用例任务完成: {self.request.id}, 通过率: {summary['pass_rate']}%")
        
        return final_result
        
    except Exception as e:
        logger.error(f"批量执行测试用例任务失败: {e}")
        
        # 更新相关执行记录状态
        try:
            executions = TestExecution.query.filter_by(task_id=self.request.id).all()
            for execution in executions:
                if execution.status in ['pending', 'running']:
                    execution.status = 'failed'
                    execution.result = 'error'
                    execution.error_message = str(e)
                    execution.completed_at = datetime.now()
            db.session.commit()
        except:
            pass
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'批量执行失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def execute_project_test_suite(self, project_id, execution_config=None):
    """执行项目测试套件任务
    
    Args:
        project_id: 项目ID
        execution_config: 执行配置
    
    Returns:
        项目测试执行结果
    """
    try:
        logger.info(f"开始执行项目测试套件任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={
            'progress': 5, 
            'message': '获取项目信息'
        })
        
        # 获取项目
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        # 获取项目下的所有测试用例
        config = execution_config or {}
        filters = config.get('filters', {})
        
        query = TestCase.query.filter_by(project_id=project_id)
        
        # 应用过滤条件
        if filters.get('module_ids'):
            query = query.filter(TestCase.module_id.in_(filters['module_ids']))
        
        if filters.get('test_types'):
            query = query.filter(TestCase.test_type.in_(filters['test_types']))
        
        if filters.get('priorities'):
            query = query.filter(TestCase.priority.in_(filters['priorities']))
        
        if filters.get('status'):
            query = query.filter_by(status=filters['status'])
        
        test_cases = query.all()
        
        if not test_cases:
            return {
                'success': True,
                'message': '没有找到符合条件的测试用例',
                'summary': {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'error': 0,
                    'skipped': 0,
                    'pass_rate': 0
                },
                'results': []
            }
        
        self.update_state(state='PROGRESS', meta={
            'progress': 10, 
            'message': f'找到 {len(test_cases)} 个测试用例'
        })
        
        # 根据优先级排序（如果启用了智能排序）
        if config.get('smart_ordering', False):
            # AI风险优先级排序
            try:
                from app.services.ai_service import AIService
                from app import create_app
                app = create_app()
                ai_service = AIService(app.config.get('AI', {}))
                
                # 获取风险评估结果
                risk_assessment = ai_service.assess_project_risk({
                    'project': project.to_dict(),
                    'test_cases': [case.to_dict() for case in test_cases]
                })
                
                if risk_assessment.get('success') and risk_assessment.get('high_risk_cases'):
                    high_risk_ids = {case['id'] for case in risk_assessment['high_risk_cases']}
                    # 高风险用例优先执行
                    test_cases.sort(key=lambda x: (x.id not in high_risk_ids, x.priority))
                    
                    self.update_state(state='PROGRESS', meta={
                        'progress': 15, 
                        'message': f'应用AI智能排序，{len(high_risk_ids)} 个高风险用例优先执行'
                    })
            except Exception as e:
                logger.warning(f"AI智能排序失败，使用默认排序: {e}")
        
        # 调用批量执行任务
        test_case_ids = [case.id for case in test_cases]
        
        # 更新执行配置
        batch_config = config.copy()
        batch_config.update({
            'parallel': config.get('parallel', True),
            'max_workers': config.get('max_workers', 5)
        })
        
        # 执行批量测试
        result = execute_test_cases_batch.apply(
            args=[test_case_ids, batch_config],
            task_id=f"{self.request.id}_batch"
        )
        
        # 等待批量执行完成
        batch_result = result.get()
        
        # 添加项目信息到结果
        final_result = batch_result.copy()
        final_result.update({
            'project_id': project_id,
            'project_name': project.name,
            'execution_config': execution_config,
            'total_test_cases': len(test_cases)
        })
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '项目测试套件执行完成',
            'result': final_result
        })
        
        logger.info(f"项目测试套件执行任务完成: {self.request.id}, 项目: {project.name}")
        
        return final_result
        
    except Exception as e:
        logger.error(f"项目测试套件执行任务失败: {e}")
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'项目测试执行失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def schedule_regression_test(self, project_id, trigger_type='manual', trigger_data=None):
    """调度回归测试任务
    
    Args:
        project_id: 项目ID
        trigger_type: 触发类型 (manual, code_change, schedule)
        trigger_data: 触发数据
    
    Returns:
        回归测试结果
    """
    try:
        logger.info(f"开始调度回归测试任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={
            'progress': 10, 
            'message': '分析回归测试范围'
        })
        
        # 获取项目
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        # 根据触发类型确定测试范围
        execution_config = {
            'parallel': True,
            'max_workers': 3,
            'smart_ordering': True
        }
        
        if trigger_type == 'code_change':
            # 代码变更触发：执行相关模块的测试用例
            changed_modules = trigger_data.get('changed_modules', []) if trigger_data else []
            if changed_modules:
                execution_config['filters'] = {
                    'module_ids': changed_modules,
                    'priorities': ['high', 'medium']  # 只执行高中优先级
                }
        elif trigger_type == 'schedule':
            # 定时触发：执行所有自动化测试用例
            execution_config['filters'] = {
                'status': 'active'  # 只执行激活状态的用例
            }
        else:
            # 手动触发：根据配置执行
            if trigger_data and trigger_data.get('filters'):
                execution_config['filters'] = trigger_data['filters']
        
        self.update_state(state='PROGRESS', meta={
            'progress': 20, 
            'message': '开始执行回归测试'
        })
        
        # 执行项目测试套件
        result = execute_project_test_suite.apply(
            args=[project_id, execution_config],
            task_id=f"{self.request.id}_regression"
        )
        
        # 等待执行完成
        regression_result = result.get()
        
        # 分析回归测试结果
        summary = regression_result.get('summary', {})
        pass_rate = summary.get('pass_rate', 0)
        
        # 判断回归测试是否通过
        regression_passed = pass_rate >= 90  # 90%通过率阈值
        
        final_result = regression_result.copy()
        final_result.update({
            'trigger_type': trigger_type,
            'trigger_data': trigger_data,
            'regression_passed': regression_passed,
            'regression_threshold': 90
        })
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': f'回归测试完成 - {"通过" if regression_passed else "失败"}',
            'result': final_result
        })
        
        logger.info(f"回归测试任务完成: {self.request.id}, 通过率: {pass_rate}%, 结果: {"通过" if regression_passed else "失败"}")
        
        return final_result
        
    except Exception as e:
        logger.error(f"回归测试任务失败: {e}")
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'回归测试失败: {str(e)}',
            'error': str(e)
        })
        
        raise