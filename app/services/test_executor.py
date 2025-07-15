#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试执行引擎
负责执行各种类型的测试用例
"""

import json
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, Future
from app.models import TestExecution, TestCase, db
from app.services.ai_service import AIService

class TestExecutor:
    """测试执行器类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.browser_config = config.get('browser', {})
        self.execution_config = config.get('execution', {})
        self.ai_service = AIService(config.get('ai', {}))
        self.running_executions = {}
        self.executor = ThreadPoolExecutor(max_workers=self.execution_config.get('max_workers', 5))
        
    def execute_test_case(self, test_case: TestCase, execution_id: int, 
                         callback: Optional[Callable] = None) -> Dict[str, Any]:
        """执行单个测试用例
        
        Args:
            test_case: 测试用例对象
            execution_id: 执行记录ID
            callback: 执行完成回调函数
        
        Returns:
            执行结果字典
        """
        try:
            logger.info(f"开始执行测试用例: {test_case.title} (ID: {test_case.id})")
            
            # 更新执行状态
            self._update_execution_status(execution_id, 'running')
            
            start_time = time.time()
            result = {'result': 'failed', 'message': '', 'details': {}}
            
            # 根据测试类型选择执行方法
            test_type = test_case.test_type
            
            if test_type == 'web_ui':
                result = self._execute_web_ui_test(test_case)
            elif test_type == 'api':
                result = self._execute_api_test(test_case)
            elif test_type == 'mobile':
                result = self._execute_mobile_test(test_case)
            elif test_type == 'performance':
                result = self._execute_performance_test(test_case)
            elif test_type == 'security':
                result = self._execute_security_test(test_case)
            else:
                result = self._execute_custom_test(test_case)
            
            # 计算执行时间
            execution_time = time.time() - start_time
            result['execution_time'] = round(execution_time, 2)
            
            # 更新执行记录
            self._update_execution_result(execution_id, result)
            
            # AI分析执行结果
            if self.config.get('ai', {}).get('enabled', False):
                try:
                    ai_analysis = self.ai_service.analyze_execution_result(
                        test_case.to_dict(), result
                    )
                    result['ai_analysis'] = ai_analysis
                    self._update_execution_ai_analysis(execution_id, ai_analysis)
                except Exception as e:
                    logger.warning(f"AI分析执行结果失败: {e}")
            
            # 执行回调
            if callback:
                try:
                    callback(test_case, result)
                except Exception as e:
                    logger.error(f"执行回调函数失败: {e}")
            
            logger.info(f"测试用例执行完成: {test_case.title}, 结果: {result['result']}")
            return result
            
        except Exception as e:
            logger.error(f"执行测试用例失败: {e}")
            error_result = {
                'result': 'error',
                'message': str(e),
                'execution_time': 0,
                'details': {}
            }
            self._update_execution_result(execution_id, error_result)
            return error_result
    
    def execute_test_cases_batch(self, test_cases: List[TestCase], 
                                execution_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """批量执行测试用例
        
        Args:
            test_cases: 测试用例列表
            execution_config: 执行配置
        
        Returns:
            执行结果列表
        """
        try:
            logger.info(f"开始批量执行测试用例，共 {len(test_cases)} 个")
            
            config = execution_config or {}
            parallel = config.get('parallel', False)
            max_workers = config.get('max_workers', 3)
            
            results = []
            
            if parallel:
                # 并行执行
                futures = []
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    for test_case in test_cases:
                        # 创建执行记录
                        execution = TestExecution(
                            test_case_id=test_case.id,
                            status='pending',
                            result='pending'
                        )
                        db.session.add(execution)
                        db.session.commit()
                        
                        future = executor.submit(self.execute_test_case, test_case, execution.id)
                        futures.append((future, test_case, execution.id))
                    
                    # 收集结果
                    for future, test_case, execution_id in futures:
                        try:
                            result = future.result(timeout=config.get('timeout', 300))
                            results.append({
                                'test_case_id': test_case.id,
                                'execution_id': execution_id,
                                'result': result
                            })
                        except Exception as e:
                            logger.error(f"获取执行结果失败: {e}")
                            results.append({
                                'test_case_id': test_case.id,
                                'execution_id': execution_id,
                                'result': {'result': 'error', 'message': str(e)}
                            })
            else:
                # 串行执行
                for test_case in test_cases:
                    # 创建执行记录
                    execution = TestExecution(
                        test_case_id=test_case.id,
                        status='pending',
                        result='pending'
                    )
                    db.session.add(execution)
                    db.session.commit()
                    
                    result = self.execute_test_case(test_case, execution.id)
                    results.append({
                        'test_case_id': test_case.id,
                        'execution_id': execution.id,
                        'result': result
                    })
            
            logger.info(f"批量执行完成，共 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"批量执行测试用例失败: {e}")
            return []
    
    def _execute_web_ui_test(self, test_case: TestCase) -> Dict[str, Any]:
        """执行Web UI测试"""
        driver = None
        try:
            # 解析测试步骤
            test_steps = self._parse_test_steps(test_case.test_steps)
            if not test_steps:
                return {'result': 'failed', 'message': '测试步骤为空'}
            
            # 创建浏览器驱动
            driver = self._create_web_driver()
            
            # 设置隐式等待
            driver.implicitly_wait(self.browser_config.get('implicit_wait', 10))
            
            # 执行测试步骤
            step_results = []
            for i, step in enumerate(test_steps, 1):
                try:
                    step_result = self._execute_web_step(driver, step, i)
                    step_results.append(step_result)
                    
                    if not step_result.get('success', False):
                        return {
                            'result': 'failed',
                            'message': f"步骤 {i} 执行失败: {step_result.get('message', '')}",
                            'details': {'step_results': step_results}
                        }
                except Exception as e:
                    return {
                        'result': 'failed',
                        'message': f"步骤 {i} 执行异常: {str(e)}",
                        'details': {'step_results': step_results}
                    }
            
            return {
                'result': 'passed',
                'message': '所有步骤执行成功',
                'details': {'step_results': step_results}
            }
            
        except Exception as e:
            logger.error(f"Web UI测试执行失败: {e}")
            return {'result': 'failed', 'message': str(e)}
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _execute_api_test(self, test_case: TestCase) -> Dict[str, Any]:
        """执行API测试"""
        try:
            # 解析API测试配置
            api_config = self._parse_api_config(test_case.test_steps)
            if not api_config:
                return {'result': 'failed', 'message': 'API配置为空'}
            
            # 准备请求参数
            method = api_config.get('method', 'GET').upper()
            url = api_config.get('url', '')
            headers = api_config.get('headers', {})
            params = api_config.get('params', {})
            data = api_config.get('data', {})
            json_data = api_config.get('json', {})
            timeout = api_config.get('timeout', 30)
            
            # 处理认证
            auth = None
            auth_config = api_config.get('auth', {})
            if auth_config:
                auth_type = auth_config.get('type', '')
                if auth_type == 'basic':
                    auth = HTTPBasicAuth(auth_config.get('username', ''), auth_config.get('password', ''))
                elif auth_type == 'digest':
                    auth = HTTPDigestAuth(auth_config.get('username', ''), auth_config.get('password', ''))
                elif auth_type == 'bearer':
                    headers['Authorization'] = f"Bearer {auth_config.get('token', '')}"
            
            # 发送请求
            start_time = time.time()
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data if data else None,
                json=json_data if json_data else None,
                auth=auth,
                timeout=timeout
            )
            response_time = time.time() - start_time
            
            # 验证响应
            validation_result = self._validate_api_response(response, api_config.get('validations', {}))
            
            # 构建结果
            result_details = {
                'request': {
                    'method': method,
                    'url': url,
                    'headers': headers,
                    'params': params,
                    'data': data,
                    'json': json_data
                },
                'response': {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'body': response.text[:1000],  # 限制响应体长度
                    'response_time': round(response_time, 3)
                },
                'validation': validation_result
            }
            
            if validation_result['success']:
                return {
                    'result': 'passed',
                    'message': 'API测试通过',
                    'details': result_details
                }
            else:
                return {
                    'result': 'failed',
                    'message': f"API验证失败: {validation_result['message']}",
                    'details': result_details
                }
            
        except requests.exceptions.RequestException as e:
            return {'result': 'failed', 'message': f'请求异常: {str(e)}'}
        except Exception as e:
            logger.error(f"API测试执行失败: {e}")
            return {'result': 'failed', 'message': str(e)}
    
    def _execute_mobile_test(self, test_case: TestCase) -> Dict[str, Any]:
        """执行移动端测试"""
        try:
            # 这里可以集成Appium等移动端测试框架
            # 目前返回模拟结果
            return {
                'result': 'skipped',
                'message': '移动端测试功能待实现',
                'details': {}
            }
        except Exception as e:
            logger.error(f"移动端测试执行失败: {e}")
            return {'result': 'failed', 'message': str(e)}
    
    def _execute_performance_test(self, test_case: TestCase) -> Dict[str, Any]:
        """执行性能测试"""
        try:
            # 解析性能测试配置
            perf_config = self._parse_performance_config(test_case.test_steps)
            
            # 执行性能测试（简化版本）
            url = perf_config.get('url', '')
            concurrent_users = perf_config.get('concurrent_users', 1)
            duration = perf_config.get('duration', 10)
            
            results = []
            start_time = time.time()
            
            # 简单的并发请求测试
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = []
                while time.time() - start_time < duration:
                    future = executor.submit(self._send_performance_request, url)
                    futures.append(future)
                    time.sleep(0.1)  # 控制请求频率
                
                for future in futures:
                    try:
                        result = future.result(timeout=5)
                        results.append(result)
                    except:
                        pass
            
            # 分析性能结果
            if results:
                response_times = [r['response_time'] for r in results if r.get('response_time')]
                success_count = len([r for r in results if r.get('success')])
                
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                success_rate = success_count / len(results) * 100 if results else 0
                
                performance_details = {
                    'total_requests': len(results),
                    'successful_requests': success_count,
                    'success_rate': round(success_rate, 2),
                    'avg_response_time': round(avg_response_time, 3),
                    'min_response_time': round(min(response_times), 3) if response_times else 0,
                    'max_response_time': round(max(response_times), 3) if response_times else 0
                }
                
                # 判断性能是否达标
                max_response_time = perf_config.get('max_response_time', 2.0)
                min_success_rate = perf_config.get('min_success_rate', 95.0)
                
                if avg_response_time <= max_response_time and success_rate >= min_success_rate:
                    return {
                        'result': 'passed',
                        'message': '性能测试通过',
                        'details': performance_details
                    }
                else:
                    return {
                        'result': 'failed',
                        'message': '性能测试未达标',
                        'details': performance_details
                    }
            else:
                return {'result': 'failed', 'message': '性能测试无有效结果'}
            
        except Exception as e:
            logger.error(f"性能测试执行失败: {e}")
            return {'result': 'failed', 'message': str(e)}
    
    def _execute_security_test(self, test_case: TestCase) -> Dict[str, Any]:
        """执行安全测试"""
        try:
            # 这里可以集成安全测试工具
            # 目前返回模拟结果
            return {
                'result': 'skipped',
                'message': '安全测试功能待实现',
                'details': {}
            }
        except Exception as e:
            logger.error(f"安全测试执行失败: {e}")
            return {'result': 'failed', 'message': str(e)}
    
    def _execute_custom_test(self, test_case: TestCase) -> Dict[str, Any]:
        """执行自定义测试"""
        try:
            # 解析自定义测试脚本
            script_config = self._parse_script_config(test_case.test_steps)
            
            if script_config.get('type') == 'python':
                return self._execute_python_script(script_config)
            elif script_config.get('type') == 'shell':
                return self._execute_shell_script(script_config)
            else:
                return {'result': 'failed', 'message': '不支持的自定义测试类型'}
            
        except Exception as e:
            logger.error(f"自定义测试执行失败: {e}")
            return {'result': 'failed', 'message': str(e)}
    
    def _create_web_driver(self) -> webdriver.Remote:
        """创建Web驱动"""
        browser_type = self.browser_config.get('type', 'chrome').lower()
        headless = self.browser_config.get('headless', True)
        
        if browser_type == 'chrome':
            options = ChromeOptions()
            if headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            return webdriver.Chrome(options=options)
        elif browser_type == 'firefox':
            options = FirefoxOptions()
            if headless:
                options.add_argument('--headless')
            return webdriver.Firefox(options=options)
        else:
            raise ValueError(f"不支持的浏览器类型: {browser_type}")
    
    def _execute_web_step(self, driver: webdriver.Remote, step: Dict[str, Any], step_num: int) -> Dict[str, Any]:
        """执行Web测试步骤"""
        try:
            action = step.get('action', '')
            locator = step.get('locator', {})
            value = step.get('value', '')
            timeout = step.get('timeout', 10)
            
            # 查找元素
            element = None
            if locator:
                by_type = locator.get('by', 'id')
                by_value = locator.get('value', '')
                
                by_mapping = {
                    'id': By.ID,
                    'name': By.NAME,
                    'class': By.CLASS_NAME,
                    'tag': By.TAG_NAME,
                    'xpath': By.XPATH,
                    'css': By.CSS_SELECTOR,
                    'link_text': By.LINK_TEXT,
                    'partial_link_text': By.PARTIAL_LINK_TEXT
                }
                
                by = by_mapping.get(by_type, By.ID)
                
                try:
                    element = WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((by, by_value))
                    )
                except TimeoutException:
                    return {
                        'success': False,
                        'message': f'元素定位超时: {by_type}={by_value}',
                        'step_num': step_num
                    }
            
            # 执行操作
            if action == 'open':
                driver.get(value)
            elif action == 'click' and element:
                element.click()
            elif action == 'input' and element:
                element.clear()
                element.send_keys(value)
            elif action == 'select' and element:
                from selenium.webdriver.support.ui import Select
                select = Select(element)
                select.select_by_visible_text(value)
            elif action == 'wait':
                time.sleep(float(value))
            elif action == 'assert_text' and element:
                actual_text = element.text
                if value not in actual_text:
                    return {
                        'success': False,
                        'message': f'文本断言失败，期望包含: {value}, 实际: {actual_text}',
                        'step_num': step_num
                    }
            elif action == 'assert_title':
                actual_title = driver.title
                if value not in actual_title:
                    return {
                        'success': False,
                        'message': f'标题断言失败，期望包含: {value}, 实际: {actual_title}',
                        'step_num': step_num
                    }
            else:
                return {
                    'success': False,
                    'message': f'不支持的操作: {action}',
                    'step_num': step_num
                }
            
            return {
                'success': True,
                'message': f'步骤 {step_num} 执行成功',
                'step_num': step_num
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'步骤执行异常: {str(e)}',
                'step_num': step_num
            }
    
    def _parse_test_steps(self, test_steps: str) -> List[Dict[str, Any]]:
        """解析测试步骤"""
        try:
            if isinstance(test_steps, str):
                return json.loads(test_steps)
            elif isinstance(test_steps, list):
                return test_steps
            else:
                return []
        except:
            return []
    
    def _parse_api_config(self, test_steps: str) -> Dict[str, Any]:
        """解析API配置"""
        try:
            steps = self._parse_test_steps(test_steps)
            if steps and isinstance(steps[0], dict):
                return steps[0]
            return {}
        except:
            return {}
    
    def _parse_performance_config(self, test_steps: str) -> Dict[str, Any]:
        """解析性能测试配置"""
        try:
            steps = self._parse_test_steps(test_steps)
            if steps and isinstance(steps[0], dict):
                return steps[0]
            return {}
        except:
            return {}
    
    def _parse_script_config(self, test_steps: str) -> Dict[str, Any]:
        """解析脚本配置"""
        try:
            steps = self._parse_test_steps(test_steps)
            if steps and isinstance(steps[0], dict):
                return steps[0]
            return {}
        except:
            return {}
    
    def _validate_api_response(self, response: requests.Response, 
                             validations: Dict[str, Any]) -> Dict[str, Any]:
        """验证API响应"""
        try:
            # 状态码验证
            expected_status = validations.get('status_code')
            if expected_status and response.status_code != expected_status:
                return {
                    'success': False,
                    'message': f'状态码验证失败，期望: {expected_status}, 实际: {response.status_code}'
                }
            
            # 响应时间验证
            max_response_time = validations.get('max_response_time')
            if max_response_time and response.elapsed.total_seconds() > max_response_time:
                return {
                    'success': False,
                    'message': f'响应时间超限，期望: <{max_response_time}s, 实际: {response.elapsed.total_seconds()}s'
                }
            
            # 响应体验证
            body_validations = validations.get('body', {})
            if body_validations:
                try:
                    response_json = response.json()
                    for key, expected_value in body_validations.items():
                        if key not in response_json or response_json[key] != expected_value:
                            return {
                                'success': False,
                                'message': f'响应体验证失败，字段: {key}, 期望: {expected_value}, 实际: {response_json.get(key)}'
                            }
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'message': '响应体不是有效的JSON格式'
                    }
            
            # 头部验证
            header_validations = validations.get('headers', {})
            for header, expected_value in header_validations.items():
                actual_value = response.headers.get(header)
                if actual_value != expected_value:
                    return {
                        'success': False,
                        'message': f'响应头验证失败，头部: {header}, 期望: {expected_value}, 实际: {actual_value}'
                    }
            
            return {'success': True, 'message': '所有验证通过'}
            
        except Exception as e:
            return {'success': False, 'message': f'验证过程异常: {str(e)}'}
    
    def _send_performance_request(self, url: str) -> Dict[str, Any]:
        """发送性能测试请求"""
        try:
            start_time = time.time()
            response = requests.get(url, timeout=5)
            response_time = time.time() - start_time
            
            return {
                'success': response.status_code == 200,
                'response_time': response_time,
                'status_code': response.status_code
            }
        except Exception as e:
            return {
                'success': False,
                'response_time': 0,
                'error': str(e)
            }
    
    def _execute_python_script(self, script_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行Python脚本"""
        try:
            script_content = script_config.get('script', '')
            if not script_content:
                return {'result': 'failed', 'message': 'Python脚本内容为空'}
            
            # 创建临时脚本文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_file = f.name
            
            try:
                # 执行脚本
                result = subprocess.run(
                    ['python', script_file],
                    capture_output=True,
                    text=True,
                    timeout=script_config.get('timeout', 60)
                )
                
                if result.returncode == 0:
                    return {
                        'result': 'passed',
                        'message': 'Python脚本执行成功',
                        'details': {
                            'stdout': result.stdout,
                            'stderr': result.stderr,
                            'returncode': result.returncode
                        }
                    }
                else:
                    return {
                        'result': 'failed',
                        'message': 'Python脚本执行失败',
                        'details': {
                            'stdout': result.stdout,
                            'stderr': result.stderr,
                            'returncode': result.returncode
                        }
                    }
            finally:
                # 清理临时文件
                try:
                    os.unlink(script_file)
                except:
                    pass
            
        except subprocess.TimeoutExpired:
            return {'result': 'failed', 'message': 'Python脚本执行超时'}
        except Exception as e:
            return {'result': 'failed', 'message': f'Python脚本执行异常: {str(e)}'}
    
    def _execute_shell_script(self, script_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行Shell脚本"""
        try:
            script_content = script_config.get('script', '')
            if not script_content:
                return {'result': 'failed', 'message': 'Shell脚本内容为空'}
            
            # 执行脚本
            result = subprocess.run(
                script_content,
                shell=True,
                capture_output=True,
                text=True,
                timeout=script_config.get('timeout', 60)
            )
            
            if result.returncode == 0:
                return {
                    'result': 'passed',
                    'message': 'Shell脚本执行成功',
                    'details': {
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    }
                }
            else:
                return {
                    'result': 'failed',
                    'message': 'Shell脚本执行失败',
                    'details': {
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    }
                }
            
        except subprocess.TimeoutExpired:
            return {'result': 'failed', 'message': 'Shell脚本执行超时'}
        except Exception as e:
            return {'result': 'failed', 'message': f'Shell脚本执行异常: {str(e)}'}
    
    def _update_execution_status(self, execution_id: int, status: str):
        """更新执行状态"""
        try:
            execution = TestExecution.query.get(execution_id)
            if execution:
                execution.status = status
                execution.updated_at = datetime.now()
                db.session.commit()
        except Exception as e:
            logger.error(f"更新执行状态失败: {e}")
    
    def _update_execution_result(self, execution_id: int, result: Dict[str, Any]):
        """更新执行结果"""
        try:
            execution = TestExecution.query.get(execution_id)
            if execution:
                execution.status = 'completed'
                execution.result = result.get('result', 'failed')
                execution.execution_time = result.get('execution_time', 0)
                execution.error_message = result.get('message', '')
                execution.execution_details = json.dumps(result.get('details', {}), ensure_ascii=False)
                execution.updated_at = datetime.now()
                db.session.commit()
        except Exception as e:
            logger.error(f"更新执行结果失败: {e}")
    
    def _update_execution_ai_analysis(self, execution_id: int, ai_analysis: Dict[str, Any]):
        """更新AI分析结果"""
        try:
            execution = TestExecution.query.get(execution_id)
            if execution:
                execution.ai_analysis_result = json.dumps(ai_analysis, ensure_ascii=False)
                execution.updated_at = datetime.now()
                db.session.commit()
        except Exception as e:
            logger.error(f"更新AI分析结果失败: {e}")
    
    def stop_execution(self, execution_id: int) -> bool:
        """停止执行"""
        try:
            if execution_id in self.running_executions:
                future = self.running_executions[execution_id]
                future.cancel()
                del self.running_executions[execution_id]
                
                # 更新执行状态
                self._update_execution_status(execution_id, 'cancelled')
                return True
            return False
        except Exception as e:
            logger.error(f"停止执行失败: {e}")
            return False
    
    def get_execution_status(self, execution_id: int) -> Dict[str, Any]:
        """获取执行状态"""
        try:
            execution = TestExecution.query.get(execution_id)
            if execution:
                return {
                    'id': execution.id,
                    'status': execution.status,
                    'result': execution.result,
                    'execution_time': execution.execution_time,
                    'error_message': execution.error_message,
                    'created_at': execution.created_at.isoformat() if execution.created_at else None,
                    'updated_at': execution.updated_at.isoformat() if execution.updated_at else None
                }
            return {}
        except Exception as e:
            logger.error(f"获取执行状态失败: {e}")
            return {}
    
    def cleanup(self):
        """清理资源"""
        try:
            self.executor.shutdown(wait=True)
        except Exception as e:
            logger.error(f"清理资源失败: {e}")