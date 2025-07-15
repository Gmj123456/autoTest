#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试用例管理视图模块
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.models import db, Project, Module, TestCase, TestExecution
from app.services.ai_service import AIService
from loguru import logger
import json

testcase_bp = Blueprint('testcase', __name__)

@testcase_bp.route('/')
def index():
    """测试用例列表页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        project_id = request.args.get('project_id', type=int)
        module_id = request.args.get('module_id', type=int)
        priority = request.args.get('priority', '')
        status = request.args.get('status', '')
        case_type = request.args.get('type', '')
        
        query = TestCase.query
        
        # 项目过滤
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        # 模块过滤
        if module_id:
            query = query.filter_by(module_id=module_id)
        
        # 搜索过滤
        if search:
            query = query.filter(
                db.or_(
                    TestCase.title.contains(search),
                    TestCase.description.contains(search),
                    TestCase.tags.contains(search)
                )
            )
        
        # 优先级过滤
        if priority:
            query = query.filter_by(priority=priority)
        
        # 状态过滤
        if status:
            query = query.filter_by(status=status)
        
        # 类型过滤
        if case_type:
            query = query.filter_by(type=case_type)
        
        # 分页
        testcases = query.order_by(TestCase.updated_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取项目和模块列表用于过滤
        projects = Project.query.filter_by(status='active').all()
        modules = Module.query.all() if not project_id else Module.query.filter_by(project_id=project_id).all()
        
        return render_template('testcase/index.html',
                             testcases=testcases,
                             projects=projects,
                             modules=modules,
                             search=search,
                             project_id=project_id,
                             module_id=module_id,
                             priority=priority,
                             status=status,
                             case_type=case_type)
    except Exception as e:
        logger.error(f"测试用例列表加载失败: {e}")
        flash('测试用例列表加载失败', 'error')
        return render_template('testcase/index.html', testcases=None)

@testcase_bp.route('/create', methods=['GET', 'POST'])
def create():
    """创建测试用例"""
    if request.method == 'GET':
        project_id = request.args.get('project_id', type=int)
        module_id = request.args.get('module_id', type=int)
        
        projects = Project.query.filter_by(status='active').all()
        modules = Module.query.filter_by(project_id=project_id).all() if project_id else []
        
        return render_template('testcase/create.html',
                             projects=projects,
                             modules=modules,
                             selected_project_id=project_id,
                             selected_module_id=module_id)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('title'):
            return jsonify({'success': False, 'message': '用例标题不能为空'}), 400
        
        if not data.get('project_id'):
            return jsonify({'success': False, 'message': '请选择项目'}), 400
        
        # 处理测试步骤
        steps = []
        if data.get('steps'):
            if isinstance(data['steps'], str):
                try:
                    steps = json.loads(data['steps'])
                except:
                    steps = [{'step': data['steps'], 'expected': ''}]
            else:
                steps = data['steps']
        
        # 创建测试用例
        testcase = TestCase(
            title=data['title'],
            description=data.get('description', ''),
            precondition=data.get('precondition', ''),
            expected_result=data.get('expected_result', ''),
            priority=data.get('priority', 'medium'),
            type=data.get('type', 'functional'),
            status='active',
            tags=data.get('tags', ''),
            project_id=data['project_id'],
            module_id=data.get('module_id'),
            creator=data.get('creator', ''),
            ai_generated=data.get('ai_generated', False),
            ai_confidence=data.get('ai_confidence')
        )
        
        testcase.set_steps(steps)
        testcase.save()
        
        logger.info(f"测试用例创建成功: {testcase.title}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': '测试用例创建成功',
                'data': testcase.to_dict()
            })
        else:
            flash('测试用例创建成功', 'success')
            return redirect(url_for('testcase.detail', id=testcase.id))
            
    except Exception as e:
        logger.error(f"测试用例创建失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('测试用例创建失败', 'error')
            return redirect(url_for('testcase.create'))

@testcase_bp.route('/<int:id>')
def detail(id):
    """测试用例详情页面"""
    try:
        testcase = TestCase.query.get_or_404(id)
        
        # 获取测试步骤
        steps = testcase.get_steps()
        
        # 获取执行历史
        executions = TestExecution.query.filter_by(testcase_id=id).order_by(
            TestExecution.created_at.desc()
        ).limit(10).all()
        
        # 获取执行统计
        total_executions = TestExecution.query.filter_by(testcase_id=id).count()
        passed_executions = TestExecution.query.filter_by(testcase_id=id, result='passed').count()
        failed_executions = TestExecution.query.filter_by(testcase_id=id, result='failed').count()
        
        pass_rate = (passed_executions / total_executions * 100) if total_executions > 0 else 0
        
        execution_stats = {
            'total': total_executions,
            'passed': passed_executions,
            'failed': failed_executions,
            'pass_rate': round(pass_rate, 2)
        }
        
        return render_template('testcase/detail.html',
                             testcase=testcase,
                             steps=steps,
                             executions=executions,
                             execution_stats=execution_stats)
    except Exception as e:
        logger.error(f"测试用例详情加载失败: {e}")
        flash('测试用例详情加载失败', 'error')
        return redirect(url_for('testcase.index'))

@testcase_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """编辑测试用例"""
    testcase = TestCase.query.get_or_404(id)
    
    if request.method == 'GET':
        projects = Project.query.filter_by(status='active').all()
        modules = Module.query.filter_by(project_id=testcase.project_id).all()
        steps = testcase.get_steps()
        
        return render_template('testcase/edit.html',
                             testcase=testcase,
                             projects=projects,
                             modules=modules,
                             steps=steps)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('title'):
            return jsonify({'success': False, 'message': '用例标题不能为空'}), 400
        
        # 处理测试步骤
        steps = []
        if data.get('steps'):
            if isinstance(data['steps'], str):
                try:
                    steps = json.loads(data['steps'])
                except:
                    steps = [{'step': data['steps'], 'expected': ''}]
            else:
                steps = data['steps']
        
        # 更新测试用例
        testcase.title = data['title']
        testcase.description = data.get('description', '')
        testcase.precondition = data.get('precondition', '')
        testcase.expected_result = data.get('expected_result', '')
        testcase.priority = data.get('priority', 'medium')
        testcase.type = data.get('type', 'functional')
        testcase.status = data.get('status', 'active')
        testcase.tags = data.get('tags', '')
        testcase.module_id = data.get('module_id')
        
        testcase.set_steps(steps)
        testcase.save()
        
        logger.info(f"测试用例更新成功: {testcase.title}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': '测试用例更新成功',
                'data': testcase.to_dict()
            })
        else:
            flash('测试用例更新成功', 'success')
            return redirect(url_for('testcase.detail', id=testcase.id))
            
    except Exception as e:
        logger.error(f"测试用例更新失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('测试用例更新失败', 'error')
            return render_template('testcase/edit.html', testcase=testcase)

@testcase_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """删除测试用例"""
    try:
        testcase = TestCase.query.get_or_404(id)
        testcase_title = testcase.title
        
        # 检查是否有执行记录
        execution_count = TestExecution.query.filter_by(testcase_id=id).count()
        if execution_count > 0:
            return jsonify({
                'success': False,
                'message': f'该测试用例有 {execution_count} 条执行记录，无法删除'
            }), 400
        
        # 删除测试用例
        testcase.delete()
        
        logger.info(f"测试用例删除成功: {testcase_title}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': '测试用例删除成功'
            })
        else:
            flash('测试用例删除成功', 'success')
            return redirect(url_for('testcase.index'))
            
    except Exception as e:
        logger.error(f"测试用例删除失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('测试用例删除失败', 'error')
            return redirect(url_for('testcase.index'))

@testcase_bp.route('/<int:id>/copy', methods=['POST'])
def copy(id):
    """复制测试用例"""
    try:
        original = TestCase.query.get_or_404(id)
        
        # 创建副本
        testcase = TestCase(
            title=f"{original.title} - 副本",
            description=original.description,
            precondition=original.precondition,
            steps=original.steps,
            expected_result=original.expected_result,
            priority=original.priority,
            type=original.type,
            status='active',
            tags=original.tags,
            project_id=original.project_id,
            module_id=original.module_id,
            creator=request.form.get('creator', ''),
            ai_generated=False
        )
        
        testcase.save()
        
        logger.info(f"测试用例复制成功: {testcase.title}")
        
        return jsonify({
            'success': True,
            'message': '测试用例复制成功',
            'data': testcase.to_dict()
        })
        
    except Exception as e:
        logger.error(f"测试用例复制失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@testcase_bp.route('/ai/generate', methods=['POST'])
def ai_generate():
    """AI生成测试用例"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('project_id'):
            return jsonify({'success': False, 'message': '请选择项目'}), 400
        
        if not data.get('requirement'):
            return jsonify({'success': False, 'message': '请输入需求描述'}), 400
        
        # 调用AI服务生成测试用例
        ai_service = AIService()
        result = ai_service.generate_testcases(
            requirement=data['requirement'],
            project_id=data['project_id'],
            module_id=data.get('module_id'),
            case_type=data.get('type', 'functional'),
            priority=data.get('priority', 'medium')
        )
        
        if result['success']:
            # 保存生成的测试用例
            saved_cases = []
            for case_data in result['testcases']:
                testcase = TestCase(
                    title=case_data['title'],
                    description=case_data['description'],
                    precondition=case_data.get('precondition', ''),
                    expected_result=case_data.get('expected_result', ''),
                    priority=case_data.get('priority', 'medium'),
                    type=case_data.get('type', 'functional'),
                    status='active',
                    tags=case_data.get('tags', ''),
                    project_id=data['project_id'],
                    module_id=data.get('module_id'),
                    creator=data.get('creator', 'AI'),
                    ai_generated=True,
                    ai_confidence=case_data.get('confidence', 0.8)
                )
                
                testcase.set_steps(case_data.get('steps', []))
                testcase.save()
                saved_cases.append(testcase.to_dict())
            
            logger.info(f"AI生成测试用例成功: {len(saved_cases)} 个")
            
            return jsonify({
                'success': True,
                'message': f'AI成功生成 {len(saved_cases)} 个测试用例',
                'data': saved_cases
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI生成失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI生成测试用例失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@testcase_bp.route('/ai/enhance', methods=['POST'])
def ai_enhance():
    """AI增强测试用例"""
    try:
        data = request.get_json()
        testcase_id = data.get('testcase_id')
        
        if not testcase_id:
            return jsonify({'success': False, 'message': '请选择测试用例'}), 400
        
        testcase = TestCase.query.get_or_404(testcase_id)
        
        # 调用AI服务增强测试用例
        ai_service = AIService()
        result = ai_service.enhance_testcase(testcase)
        
        if result['success']:
            # 更新测试用例
            enhanced_data = result['enhanced_testcase']
            
            if enhanced_data.get('steps'):
                testcase.set_steps(enhanced_data['steps'])
            
            if enhanced_data.get('expected_result'):
                testcase.expected_result = enhanced_data['expected_result']
            
            if enhanced_data.get('precondition'):
                testcase.precondition = enhanced_data['precondition']
            
            testcase.save()
            
            logger.info(f"AI增强测试用例成功: {testcase.title}")
            
            return jsonify({
                'success': True,
                'message': 'AI增强测试用例成功',
                'data': testcase.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'AI增强失败')
            }), 500
            
    except Exception as e:
        logger.error(f"AI增强测试用例失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@testcase_bp.route('/api/modules/<int:project_id>')
def api_get_modules(project_id):
    """获取项目下的模块列表API"""
    try:
        modules = Module.query.filter_by(project_id=project_id).all()
        return jsonify({
            'success': True,
            'data': [module.to_dict() for module in modules]
        })
    except Exception as e:
        logger.error(f"获取模块列表失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500