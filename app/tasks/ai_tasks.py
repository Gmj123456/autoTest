#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI相关异步任务
"""

import json
from datetime import datetime
from loguru import logger
from celery import current_task
from app.tasks import celery
from app.models import db, TestCase, TestExecution, Bug, AITask
from app.services.ai_service import AIService
from app.utils.text_similarity import find_similar_texts

@celery.task(bind=True)
def ai_generate_test_cases(self, project_id, module_id, requirements, config=None):
    """AI生成测试用例任务
    
    Args:
        project_id: 项目ID
        module_id: 模块ID
        requirements: 需求描述
        config: 生成配置
    
    Returns:
        生成结果
    """
    try:
        logger.info(f"开始AI生成测试用例任务: {self.request.id}")
        
        # 更新任务状态
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '初始化AI服务'})
        
        # 创建AI任务记录
        ai_task = AITask(
            task_id=self.request.id,
            task_type='generate_test_cases',
            status='running',
            input_data=json.dumps({
                'project_id': project_id,
                'module_id': module_id,
                'requirements': requirements,
                'config': config
            }, ensure_ascii=False)
        )
        db.session.add(ai_task)
        db.session.commit()
        
        # 初始化AI服务
        from app import create_app
        app = create_app()
        ai_service = AIService(app.config.get('AI', {}))
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': '分析需求'})
        
        # 生成测试用例
        result = ai_service.generate_test_cases(
            requirements=requirements,
            project_id=project_id,
            module_id=module_id,
            config=config or {}
        )
        
        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': '保存测试用例'})
        
        # 保存生成的测试用例
        created_cases = []
        if result.get('success') and result.get('test_cases'):
            for case_data in result['test_cases']:
                try:
                    test_case = TestCase(
                        title=case_data.get('title', ''),
                        description=case_data.get('description', ''),
                        test_steps=json.dumps(case_data.get('test_steps', []), ensure_ascii=False),
                        expected_result=case_data.get('expected_result', ''),
                        test_type=case_data.get('test_type', 'functional'),
                        priority=case_data.get('priority', 'medium'),
                        project_id=project_id,
                        module_id=module_id,
                        ai_generated=True,
                        ai_confidence=case_data.get('confidence', 0.8)
                    )
                    db.session.add(test_case)
                    db.session.flush()
                    created_cases.append({
                        'id': test_case.id,
                        'title': test_case.title,
                        'confidence': case_data.get('confidence', 0.8)
                    })
                except Exception as e:
                    logger.error(f"保存测试用例失败: {e}")
            
            db.session.commit()
        
        # 更新AI任务结果
        ai_task.status = 'completed'
        ai_task.result = json.dumps({
            'success': result.get('success', False),
            'message': result.get('message', ''),
            'created_cases': created_cases,
            'total_generated': len(created_cases)
        }, ensure_ascii=False)
        ai_task.completed_at = datetime.now()
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '测试用例生成完成',
            'result': {
                'success': True,
                'created_cases': created_cases,
                'total_generated': len(created_cases)
            }
        })
        
        logger.info(f"AI生成测试用例任务完成: {self.request.id}, 生成 {len(created_cases)} 个用例")
        
        return {
            'success': True,
            'created_cases': created_cases,
            'total_generated': len(created_cases)
        }
        
    except Exception as e:
        logger.error(f"AI生成测试用例任务失败: {e}")
        
        # 更新AI任务状态
        try:
            ai_task = AITask.query.filter_by(task_id=self.request.id).first()
            if ai_task:
                ai_task.status = 'failed'
                ai_task.error_message = str(e)
                ai_task.completed_at = datetime.now()
                db.session.commit()
        except:
            pass
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'生成失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def ai_enhance_test_case(self, test_case_id, enhancement_type='all'):
    """AI增强测试用例任务
    
    Args:
        test_case_id: 测试用例ID
        enhancement_type: 增强类型 (steps, assertions, data, all)
    
    Returns:
        增强结果
    """
    try:
        logger.info(f"开始AI增强测试用例任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '获取测试用例'})
        
        # 获取测试用例
        test_case = TestCase.query.get(test_case_id)
        if not test_case:
            raise ValueError(f"测试用例不存在: {test_case_id}")
        
        # 创建AI任务记录
        ai_task = AITask(
            task_id=self.request.id,
            task_type='enhance_test_case',
            status='running',
            input_data=json.dumps({
                'test_case_id': test_case_id,
                'enhancement_type': enhancement_type
            }, ensure_ascii=False)
        )
        db.session.add(ai_task)
        db.session.commit()
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': '初始化AI服务'})
        
        # 初始化AI服务
        from app import create_app
        app = create_app()
        ai_service = AIService(app.config.get('AI', {}))
        
        self.update_state(state='PROGRESS', meta={'progress': 50, 'message': '分析测试用例'})
        
        # AI增强测试用例
        result = ai_service.enhance_test_case(
            test_case.to_dict(),
            enhancement_type=enhancement_type
        )
        
        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': '更新测试用例'})
        
        # 更新测试用例
        if result.get('success') and result.get('enhanced_case'):
            enhanced_case = result['enhanced_case']
            
            # 备份原始数据
            original_data = {
                'test_steps': test_case.test_steps,
                'expected_result': test_case.expected_result,
                'test_data': test_case.test_data
            }
            
            # 更新字段
            if 'test_steps' in enhanced_case:
                test_case.test_steps = json.dumps(enhanced_case['test_steps'], ensure_ascii=False)
            if 'expected_result' in enhanced_case:
                test_case.expected_result = enhanced_case['expected_result']
            if 'test_data' in enhanced_case:
                test_case.test_data = json.dumps(enhanced_case['test_data'], ensure_ascii=False)
            
            test_case.ai_enhanced = True
            test_case.ai_enhancement_history = json.dumps({
                'enhanced_at': datetime.now().isoformat(),
                'enhancement_type': enhancement_type,
                'original_data': original_data,
                'ai_suggestions': result.get('suggestions', [])
            }, ensure_ascii=False)
            
            db.session.commit()
        
        # 更新AI任务结果
        ai_task.status = 'completed'
        ai_task.result = json.dumps(result, ensure_ascii=False)
        ai_task.completed_at = datetime.now()
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '测试用例增强完成',
            'result': result
        })
        
        logger.info(f"AI增强测试用例任务完成: {self.request.id}")
        
        return result
        
    except Exception as e:
        logger.error(f"AI增强测试用例任务失败: {e}")
        
        # 更新AI任务状态
        try:
            ai_task = AITask.query.filter_by(task_id=self.request.id).first()
            if ai_task:
                ai_task.status = 'failed'
                ai_task.error_message = str(e)
                ai_task.completed_at = datetime.now()
                db.session.commit()
        except:
            pass
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'增强失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def ai_analyze_execution_result(self, execution_id):
    """AI分析测试执行结果任务
    
    Args:
        execution_id: 执行记录ID
    
    Returns:
        分析结果
    """
    try:
        logger.info(f"开始AI分析执行结果任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '获取执行记录'})
        
        # 获取执行记录
        execution = TestExecution.query.get(execution_id)
        if not execution:
            raise ValueError(f"执行记录不存在: {execution_id}")
        
        # 创建AI任务记录
        ai_task = AITask(
            task_id=self.request.id,
            task_type='analyze_execution',
            status='running',
            input_data=json.dumps({
                'execution_id': execution_id
            }, ensure_ascii=False)
        )
        db.session.add(ai_task)
        db.session.commit()
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': '初始化AI服务'})
        
        # 初始化AI服务
        from app import create_app
        app = create_app()
        ai_service = AIService(app.config.get('AI', {}))
        
        self.update_state(state='PROGRESS', meta={'progress': 50, 'message': '分析执行结果'})
        
        # 获取测试用例信息
        test_case = execution.test_case
        if not test_case:
            raise ValueError("关联的测试用例不存在")
        
        # AI分析执行结果
        result = ai_service.analyze_execution_result(
            test_case.to_dict(),
            {
                'result': execution.result,
                'execution_time': execution.execution_time,
                'error_message': execution.error_message,
                'execution_details': execution.execution_details
            }
        )
        
        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': '保存分析结果'})
        
        # 更新执行记录的AI分析结果
        if result.get('success'):
            execution.ai_analysis_result = json.dumps(result, ensure_ascii=False)
            db.session.commit()
        
        # 更新AI任务结果
        ai_task.status = 'completed'
        ai_task.result = json.dumps(result, ensure_ascii=False)
        ai_task.completed_at = datetime.now()
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '执行结果分析完成',
            'result': result
        })
        
        logger.info(f"AI分析执行结果任务完成: {self.request.id}")
        
        return result
        
    except Exception as e:
        logger.error(f"AI分析执行结果任务失败: {e}")
        
        # 更新AI任务状态
        try:
            ai_task = AITask.query.filter_by(task_id=self.request.id).first()
            if ai_task:
                ai_task.status = 'failed'
                ai_task.error_message = str(e)
                ai_task.completed_at = datetime.now()
                db.session.commit()
        except:
            pass
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'分析失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def ai_analyze_bug_root_cause(self, bug_id):
    """AI分析Bug根因任务
    
    Args:
        bug_id: Bug ID
    
    Returns:
        分析结果
    """
    try:
        logger.info(f"开始AI分析Bug根因任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '获取Bug信息'})
        
        # 获取Bug
        bug = Bug.query.get(bug_id)
        if not bug:
            raise ValueError(f"Bug不存在: {bug_id}")
        
        # 创建AI任务记录
        ai_task = AITask(
            task_id=self.request.id,
            task_type='analyze_bug_root_cause',
            status='running',
            input_data=json.dumps({
                'bug_id': bug_id
            }, ensure_ascii=False)
        )
        db.session.add(ai_task)
        db.session.commit()
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': '初始化AI服务'})
        
        # 初始化AI服务
        from app import create_app
        app = create_app()
        ai_service = AIService(app.config.get('AI', {}))
        
        self.update_state(state='PROGRESS', meta={'progress': 50, 'message': '分析Bug根因'})
        
        # AI分析Bug根因
        result = ai_service.analyze_bug_root_cause(bug.to_dict())
        
        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': '保存分析结果'})
        
        # 更新Bug的AI分析结果
        if result.get('success'):
            bug.ai_root_cause_analysis = json.dumps(result, ensure_ascii=False)
            db.session.commit()
        
        # 更新AI任务结果
        ai_task.status = 'completed'
        ai_task.result = json.dumps(result, ensure_ascii=False)
        ai_task.completed_at = datetime.now()
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': 'Bug根因分析完成',
            'result': result
        })
        
        logger.info(f"AI分析Bug根因任务完成: {self.request.id}")
        
        return result
        
    except Exception as e:
        logger.error(f"AI分析Bug根因任务失败: {e}")
        
        # 更新AI任务状态
        try:
            ai_task = AITask.query.filter_by(task_id=self.request.id).first()
            if ai_task:
                ai_task.status = 'failed'
                ai_task.error_message = str(e)
                ai_task.completed_at = datetime.now()
                db.session.commit()
        except:
            pass
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'分析失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def ai_find_similar_bugs(self, bug_id, similarity_threshold=0.7):
    """AI查找相似Bug任务
    
    Args:
        bug_id: Bug ID
        similarity_threshold: 相似度阈值
    
    Returns:
        相似Bug列表
    """
    try:
        logger.info(f"开始AI查找相似Bug任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '获取Bug信息'})
        
        # 获取Bug
        bug = Bug.query.get(bug_id)
        if not bug:
            raise ValueError(f"Bug不存在: {bug_id}")
        
        # 创建AI任务记录
        ai_task = AITask(
            task_id=self.request.id,
            task_type='find_similar_bugs',
            status='running',
            input_data=json.dumps({
                'bug_id': bug_id,
                'similarity_threshold': similarity_threshold
            }, ensure_ascii=False)
        )
        db.session.add(ai_task)
        db.session.commit()
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': '获取所有Bug'})
        
        # 获取所有其他Bug
        all_bugs = Bug.query.filter(Bug.id != bug_id).all()
        
        self.update_state(state='PROGRESS', meta={'progress': 50, 'message': '计算相似度'})
        
        # 准备文本数据
        target_text = f"{bug.title} {bug.description}"
        bug_texts = []
        bug_data = []
        
        for other_bug in all_bugs:
            bug_text = f"{other_bug.title} {other_bug.description}"
            bug_texts.append(bug_text)
            bug_data.append({
                'id': other_bug.id,
                'title': other_bug.title,
                'description': other_bug.description,
                'severity': other_bug.severity,
                'status': other_bug.status,
                'created_at': other_bug.created_at.isoformat() if other_bug.created_at else None
            })
        
        # 查找相似文本
        similar_results = find_similar_texts(
            target_text, 
            bug_texts, 
            threshold=similarity_threshold,
            top_k=10
        )
        
        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': '整理结果'})
        
        # 整理相似Bug结果
        similar_bugs = []
        for idx, similarity in similar_results:
            if idx < len(bug_data):
                similar_bug = bug_data[idx].copy()
                similar_bug['similarity'] = round(similarity, 3)
                similar_bugs.append(similar_bug)
        
        # 保存相似Bug到原Bug记录
        if similar_bugs:
            bug.ai_similar_bugs = json.dumps(similar_bugs, ensure_ascii=False)
            db.session.commit()
        
        result = {
            'success': True,
            'similar_bugs': similar_bugs,
            'total_found': len(similar_bugs),
            'similarity_threshold': similarity_threshold
        }
        
        # 更新AI任务结果
        ai_task.status = 'completed'
        ai_task.result = json.dumps(result, ensure_ascii=False)
        ai_task.completed_at = datetime.now()
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '相似Bug查找完成',
            'result': result
        })
        
        logger.info(f"AI查找相似Bug任务完成: {self.request.id}, 找到 {len(similar_bugs)} 个相似Bug")
        
        return result
        
    except Exception as e:
        logger.error(f"AI查找相似Bug任务失败: {e}")
        
        # 更新AI任务状态
        try:
            ai_task = AITask.query.filter_by(task_id=self.request.id).first()
            if ai_task:
                ai_task.status = 'failed'
                ai_task.error_message = str(e)
                ai_task.completed_at = datetime.now()
                db.session.commit()
        except:
            pass
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'查找失败: {str(e)}',
            'error': str(e)
        })
        
        raise

@celery.task(bind=True)
def ai_project_risk_assessment(self, project_id):
    """AI项目风险评估任务
    
    Args:
        project_id: 项目ID
    
    Returns:
        风险评估结果
    """
    try:
        logger.info(f"开始AI项目风险评估任务: {self.request.id}")
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': '收集项目数据'})
        
        # 创建AI任务记录
        ai_task = AITask(
            task_id=self.request.id,
            task_type='project_risk_assessment',
            status='running',
            input_data=json.dumps({
                'project_id': project_id
            }, ensure_ascii=False)
        )
        db.session.add(ai_task)
        db.session.commit()
        
        # 收集项目相关数据
        from app.models import Project, Module
        
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        
        # 获取项目的测试用例、执行记录、Bug等数据
        test_cases = TestCase.query.filter_by(project_id=project_id).all()
        executions = TestExecution.query.join(TestCase).filter(TestCase.project_id == project_id).all()
        bugs = Bug.query.filter_by(project_id=project_id).all()
        modules = Module.query.filter_by(project_id=project_id).all()
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': '初始化AI服务'})
        
        # 初始化AI服务
        from app import create_app
        app = create_app()
        ai_service = AIService(app.config.get('AI', {}))
        
        self.update_state(state='PROGRESS', meta={'progress': 50, 'message': '进行风险评估'})
        
        # 准备项目数据
        project_data = {
            'project': project.to_dict(),
            'modules': [module.to_dict() for module in modules],
            'test_cases': [case.to_dict() for case in test_cases],
            'executions': [execution.to_dict() for execution in executions],
            'bugs': [bug.to_dict() for bug in bugs]
        }
        
        # AI风险评估
        result = ai_service.assess_project_risk(project_data)
        
        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': '保存评估结果'})
        
        # 更新AI任务结果
        ai_task.status = 'completed'
        ai_task.result = json.dumps(result, ensure_ascii=False)
        ai_task.completed_at = datetime.now()
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'message': '项目风险评估完成',
            'result': result
        })
        
        logger.info(f"AI项目风险评估任务完成: {self.request.id}")
        
        return result
        
    except Exception as e:
        logger.error(f"AI项目风险评估任务失败: {e}")
        
        # 更新AI任务状态
        try:
            ai_task = AITask.query.filter_by(task_id=self.request.id).first()
            if ai_task:
                ai_task.status = 'failed'
                ai_task.error_message = str(e)
                ai_task.completed_at = datetime.now()
                db.session.commit()
        except:
            pass
        
        self.update_state(state='FAILURE', meta={
            'progress': 0,
            'message': f'评估失败: {str(e)}',
            'error': str(e)
        })
        
        raise