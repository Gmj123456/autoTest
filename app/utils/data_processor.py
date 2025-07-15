#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据处理工具
提供数据清洗、转换、分析等功能
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from loguru import logger
import re

class DataProcessor:
    """数据处理器类"""
    
    def __init__(self):
        self.data_cache = {}
    
    def clean_text_data(self, text: str) -> str:
        """清洗文本数据
        
        Args:
            text: 原始文本
        
        Returns:
            清洗后的文本
        """
        try:
            if not text or not isinstance(text, str):
                return ''
            
            # 移除HTML标签
            text = re.sub(r'<[^>]+>', '', text)
            
            # 移除多余的空白字符
            text = re.sub(r'\s+', ' ', text)
            
            # 移除首尾空白
            text = text.strip()
            
            # 移除特殊控制字符
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)
            
            return text
            
        except Exception as e:
            logger.error(f"清洗文本数据失败: {e}")
            return text if isinstance(text, str) else ''
    
    def validate_json_data(self, json_str: str) -> Dict[str, Any]:
        """验证和解析JSON数据
        
        Args:
            json_str: JSON字符串
        
        Returns:
            解析后的字典，如果解析失败返回空字典
        """
        try:
            if not json_str:
                return {}
            
            # 尝试解析JSON
            data = json.loads(json_str)
            
            # 验证数据类型
            if not isinstance(data, dict):
                logger.warning(f"JSON数据不是字典类型: {type(data)}")
                return {}
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"验证JSON数据失败: {e}")
            return {}
    
    def normalize_test_data(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化测试数据
        
        Args:
            test_data: 原始测试数据
        
        Returns:
            标准化后的测试数据
        """
        try:
            normalized_data = {}
            
            for key, value in test_data.items():
                # 清洗键名
                clean_key = self.clean_text_data(str(key)).lower().replace(' ', '_')
                
                # 处理值
                if isinstance(value, str):
                    normalized_data[clean_key] = self.clean_text_data(value)
                elif isinstance(value, (int, float, bool)):
                    normalized_data[clean_key] = value
                elif isinstance(value, list):
                    normalized_data[clean_key] = [self.clean_text_data(str(item)) if isinstance(item, str) else item for item in value]
                elif isinstance(value, dict):
                    normalized_data[clean_key] = self.normalize_test_data(value)
                else:
                    normalized_data[clean_key] = str(value)
            
            return normalized_data
            
        except Exception as e:
            logger.error(f"标准化测试数据失败: {e}")
            return test_data
    
    def extract_execution_metrics(self, executions: List[Dict]) -> Dict[str, Any]:
        """提取执行指标
        
        Args:
            executions: 执行记录列表
        
        Returns:
            执行指标字典
        """
        try:
            if not executions:
                return self._get_empty_metrics()
            
            # 转换为DataFrame便于分析
            df = pd.DataFrame(executions)
            
            # 基本统计
            total_count = len(df)
            passed_count = len(df[df['result'] == 'passed'])
            failed_count = len(df[df['result'] == 'failed'])
            skipped_count = len(df[df['result'] == 'skipped'])
            
            # 计算通过率
            pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0
            
            # 执行时间分析
            execution_times = []
            for execution in executions:
                if execution.get('execution_time'):
                    try:
                        exec_time = float(execution['execution_time'])
                        execution_times.append(exec_time)
                    except (ValueError, TypeError):
                        continue
            
            time_stats = {}
            if execution_times:
                time_stats = {
                    'avg_time': round(np.mean(execution_times), 2),
                    'min_time': round(np.min(execution_times), 2),
                    'max_time': round(np.max(execution_times), 2),
                    'median_time': round(np.median(execution_times), 2)
                }
            
            # 按日期统计
            daily_stats = self._calculate_daily_execution_stats(executions)
            
            # 按优先级统计
            priority_stats = self._calculate_priority_stats(executions)
            
            # 按测试类型统计
            type_stats = self._calculate_type_stats(executions)
            
            return {
                'total_count': total_count,
                'passed_count': passed_count,
                'failed_count': failed_count,
                'skipped_count': skipped_count,
                'pass_rate': round(pass_rate, 2),
                'time_stats': time_stats,
                'daily_stats': daily_stats,
                'priority_stats': priority_stats,
                'type_stats': type_stats
            }
            
        except Exception as e:
            logger.error(f"提取执行指标失败: {e}")
            return self._get_empty_metrics()
    
    def analyze_bug_patterns(self, bugs: List[Dict]) -> Dict[str, Any]:
        """分析Bug模式
        
        Args:
            bugs: Bug记录列表
        
        Returns:
            Bug分析结果
        """
        try:
            if not bugs:
                return {
                    'total_count': 0,
                    'severity_distribution': {},
                    'status_distribution': {},
                    'common_keywords': [],
                    'trend_analysis': []
                }
            
            # 转换为DataFrame
            df = pd.DataFrame(bugs)
            
            # 严重程度分布
            severity_dist = df['severity'].value_counts().to_dict() if 'severity' in df.columns else {}
            
            # 状态分布
            status_dist = df['status'].value_counts().to_dict() if 'status' in df.columns else {}
            
            # 提取常见关键词
            common_keywords = self._extract_bug_keywords(bugs)
            
            # 趋势分析
            trend_analysis = self._analyze_bug_trends(bugs)
            
            # 根因分析
            root_cause_analysis = self._analyze_root_causes(bugs)
            
            return {
                'total_count': len(bugs),
                'severity_distribution': severity_dist,
                'status_distribution': status_dist,
                'common_keywords': common_keywords,
                'trend_analysis': trend_analysis,
                'root_cause_analysis': root_cause_analysis
            }
            
        except Exception as e:
            logger.error(f"分析Bug模式失败: {e}")
            return {}
    
    def calculate_test_coverage(self, test_cases: List[Dict], 
                              executions: List[Dict]) -> Dict[str, Any]:
        """计算测试覆盖率
        
        Args:
            test_cases: 测试用例列表
            executions: 执行记录列表
        
        Returns:
            覆盖率分析结果
        """
        try:
            if not test_cases:
                return {'overall_coverage': 0, 'module_coverage': {}, 'type_coverage': {}}
            
            # 获取已执行的测试用例ID
            executed_case_ids = set()
            for execution in executions:
                if execution.get('test_case_id'):
                    executed_case_ids.add(execution['test_case_id'])
            
            # 总体覆盖率
            total_cases = len(test_cases)
            executed_cases = len(executed_case_ids)
            overall_coverage = (executed_cases / total_cases * 100) if total_cases > 0 else 0
            
            # 按模块计算覆盖率
            module_coverage = self._calculate_module_coverage(test_cases, executed_case_ids)
            
            # 按测试类型计算覆盖率
            type_coverage = self._calculate_type_coverage(test_cases, executed_case_ids)
            
            # 按优先级计算覆盖率
            priority_coverage = self._calculate_priority_coverage(test_cases, executed_case_ids)
            
            return {
                'overall_coverage': round(overall_coverage, 2),
                'total_cases': total_cases,
                'executed_cases': executed_cases,
                'module_coverage': module_coverage,
                'type_coverage': type_coverage,
                'priority_coverage': priority_coverage
            }
            
        except Exception as e:
            logger.error(f"计算测试覆盖率失败: {e}")
            return {}
    
    def generate_quality_metrics(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成质量指标
        
        Args:
            project_data: 项目数据
        
        Returns:
            质量指标字典
        """
        try:
            test_cases = project_data.get('test_cases', [])
            executions = project_data.get('executions', [])
            bugs = project_data.get('bugs', [])
            
            # 测试执行质量
            execution_metrics = self.extract_execution_metrics(executions)
            
            # 缺陷质量
            bug_metrics = self.analyze_bug_patterns(bugs)
            
            # 测试覆盖率
            coverage_metrics = self.calculate_test_coverage(test_cases, executions)
            
            # 稳定性指标
            stability_metrics = self._calculate_stability_metrics(executions)
            
            # 效率指标
            efficiency_metrics = self._calculate_efficiency_metrics(executions, test_cases)
            
            # 综合质量评分
            quality_score = self._calculate_quality_score(
                execution_metrics, bug_metrics, coverage_metrics, 
                stability_metrics, efficiency_metrics
            )
            
            return {
                'quality_score': quality_score,
                'execution_metrics': execution_metrics,
                'bug_metrics': bug_metrics,
                'coverage_metrics': coverage_metrics,
                'stability_metrics': stability_metrics,
                'efficiency_metrics': efficiency_metrics,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成质量指标失败: {e}")
            return {}
    
    def _get_empty_metrics(self) -> Dict[str, Any]:
        """获取空的指标字典"""
        return {
            'total_count': 0,
            'passed_count': 0,
            'failed_count': 0,
            'skipped_count': 0,
            'pass_rate': 0,
            'time_stats': {},
            'daily_stats': [],
            'priority_stats': {},
            'type_stats': {}
        }
    
    def _calculate_daily_execution_stats(self, executions: List[Dict]) -> List[Dict]:
        """计算每日执行统计"""
        try:
            daily_stats = {}
            
            for execution in executions:
                created_at = execution.get('created_at')
                if not created_at:
                    continue
                
                # 解析日期
                if isinstance(created_at, str):
                    try:
                        date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        continue
                elif isinstance(created_at, datetime):
                    date_obj = created_at
                else:
                    continue
                
                date_key = date_obj.date().isoformat()
                
                if date_key not in daily_stats:
                    daily_stats[date_key] = {
                        'date': date_key,
                        'total': 0,
                        'passed': 0,
                        'failed': 0,
                        'skipped': 0
                    }
                
                daily_stats[date_key]['total'] += 1
                result = execution.get('result', 'unknown')
                if result in daily_stats[date_key]:
                    daily_stats[date_key][result] += 1
            
            # 转换为列表并排序
            return sorted(daily_stats.values(), key=lambda x: x['date'])
            
        except Exception as e:
            logger.error(f"计算每日执行统计失败: {e}")
            return []
    
    def _calculate_priority_stats(self, executions: List[Dict]) -> Dict[str, int]:
        """计算优先级统计"""
        try:
            priority_stats = {}
            
            for execution in executions:
                priority = execution.get('priority', 'unknown')
                priority_stats[priority] = priority_stats.get(priority, 0) + 1
            
            return priority_stats
            
        except Exception as e:
            logger.error(f"计算优先级统计失败: {e}")
            return {}
    
    def _calculate_type_stats(self, executions: List[Dict]) -> Dict[str, int]:
        """计算测试类型统计"""
        try:
            type_stats = {}
            
            for execution in executions:
                test_type = execution.get('test_type', 'unknown')
                type_stats[test_type] = type_stats.get(test_type, 0) + 1
            
            return type_stats
            
        except Exception as e:
            logger.error(f"计算测试类型统计失败: {e}")
            return {}
    
    def _extract_bug_keywords(self, bugs: List[Dict]) -> List[str]:
        """提取Bug关键词"""
        try:
            from app.utils.text_similarity import extract_keywords
            
            # 合并所有Bug的标题和描述
            all_text = ''
            for bug in bugs:
                title = bug.get('title', '')
                description = bug.get('description', '')
                all_text += f" {title} {description}"
            
            # 提取关键词
            keywords = extract_keywords(all_text, top_k=10)
            
            return keywords
            
        except Exception as e:
            logger.error(f"提取Bug关键词失败: {e}")
            return []
    
    def _analyze_bug_trends(self, bugs: List[Dict]) -> List[Dict]:
        """分析Bug趋势"""
        try:
            # 按日期统计Bug数量
            daily_bugs = {}
            
            for bug in bugs:
                created_at = bug.get('created_at')
                if not created_at:
                    continue
                
                # 解析日期
                if isinstance(created_at, str):
                    try:
                        date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        continue
                elif isinstance(created_at, datetime):
                    date_obj = created_at
                else:
                    continue
                
                date_key = date_obj.date().isoformat()
                daily_bugs[date_key] = daily_bugs.get(date_key, 0) + 1
            
            # 转换为列表
            trend_data = []
            for date, count in sorted(daily_bugs.items()):
                trend_data.append({
                    'date': date,
                    'count': count
                })
            
            return trend_data
            
        except Exception as e:
            logger.error(f"分析Bug趋势失败: {e}")
            return []
    
    def _analyze_root_causes(self, bugs: List[Dict]) -> Dict[str, Any]:
        """分析根因"""
        try:
            root_causes = {}
            
            for bug in bugs:
                # 从AI分析结果中提取根因
                ai_analysis = bug.get('ai_root_cause_analysis')
                if ai_analysis:
                    try:
                        analysis_data = json.loads(ai_analysis) if isinstance(ai_analysis, str) else ai_analysis
                        category = analysis_data.get('category', 'unknown')
                        root_causes[category] = root_causes.get(category, 0) + 1
                    except:
                        pass
            
            return root_causes
            
        except Exception as e:
            logger.error(f"分析根因失败: {e}")
            return {}
    
    def _calculate_module_coverage(self, test_cases: List[Dict], 
                                 executed_case_ids: set) -> Dict[str, float]:
        """计算模块覆盖率"""
        try:
            module_coverage = {}
            module_stats = {}
            
            # 统计每个模块的用例数和执行数
            for case in test_cases:
                module_id = case.get('module_id', 'unknown')
                module_name = case.get('module_name', f'Module_{module_id}')
                
                if module_name not in module_stats:
                    module_stats[module_name] = {'total': 0, 'executed': 0}
                
                module_stats[module_name]['total'] += 1
                
                if case.get('id') in executed_case_ids:
                    module_stats[module_name]['executed'] += 1
            
            # 计算覆盖率
            for module_name, stats in module_stats.items():
                coverage = (stats['executed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                module_coverage[module_name] = round(coverage, 2)
            
            return module_coverage
            
        except Exception as e:
            logger.error(f"计算模块覆盖率失败: {e}")
            return {}
    
    def _calculate_type_coverage(self, test_cases: List[Dict], 
                               executed_case_ids: set) -> Dict[str, float]:
        """计算测试类型覆盖率"""
        try:
            type_coverage = {}
            type_stats = {}
            
            # 统计每个测试类型的用例数和执行数
            for case in test_cases:
                test_type = case.get('test_type', 'unknown')
                
                if test_type not in type_stats:
                    type_stats[test_type] = {'total': 0, 'executed': 0}
                
                type_stats[test_type]['total'] += 1
                
                if case.get('id') in executed_case_ids:
                    type_stats[test_type]['executed'] += 1
            
            # 计算覆盖率
            for test_type, stats in type_stats.items():
                coverage = (stats['executed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                type_coverage[test_type] = round(coverage, 2)
            
            return type_coverage
            
        except Exception as e:
            logger.error(f"计算测试类型覆盖率失败: {e}")
            return {}
    
    def _calculate_priority_coverage(self, test_cases: List[Dict], 
                                   executed_case_ids: set) -> Dict[str, float]:
        """计算优先级覆盖率"""
        try:
            priority_coverage = {}
            priority_stats = {}
            
            # 统计每个优先级的用例数和执行数
            for case in test_cases:
                priority = case.get('priority', 'unknown')
                
                if priority not in priority_stats:
                    priority_stats[priority] = {'total': 0, 'executed': 0}
                
                priority_stats[priority]['total'] += 1
                
                if case.get('id') in executed_case_ids:
                    priority_stats[priority]['executed'] += 1
            
            # 计算覆盖率
            for priority, stats in priority_stats.items():
                coverage = (stats['executed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                priority_coverage[priority] = round(coverage, 2)
            
            return priority_coverage
            
        except Exception as e:
            logger.error(f"计算优先级覆盖率失败: {e}")
            return {}
    
    def _calculate_stability_metrics(self, executions: List[Dict]) -> Dict[str, Any]:
        """计算稳定性指标"""
        try:
            if not executions:
                return {'flaky_rate': 0, 'consistency_score': 0}
            
            # 计算不稳定用例率（同一用例多次执行结果不一致）
            case_results = {}
            for execution in executions:
                case_id = execution.get('test_case_id')
                result = execution.get('result')
                
                if case_id and result:
                    if case_id not in case_results:
                        case_results[case_id] = []
                    case_results[case_id].append(result)
            
            flaky_cases = 0
            total_multi_run_cases = 0
            
            for case_id, results in case_results.items():
                if len(results) > 1:  # 多次执行的用例
                    total_multi_run_cases += 1
                    if len(set(results)) > 1:  # 结果不一致
                        flaky_cases += 1
            
            flaky_rate = (flaky_cases / total_multi_run_cases * 100) if total_multi_run_cases > 0 else 0
            
            # 一致性评分
            consistency_score = 100 - flaky_rate
            
            return {
                'flaky_rate': round(flaky_rate, 2),
                'consistency_score': round(consistency_score, 2),
                'flaky_cases': flaky_cases,
                'total_multi_run_cases': total_multi_run_cases
            }
            
        except Exception as e:
            logger.error(f"计算稳定性指标失败: {e}")
            return {}
    
    def _calculate_efficiency_metrics(self, executions: List[Dict], 
                                    test_cases: List[Dict]) -> Dict[str, Any]:
        """计算效率指标"""
        try:
            if not executions:
                return {'automation_rate': 0, 'execution_efficiency': 0}
            
            # 自动化率
            automated_cases = len([case for case in test_cases if case.get('automated', False)])
            total_cases = len(test_cases)
            automation_rate = (automated_cases / total_cases * 100) if total_cases > 0 else 0
            
            # 执行效率（基于执行时间）
            execution_times = []
            for execution in executions:
                exec_time = execution.get('execution_time')
                if exec_time:
                    try:
                        execution_times.append(float(exec_time))
                    except (ValueError, TypeError):
                        pass
            
            avg_execution_time = np.mean(execution_times) if execution_times else 0
            
            # 效率评分（执行时间越短效率越高）
            if avg_execution_time > 0:
                efficiency_score = max(0, 100 - (avg_execution_time / 60) * 10)  # 假设1分钟为基准
            else:
                efficiency_score = 0
            
            return {
                'automation_rate': round(automation_rate, 2),
                'execution_efficiency': round(efficiency_score, 2),
                'avg_execution_time': round(avg_execution_time, 2),
                'automated_cases': automated_cases,
                'total_cases': total_cases
            }
            
        except Exception as e:
            logger.error(f"计算效率指标失败: {e}")
            return {}
    
    def _calculate_quality_score(self, execution_metrics: Dict, bug_metrics: Dict,
                               coverage_metrics: Dict, stability_metrics: Dict,
                               efficiency_metrics: Dict) -> float:
        """计算综合质量评分"""
        try:
            # 各项指标权重
            weights = {
                'pass_rate': 0.3,
                'coverage': 0.25,
                'stability': 0.2,
                'efficiency': 0.15,
                'bug_density': 0.1
            }
            
            # 获取各项评分
            pass_rate_score = execution_metrics.get('pass_rate', 0)
            coverage_score = coverage_metrics.get('overall_coverage', 0)
            stability_score = stability_metrics.get('consistency_score', 0)
            efficiency_score = efficiency_metrics.get('execution_efficiency', 0)
            
            # Bug密度评分（Bug越少评分越高）
            bug_count = bug_metrics.get('total_count', 0)
            total_cases = coverage_metrics.get('total_cases', 1)
            bug_density = bug_count / total_cases
            bug_density_score = max(0, 100 - bug_density * 50)
            
            # 加权计算综合评分
            quality_score = (
                pass_rate_score * weights['pass_rate'] +
                coverage_score * weights['coverage'] +
                stability_score * weights['stability'] +
                efficiency_score * weights['efficiency'] +
                bug_density_score * weights['bug_density']
            )
            
            return round(quality_score, 2)
            
        except Exception as e:
            logger.error(f"计算质量评分失败: {e}")
            return 0.0