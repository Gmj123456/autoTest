#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI服务模块
提供AI增强功能，包括测试用例生成、智能分析、Bug根因分析等
"""

import openai
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from flask import current_app
from app.models import db, Project, Module, TestCase, TestExecution, Bug, TestReport, AITask
from app.utils.text_similarity import calculate_similarity
from app.utils.data_processor import DataProcessor
import asyncio
import threading

class AIService:
    """AI服务类"""
    
    def __init__(self):
        self.openai_client = None
        self.data_processor = DataProcessor()
        self._init_openai()
    
    def _init_openai(self):
        """初始化OpenAI客户端"""
        try:
            api_key = current_app.config.get('AI_OPENAI_API_KEY')
            api_base = current_app.config.get('AI_OPENAI_API_BASE')
            
            if api_key:
                openai.api_key = api_key
                if api_base:
                    openai.api_base = api_base
                
                self.openai_client = openai
                logger.info("OpenAI客户端初始化成功")
            else:
                logger.warning("未配置OpenAI API密钥")
        except Exception as e:
            logger.error(f"OpenAI客户端初始化失败: {e}")
    
    def generate_test_cases(self, project_id: int, module_id: Optional[int], 
                          requirement: str, test_type: str = 'functional',
                          priority: str = 'medium', count: int = 5) -> Dict[str, Any]:
        """AI生成测试用例"""
        try:
            # 创建AI任务
            task = AITask(
                task_type='generate_testcase',
                status='pending',
                parameters=json.dumps({
                    'project_id': project_id,
                    'module_id': module_id,
                    'requirement': requirement,
                    'test_type': test_type,
                    'priority': priority,
                    'count': count
                })
            )
            task.save()
            
            # 异步执行生成任务
            threading.Thread(
                target=self._generate_test_cases_async,
                args=(task.id, project_id, module_id, requirement, test_type, priority, count)
            ).start()
            
            return {
                'success': True,
                'task_id': task.id,
                'message': '测试用例生成任务已启动'
            }
            
        except Exception as e:
            logger.error(f"生成测试用例失败: {e}")
            return {
                'success': False,
                'message': f'生成测试用例失败: {str(e)}'
            }
    
    def _generate_test_cases_async(self, task_id: int, project_id: int, 
                                 module_id: Optional[int], requirement: str,
                                 test_type: str, priority: str, count: int):
        """异步生成测试用例"""
        try:
            task = AITask.query.get(task_id)
            if not task:
                return
            
            task.status = 'running'
            task.progress = 10
            task.save()
            
            # 获取项目和模块信息
            project = Project.query.get(project_id)
            module = Module.query.get(module_id) if module_id else None
            
            # 构建上下文信息
            context = self._build_project_context(project, module)
            
            task.progress = 30
            task.save()
            
            # 调用AI生成测试用例
            if self.openai_client:
                test_cases = self._call_openai_generate_testcases(
                    context, requirement, test_type, priority, count
                )
            else:
                # 使用模板生成（备用方案）
                test_cases = self._generate_testcases_by_template(
                    requirement, test_type, priority, count
                )
            
            task.progress = 80
            task.save()
            
            # 保存生成的测试用例
            saved_cases = []
            for case_data in test_cases:
                test_case = TestCase(
                    title=case_data['title'],
                    description=case_data['description'],
                    steps=json.dumps(case_data['steps']),
                    expected_result=case_data['expected_result'],
                    project_id=project_id,
                    module_id=module_id,
                    test_type=test_type,
                    priority=priority,
                    ai_generated=True,
                    ai_confidence_score=case_data.get('confidence', 0.8)
                )
                test_case.save()
                saved_cases.append(test_case.to_dict())
            
            # 更新任务状态
            task.status = 'completed'
            task.progress = 100
            task.result = json.dumps({
                'test_cases': saved_cases,
                'count': len(saved_cases)
            })
            task.save()
            
            logger.info(f"AI生成测试用例完成: 任务ID {task_id}, 生成 {len(saved_cases)} 个用例")
            
        except Exception as e:
            logger.error(f"异步生成测试用例失败: {e}")
            task = AITask.query.get(task_id)
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                task.save()
    
    def enhance_test_case(self, testcase: TestCase, enhancement_type: str = 'steps',
                         context: str = '') -> Dict[str, Any]:
        """AI增强测试用例"""
        try:
            # 创建AI任务
            task = AITask(
                task_type='enhance_testcase',
                status='pending',
                parameters=json.dumps({
                    'testcase_id': testcase.id,
                    'enhancement_type': enhancement_type,
                    'context': context
                })
            )
            task.save()
            
            # 异步执行增强任务
            threading.Thread(
                target=self._enhance_test_case_async,
                args=(task.id, testcase.id, enhancement_type, context)
            ).start()
            
            return {
                'success': True,
                'task_id': task.id,
                'message': '测试用例增强任务已启动'
            }
            
        except Exception as e:
            logger.error(f"增强测试用例失败: {e}")
            return {
                'success': False,
                'message': f'增强测试用例失败: {str(e)}'
            }
    
    def _enhance_test_case_async(self, task_id: int, testcase_id: int,
                               enhancement_type: str, context: str):
        """异步增强测试用例"""
        try:
            task = AITask.query.get(task_id)
            testcase = TestCase.query.get(testcase_id)
            
            if not task or not testcase:
                return
            
            task.status = 'running'
            task.progress = 20
            task.save()
            
            # 调用AI增强测试用例
            if self.openai_client:
                enhanced_content = self._call_openai_enhance_testcase(
                    testcase, enhancement_type, context
                )
            else:
                # 使用规则增强（备用方案）
                enhanced_content = self._enhance_testcase_by_rules(
                    testcase, enhancement_type
                )
            
            task.progress = 80
            task.save()
            
            # 更新测试用例
            if enhancement_type == 'steps' and enhanced_content.get('steps'):
                testcase.steps = json.dumps(enhanced_content['steps'])
            
            if enhancement_type == 'assertions' and enhanced_content.get('expected_result'):
                testcase.expected_result = enhanced_content['expected_result']
            
            if enhancement_type == 'data' and enhanced_content.get('test_data'):
                testcase.test_data = json.dumps(enhanced_content['test_data'])
            
            # 更新AI相关字段
            testcase.ai_enhanced = True
            testcase.ai_suggestions = json.dumps(enhanced_content.get('suggestions', []))
            testcase.save()
            
            # 更新任务状态
            task.status = 'completed'
            task.progress = 100
            task.result = json.dumps(enhanced_content)
            task.save()
            
            logger.info(f"AI增强测试用例完成: 任务ID {task_id}")
            
        except Exception as e:
            logger.error(f"异步增强测试用例失败: {e}")
            task = AITask.query.get(task_id)
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                task.save()
    
    def analyze_execution_result(self, execution: TestExecution,
                               analysis_type: str = 'failure') -> Dict[str, Any]:
        """AI分析测试执行结果"""
        try:
            # 创建AI任务
            task = AITask(
                task_type='analyze_execution',
                status='pending',
                parameters=json.dumps({
                    'execution_id': execution.id,
                    'analysis_type': analysis_type
                })
            )
            task.save()
            
            # 异步执行分析任务
            threading.Thread(
                target=self._analyze_execution_async,
                args=(task.id, execution.id, analysis_type)
            ).start()
            
            return {
                'success': True,
                'task_id': task.id,
                'message': '测试执行分析任务已启动'
            }
            
        except Exception as e:
            logger.error(f"分析测试执行失败: {e}")
            return {
                'success': False,
                'message': f'分析测试执行失败: {str(e)}'
            }
    
    def _analyze_execution_async(self, task_id: int, execution_id: int, analysis_type: str):
        """异步分析测试执行"""
        try:
            task = AITask.query.get(task_id)
            execution = TestExecution.query.get(execution_id)
            
            if not task or not execution:
                return
            
            task.status = 'running'
            task.progress = 20
            task.save()
            
            # 调用AI分析执行结果
            if self.openai_client:
                analysis = self._call_openai_analyze_execution(execution, analysis_type)
            else:
                # 使用规则分析（备用方案）
                analysis = self._analyze_execution_by_rules(execution, analysis_type)
            
            task.progress = 80
            task.save()
            
            # 更新任务状态
            task.status = 'completed'
            task.progress = 100
            task.result = json.dumps(analysis)
            task.save()
            
            logger.info(f"AI分析测试执行完成: 任务ID {task_id}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"异步分析测试执行失败: {e}")
            task = AITask.query.get(task_id)
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                task.save()
    
    def analyze_bug_root_cause(self, bug: Bug, include_similar: bool = True) -> Dict[str, Any]:
        """AI分析Bug根因"""
        try:
            # 创建AI任务
            task = AITask(
                task_type='analyze_bug',
                status='pending',
                parameters=json.dumps({
                    'bug_id': bug.id,
                    'include_similar': include_similar
                })
            )
            task.save()
            
            # 异步执行分析任务
            threading.Thread(
                target=self._analyze_bug_async,
                args=(task.id, bug.id, include_similar)
            ).start()
            
            return {
                'success': True,
                'task_id': task.id,
                'message': 'Bug根因分析任务已启动'
            }
            
        except Exception as e:
            logger.error(f"分析Bug根因失败: {e}")
            return {
                'success': False,
                'message': f'分析Bug根因失败: {str(e)}'
            }
    
    def _analyze_bug_async(self, task_id: int, bug_id: int, include_similar: bool):
        """异步分析Bug根因"""
        try:
            task = AITask.query.get(task_id)
            bug = Bug.query.get(bug_id)
            
            if not task or not bug:
                return
            
            task.status = 'running'
            task.progress = 20
            task.save()
            
            # 调用AI分析Bug根因
            if self.openai_client:
                analysis = self._call_openai_analyze_bug(bug, include_similar)
            else:
                # 使用规则分析（备用方案）
                analysis = self._analyze_bug_by_rules(bug, include_similar)
            
            task.progress = 60
            task.save()
            
            # 查找相似Bug
            if include_similar:
                similar_bugs = self._find_similar_bugs_internal(bug)
                analysis['similar_bugs'] = similar_bugs
            
            task.progress = 90
            task.save()
            
            # 更新任务状态
            task.status = 'completed'
            task.progress = 100
            task.result = json.dumps(analysis)
            task.save()
            
            logger.info(f"AI分析Bug根因完成: 任务ID {task_id}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"异步分析Bug根因失败: {e}")
            task = AITask.query.get(task_id)
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                task.save()
    
    def find_similar_bugs(self, bug: Bug, similarity_threshold: float = 0.7,
                         max_results: int = 10) -> Dict[str, Any]:
        """AI查找相似Bug"""
        try:
            # 创建AI任务
            task = AITask(
                task_type='find_similar_bugs',
                status='pending',
                parameters=json.dumps({
                    'bug_id': bug.id,
                    'similarity_threshold': similarity_threshold,
                    'max_results': max_results
                })
            )
            task.save()
            
            # 异步执行查找任务
            threading.Thread(
                target=self._find_similar_bugs_async,
                args=(task.id, bug.id, similarity_threshold, max_results)
            ).start()
            
            return {
                'success': True,
                'task_id': task.id,
                'message': '相似Bug查找任务已启动'
            }
            
        except Exception as e:
            logger.error(f"查找相似Bug失败: {e}")
            return {
                'success': False,
                'message': f'查找相似Bug失败: {str(e)}'
            }
    
    def _find_similar_bugs_async(self, task_id: int, bug_id: int,
                               similarity_threshold: float, max_results: int):
        """异步查找相似Bug"""
        try:
            task = AITask.query.get(task_id)
            bug = Bug.query.get(bug_id)
            
            if not task or not bug:
                return
            
            task.status = 'running'
            task.progress = 20
            task.save()
            
            # 查找相似Bug
            similar_bugs = self._find_similar_bugs_internal(
                bug, similarity_threshold, max_results
            )
            
            task.progress = 90
            task.save()
            
            # 更新任务状态
            task.status = 'completed'
            task.progress = 100
            task.result = json.dumps({
                'similar_bugs': similar_bugs,
                'count': len(similar_bugs)
            })
            task.save()
            
            logger.info(f"AI查找相似Bug完成: 任务ID {task_id}")
            
        except Exception as e:
            logger.error(f"异步查找相似Bug失败: {e}")
            task = AITask.query.get(task_id)
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                task.save()
    
    def assess_project_risk(self, project_id: int, assessment_type: str = 'comprehensive',
                          time_range: int = 30) -> Dict[str, Any]:
        """AI项目风险评估"""
        try:
            # 创建AI任务
            task = AITask(
                task_type='risk_assessment',
                status='pending',
                parameters=json.dumps({
                    'project_id': project_id,
                    'assessment_type': assessment_type,
                    'time_range': time_range
                })
            )
            task.save()
            
            # 异步执行评估任务
            threading.Thread(
                target=self._assess_project_risk_async,
                args=(task.id, project_id, assessment_type, time_range)
            ).start()
            
            return {
                'success': True,
                'task_id': task.id,
                'message': '项目风险评估任务已启动'
            }
            
        except Exception as e:
            logger.error(f"项目风险评估失败: {e}")
            return {
                'success': False,
                'message': f'项目风险评估失败: {str(e)}'
            }
    
    def analyze_test_report(self, report: TestReport) -> Dict[str, Any]:
        """AI分析测试报告"""
        try:
            # 创建AI任务
            task = AITask(
                task_type='analyze_report',
                status='pending',
                parameters=json.dumps({
                    'report_id': report.id
                })
            )
            task.save()
            
            # 异步执行分析任务
            threading.Thread(
                target=self._analyze_test_report_async,
                args=(task.id, report.id)
            ).start()
            
            return {
                'success': True,
                'task_id': task.id,
                'message': '测试报告分析任务已启动'
            }
            
        except Exception as e:
            logger.error(f"分析测试报告失败: {e}")
            return {
                'success': False,
                'message': f'分析测试报告失败: {str(e)}'
            }
    
    # OpenAI调用方法
    def _call_openai_generate_testcases(self, context: str, requirement: str,
                                       test_type: str, priority: str, count: int) -> List[Dict]:
        """调用OpenAI生成测试用例"""
        try:
            prompt = f"""
            基于以下项目上下文和需求，生成 {count} 个 {test_type} 类型的测试用例，优先级为 {priority}。
            
            项目上下文：
            {context}
            
            需求描述：
            {requirement}
            
            请生成JSON格式的测试用例，包含以下字段：
            - title: 测试用例标题
            - description: 测试用例描述
            - steps: 测试步骤列表
            - expected_result: 预期结果
            - confidence: 置信度(0-1)
            
            返回格式：
            [
                {
                    "title": "测试用例标题",
                    "description": "测试用例描述",
                    "steps": ["步骤1", "步骤2", "步骤3"],
                    "expected_result": "预期结果",
                    "confidence": 0.9
                }
            ]
            """
            
            response = self.openai_client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的测试工程师，擅长编写高质量的测试用例。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # 解析JSON响应
            test_cases = json.loads(content)
            
            return test_cases
            
        except Exception as e:
            logger.error(f"OpenAI生成测试用例失败: {e}")
            # 返回备用方案
            return self._generate_testcases_by_template(requirement, test_type, priority, count)
    
    # 备用方案方法
    def _generate_testcases_by_template(self, requirement: str, test_type: str,
                                      priority: str, count: int) -> List[Dict]:
        """使用模板生成测试用例（备用方案）"""
        test_cases = []
        
        templates = {
            'functional': [
                {
                    'title': f'功能测试 - {requirement}',
                    'description': f'验证{requirement}的基本功能',
                    'steps': ['打开应用', '执行操作', '验证结果'],
                    'expected_result': '功能正常工作',
                    'confidence': 0.7
                }
            ],
            'ui': [
                {
                    'title': f'界面测试 - {requirement}',
                    'description': f'验证{requirement}的界面显示',
                    'steps': ['打开页面', '检查界面元素', '验证布局'],
                    'expected_result': '界面显示正确',
                    'confidence': 0.7
                }
            ],
            'api': [
                {
                    'title': f'API测试 - {requirement}',
                    'description': f'验证{requirement}的API接口',
                    'steps': ['发送请求', '检查响应', '验证数据'],
                    'expected_result': 'API返回正确',
                    'confidence': 0.7
                }
            ]
        }
        
        template_list = templates.get(test_type, templates['functional'])
        
        for i in range(min(count, len(template_list) * 3)):
            template = template_list[i % len(template_list)]
            test_case = template.copy()
            test_case['title'] = f"{test_case['title']} - 用例{i+1}"
            test_cases.append(test_case)
        
        return test_cases
    
    def _enhance_testcase_by_rules(self, testcase: TestCase, enhancement_type: str) -> Dict:
        """使用规则增强测试用例（备用方案）"""
        enhanced_content = {}
        
        if enhancement_type == 'steps':
            current_steps = json.loads(testcase.steps or '[]')
            enhanced_steps = current_steps.copy()
            
            # 添加前置条件
            if not any('前置' in step for step in enhanced_steps):
                enhanced_steps.insert(0, '前置条件：确保系统正常运行')
            
            # 添加清理步骤
            if not any('清理' in step for step in enhanced_steps):
                enhanced_steps.append('清理：恢复测试环境')
            
            enhanced_content['steps'] = enhanced_steps
            enhanced_content['suggestions'] = ['添加了前置条件和清理步骤']
        
        elif enhancement_type == 'assertions':
            enhanced_content['expected_result'] = f"{testcase.expected_result}\n\n增强验证点：\n- 检查响应时间\n- 验证数据完整性\n- 确认错误处理"
            enhanced_content['suggestions'] = ['增加了详细的验证点']
        
        elif enhancement_type == 'data':
            enhanced_content['test_data'] = {
                'valid_data': {'example': 'valid_value'},
                'invalid_data': {'example': 'invalid_value'},
                'boundary_data': {'example': 'boundary_value'}
            }
            enhanced_content['suggestions'] = ['添加了测试数据集']
        
        return enhanced_content
    
    def _analyze_execution_by_rules(self, execution: TestExecution, analysis_type: str) -> Dict:
        """使用规则分析测试执行（备用方案）"""
        analysis = {
            'analysis_type': analysis_type,
            'execution_id': execution.id,
            'timestamp': datetime.now().isoformat()
        }
        
        if execution.result == 'failed':
            analysis['failure_analysis'] = {
                'possible_causes': [
                    '环境配置问题',
                    '数据依赖问题',
                    '时序问题',
                    '网络连接问题'
                ],
                'suggestions': [
                    '检查测试环境配置',
                    '验证测试数据',
                    '增加等待时间',
                    '检查网络连接'
                ],
                'confidence': 0.6
            }
        elif execution.result == 'passed':
            analysis['success_analysis'] = {
                'performance': '正常',
                'stability': '稳定',
                'confidence': 0.8
            }
        
        return analysis
    
    def _analyze_bug_by_rules(self, bug: Bug, include_similar: bool) -> Dict:
        """使用规则分析Bug（备用方案）"""
        analysis = {
            'bug_id': bug.id,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # 根据Bug描述分析可能原因
        description = bug.description.lower()
        
        if '崩溃' in description or 'crash' in description:
            analysis['root_cause'] = '应用崩溃，可能是内存泄漏或空指针异常'
            analysis['category'] = 'stability'
        elif '性能' in description or 'performance' in description:
            analysis['root_cause'] = '性能问题，可能是算法效率或资源使用不当'
            analysis['category'] = 'performance'
        elif '界面' in description or 'ui' in description:
            analysis['root_cause'] = '界面显示问题，可能是CSS样式或布局问题'
            analysis['category'] = 'ui'
        else:
            analysis['root_cause'] = '功能逻辑问题，需要进一步分析代码逻辑'
            analysis['category'] = 'functional'
        
        analysis['confidence'] = 0.6
        analysis['suggestions'] = [
            '检查相关代码逻辑',
            '重现Bug场景',
            '分析日志信息',
            '进行单元测试'
        ]
        
        return analysis
    
    def _find_similar_bugs_internal(self, bug: Bug, similarity_threshold: float = 0.7,
                                  max_results: int = 10) -> List[Dict]:
        """内部查找相似Bug方法"""
        try:
            # 获取同项目的其他Bug
            other_bugs = Bug.query.filter(
                Bug.project_id == bug.project_id,
                Bug.id != bug.id
            ).all()
            
            similar_bugs = []
            
            for other_bug in other_bugs:
                # 计算相似度
                title_similarity = calculate_similarity(bug.title, other_bug.title)
                desc_similarity = calculate_similarity(bug.description, other_bug.description)
                
                # 综合相似度
                overall_similarity = (title_similarity * 0.6 + desc_similarity * 0.4)
                
                if overall_similarity >= similarity_threshold:
                    similar_bugs.append({
                        'bug_id': other_bug.id,
                        'title': other_bug.title,
                        'similarity': round(overall_similarity, 3),
                        'status': other_bug.status,
                        'created_at': other_bug.created_at.isoformat()
                    })
            
            # 按相似度排序
            similar_bugs.sort(key=lambda x: x['similarity'], reverse=True)
            
            return similar_bugs[:max_results]
            
        except Exception as e:
            logger.error(f"查找相似Bug失败: {e}")
            return []
    
    def _build_project_context(self, project: Project, module: Optional[Module] = None) -> str:
        """构建项目上下文信息"""
        context = f"项目名称: {project.name}\n"
        context += f"项目描述: {project.description}\n"
        
        if module:
            context += f"模块名称: {module.name}\n"
            context += f"模块描述: {module.description}\n"
        
        # 添加项目的测试用例统计
        total_cases = TestCase.query.filter_by(project_id=project.id).count()
        context += f"现有测试用例数量: {total_cases}\n"
        
        return context
    
    # 其他异步方法的实现...
    def _assess_project_risk_async(self, task_id: int, project_id: int,
                                 assessment_type: str, time_range: int):
        """异步项目风险评估"""
        # 实现风险评估逻辑
        pass
    
    def _analyze_test_report_async(self, task_id: int, report_id: int):
        """异步测试报告分析"""
        # 实现报告分析逻辑
        pass