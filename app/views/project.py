#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目管理视图模块
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.models import db, Project, Module, TestCase, TestExecution, Bug
from sqlalchemy import func
from loguru import logger

project_bp = Blueprint('project', __name__)

@project_bp.route('/')
def index():
    """项目列表页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        
        query = Project.query
        
        # 搜索过滤
        if search:
            query = query.filter(
                db.or_(
                    Project.name.contains(search),
                    Project.description.contains(search),
                    Project.owner.contains(search)
                )
            )
        
        # 状态过滤
        if status:
            query = query.filter_by(status=status)
        
        # 分页
        projects = query.order_by(Project.updated_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取每个项目的统计信息
        for project in projects.items:
            project.stats = get_project_stats(project.id)
        
        return render_template('project/index.html', 
                             projects=projects,
                             search=search,
                             status=status)
    except Exception as e:
        logger.error(f"项目列表加载失败: {e}")
        flash('项目列表加载失败', 'error')
        return render_template('project/index.html', projects=None)

@project_bp.route('/create', methods=['GET', 'POST'])
def create():
    """创建项目"""
    if request.method == 'GET':
        return render_template('project/create.html')
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({'success': False, 'message': '项目名称不能为空'}), 400
        
        # 检查项目名称是否已存在
        existing = Project.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'success': False, 'message': '项目名称已存在'}), 400
        
        # 创建项目
        project = Project(
            name=data['name'],
            description=data.get('description', ''),
            owner=data.get('owner', ''),
            environment=data.get('environment', 'test'),
            base_url=data.get('base_url', ''),
            api_base_url=data.get('api_base_url', ''),
            status='active'
        )
        
        project.save()
        
        logger.info(f"项目创建成功: {project.name}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': '项目创建成功',
                'data': project.to_dict()
            })
        else:
            flash('项目创建成功', 'success')
            return redirect(url_for('project.detail', id=project.id))
            
    except Exception as e:
        logger.error(f"项目创建失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('项目创建失败', 'error')
            return render_template('project/create.html')

@project_bp.route('/<int:id>')
def detail(id):
    """项目详情页面"""
    try:
        project = Project.query.get_or_404(id)
        
        # 获取项目统计信息
        stats = get_project_stats(id)
        
        # 获取模块树
        modules = get_module_tree(id)
        
        # 获取最近的测试执行
        recent_executions = TestExecution.query.filter_by(project_id=id).order_by(
            TestExecution.created_at.desc()
        ).limit(10).all()
        
        # 获取最近的Bug
        recent_bugs = Bug.query.filter_by(project_id=id).order_by(
            Bug.created_at.desc()
        ).limit(10).all()
        
        return render_template('project/detail.html',
                             project=project,
                             stats=stats,
                             modules=modules,
                             recent_executions=recent_executions,
                             recent_bugs=recent_bugs)
    except Exception as e:
        logger.error(f"项目详情加载失败: {e}")
        flash('项目详情加载失败', 'error')
        return redirect(url_for('project.index'))

@project_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """编辑项目"""
    project = Project.query.get_or_404(id)
    
    if request.method == 'GET':
        return render_template('project/edit.html', project=project)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({'success': False, 'message': '项目名称不能为空'}), 400
        
        # 检查项目名称是否已存在（排除当前项目）
        existing = Project.query.filter(
            Project.name == data['name'],
            Project.id != id
        ).first()
        if existing:
            return jsonify({'success': False, 'message': '项目名称已存在'}), 400
        
        # 更新项目信息
        project.name = data['name']
        project.description = data.get('description', '')
        project.owner = data.get('owner', '')
        project.environment = data.get('environment', 'test')
        project.base_url = data.get('base_url', '')
        project.api_base_url = data.get('api_base_url', '')
        project.status = data.get('status', 'active')
        
        project.save()
        
        logger.info(f"项目更新成功: {project.name}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': '项目更新成功',
                'data': project.to_dict()
            })
        else:
            flash('项目更新成功', 'success')
            return redirect(url_for('project.detail', id=project.id))
            
    except Exception as e:
        logger.error(f"项目更新失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('项目更新失败', 'error')
            return render_template('project/edit.html', project=project)

@project_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """删除项目"""
    try:
        project = Project.query.get_or_404(id)
        project_name = project.name
        
        # 删除项目（级联删除相关数据）
        project.delete()
        
        logger.info(f"项目删除成功: {project_name}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': '项目删除成功'
            })
        else:
            flash('项目删除成功', 'success')
            return redirect(url_for('project.index'))
            
    except Exception as e:
        logger.error(f"项目删除失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('项目删除失败', 'error')
            return redirect(url_for('project.index'))

@project_bp.route('/<int:id>/modules')
def modules(id):
    """项目模块管理页面"""
    try:
        project = Project.query.get_or_404(id)
        modules = get_module_tree(id)
        
        # 复用操作管理页面
        return render_template('project/modules.html',
                             project=project,
                             modules=modules)
    except Exception as e:
        logger.error(f"模块列表加载失败: {e}")
        flash('模块列表加载失败', 'error')
        return redirect(url_for('project.detail', id=id))


# 新增专门页面管理复用操作的接口示例
@project_bp.route('/<int:id>/manage', methods=['GET', 'POST'])
def manage_project(id):
    """专门页面管理复用操作"""
    try:
        project = Project.query.get_or_404(id)
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            action = data.get('action')
            if action == 'archive':
                project.status = 'archived'
                project.save()
                return jsonify({'success': True, 'message': '项目已归档'})
            elif action == 'activate':
                project.status = 'active'
                project.save()
                return jsonify({'success': True, 'message': '项目已激活'})
            else:
                return jsonify({'success': False, 'message': '未知操作'}), 400
        else:
            return render_template('project/manage.html', project=project)
    except Exception as e:
        logger.error(f"管理页面加载失败: {e}")
        flash('管理页面加载失败', 'error')
        return redirect(url_for('project.detail', id=id))


@project_bp.route('/<int:id>/modules/create', methods=['POST'])
def create_module(id):
    """创建模块"""
    try:
        project = Project.query.get_or_404(id)
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({'success': False, 'message': '模块名称不能为空'}), 400
        
        # 创建模块
        module = Module(
            name=data['name'],
            description=data.get('description', ''),
            project_id=id,
            parent_id=data.get('parent_id') if data.get('parent_id') else None
        )
        
        module.save()
        
        logger.info(f"模块创建成功: {module.name}")
        
        return jsonify({
            'success': True,
            'message': '模块创建成功',
            'data': module.to_dict()
        })
        
    except Exception as e:
        logger.error(f"模块创建失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@project_bp.route('/modules/<int:module_id>/edit', methods=['POST'])
def edit_module(module_id):
    """编辑模块"""
    try:
        module = Module.query.get_or_404(module_id)
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({'success': False, 'message': '模块名称不能为空'}), 400
        
        # 更新模块信息
        module.name = data['name']
        module.description = data.get('description', '')
        
        module.save()
        
        logger.info(f"模块更新成功: {module.name}")
        
        return jsonify({
            'success': True,
            'message': '模块更新成功',
            'data': module.to_dict()
        })
        
    except Exception as e:
        logger.error(f"模块更新失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@project_bp.route('/modules/<int:module_id>/delete', methods=['POST'])
def delete_module(module_id):
    """删除模块"""
    try:
        module = Module.query.get_or_404(module_id)
        module_name = module.name
        
        # 检查是否有子模块
        if module.children.count() > 0:
            return jsonify({'success': False, 'message': '该模块下还有子模块，无法删除'}), 400
        
        # 检查是否有测试用例
        if module.testcases.count() > 0:
            return jsonify({'success': False, 'message': '该模块下还有测试用例，无法删除'}), 400
        
        # 删除模块
        module.delete()
        
        logger.info(f"模块删除成功: {module_name}")
        
        return jsonify({
            'success': True,
            'message': '模块删除成功'
        })
        
    except Exception as e:
        logger.error(f"模块删除失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def get_project_stats(project_id):
    """获取项目统计信息"""
    # 模块统计
    total_modules = Module.query.filter_by(project_id=project_id).count()
    
    # 测试用例统计
    total_testcases = TestCase.query.filter_by(project_id=project_id).count()
    active_testcases = TestCase.query.filter_by(project_id=project_id, status='active').count()
    ai_generated_cases = TestCase.query.filter_by(project_id=project_id, ai_generated=True).count()
    
    # 测试执行统计
    total_executions = TestExecution.query.filter_by(project_id=project_id).count()
    passed_executions = TestExecution.query.filter_by(project_id=project_id, result='passed').count()
    failed_executions = TestExecution.query.filter_by(project_id=project_id, result='failed').count()
    
    # 计算通过率
    total_completed = passed_executions + failed_executions
    pass_rate = (passed_executions / total_completed * 100) if total_completed > 0 else 0
    
    # Bug统计
    total_bugs = Bug.query.filter_by(project_id=project_id).count()
    open_bugs = Bug.query.filter(
        Bug.project_id == project_id,
        Bug.status.in_(['new', 'assigned', 'in_progress'])
    ).count()
    
    return {
        'modules': total_modules,
        'testcases': {
            'total': total_testcases,
            'active': active_testcases,
            'ai_generated': ai_generated_cases
        },
        'executions': {
            'total': total_executions,
            'passed': passed_executions,
            'failed': failed_executions,
            'pass_rate': round(pass_rate, 2)
        },
        'bugs': {
            'total': total_bugs,
            'open': open_bugs
        }
    }

def get_module_tree(project_id):
    """获取项目的模块树结构"""
    # 获取所有模块
    modules = Module.query.filter_by(project_id=project_id).all()
    
    # 构建树结构
    module_dict = {module.id: module.to_dict() for module in modules}
    
    # 添加children字段
    for module in module_dict.values():
        module['children'] = []
        module['testcase_count'] = TestCase.query.filter_by(module_id=module['id']).count()
    
    # 构建父子关系
    root_modules = []
    for module in module_dict.values():
        if module['parent_id']:
            parent = module_dict.get(module['parent_id'])
            if parent:
                parent['children'].append(module)
        else:
            root_modules.append(module)
    
    return root_modules