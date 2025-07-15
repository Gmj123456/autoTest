#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bug管理视图模块
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from app.models import db, Project, TestCase, TestExecution, Bug
from app.services.ai_service import AIService
from loguru import logger
import json
import os

bug_bp = Blueprint('bug', __name__)

@bug_bp.route('/')
def index():
    """Bug列表页面"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        project_id = request.args.get('project_id', type=int)
        status = request.args.get('status', '')
        severity = request.args.get('severity', '')
        priority = request.args.get('priority', '')
        
        query = Bug.query
        
        # 项目过滤
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        # 搜索过滤
        if search:
            query = query.filter(
                db.or_(
                    Bug.title.contains(search),
                    Bug.description.contains(search),
                    Bug.reporter.contains(search),
                    Bug.assignee.contains(search)
                )
            )
        
        # 状态过滤
        if status:
            query = query.filter_by(status=status)
        
        # 严重程度过滤
        if severity:
            query = query.filter_by(severity=severity)
        
        # 优先级过滤
        if priority:
            query = query.filter_by(priority=priority)
        
        # 分页
        bugs = query.order_by(Bug.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取项目列表用于过滤
        projects = Project.query.filter_by(status='active').all()
        
        # 获取配置中的状态和级别选项
        config = current_app.config.get('YAML_CONFIG', {})
        bug_config = config.get('bug', {})
        severity_levels = bug_config.get('severity_levels', ['低', '中', '高', '严重'])
        status_flow = bug_config.get('status_flow', ['新建', '已分配', '处理中', '已解决', '已关闭'])
        
        return render_template('bug/index.html',
                             bugs=bugs,
                             projects=projects,
                             severity_levels=severity_levels,
                             status_flow=status_flow,
                             search=search,
                             project_id=project_id,
                             status=status,
                             severity=severity,
                             priority=priority)
    except Exception as e:
        logger.error(f"Bug列表加载失败: {e}")
        flash('Bug列表加载失败', 'error')
        return render_template('bug/index.html', bugs=None)

@bug_bp.route('/create', methods=['GET', 'POST'])
def create():
    """创建Bug"""
    if request.method == 'GET':
        project_id = request.args.get('project_id', type=int)
        testcase_id = request.args.get('testcase_id', type=int)
        execution_id = request.args.get('execution_id', type=int)
        
        projects = Project.query.filter_by(status='active').all()
        testcases = TestCase.query.filter_by(project_id=project_id).all() if project_id else []
        
        # 获取配置中的选项
        config = current_app.config.get('YAML_CONFIG', {})
        bug_config = config.get('bug', {})
        severity_levels = bug_config.get('severity_levels', ['低', '中', '高', '严重'])
        status_flow = bug_config.get('status_flow', ['新建', '已分配', '处理中', '已解决', '已关闭'])
        
        return render_template('bug/create.html',
                             projects=projects,
                             testcases=testcases,
                             severity_levels=severity_levels,
                             status_flow=status_flow,
                             selected_project_id=project_id,
                             selected_testcase_id=testcase_id,
                             selected_execution_id=execution_id)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('title'):
            return jsonify({'success': False, 'message': 'Bug标题不能为空'}), 400
        
        if not data.get('project_id'):
            return jsonify({'success': False, 'message': '请选择项目'}), 400
        
        # 创建Bug
        bug = Bug(
            title=data['title'],
            description=data.get('description', ''),
            severity=data.get('severity', 'medium'),
            priority=data.get('priority', 'medium'),
            status=data.get('status', 'new'),
            type=data.get('type', ''),
            project_id=data['project_id'],
            testcase_id=data.get('testcase_id'),
            execution_id=data.get('execution_id'),
            reporter=data.get('reporter', ''),
            assignee=data.get('assignee', ''),
            steps_to_reproduce=data.get('steps_to_reproduce', ''),
            environment_info=data.get('environment_info', '')
        )
        
        bug.save()
        
        logger.info(f"Bug创建成功: {bug.title}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Bug创建成功',
                'data': bug.to_dict()
            })
        else:
            flash('Bug创建成功', 'success')
            return redirect(url_for('bug.detail', id=bug.id))
            
    except Exception as e:
        logger.error(f"Bug创建失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('Bug创建失败', 'error')
            return redirect(url_for('bug.create'))

@bug_bp.route('/<int:id>')
def detail(id):
    """Bug详情页面"""
    try:
        bug = Bug.query.get_or_404(id)
        
        # 获取附件列表
        attachments = bug.get_attachments()
        
        # 获取相似Bug列表
        similar_bugs_data = bug.get_similar_bugs()
        similar_bugs = []
        for similar_data in similar_bugs_data:
            similar_bug = Bug.query.get(similar_data.get('id'))
            if similar_bug:
                similar_bugs.append({
                    'bug': similar_bug,
                    'similarity': similar_data.get('similarity', 0)
                })
        
        # 获取关联的测试用例和执行记录
        testcase = bug.testcase if bug.testcase_id else None
        execution = bug.execution if bug.execution_id else None
        
        return render_template('bug/detail.html',
                             bug=bug,
                             attachments=attachments,
                             similar_bugs=similar_bugs,
                             testcase=testcase,
                             execution=execution)
    except Exception as e:
        logger.error(f"Bug详情加载失败: {e}")
        flash('Bug详情加载失败', 'error')
        return redirect(url_for('bug.index'))

@bug_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """编辑Bug"""
    bug = Bug.query.get_or_404(id)
    
    if request.method == 'GET':
        projects = Project.query.filter_by(status='active').all()
        testcases = TestCase.query.filter_by(project_id=bug.project_id).all()
        
        # 获取配置中的选项
        config = current_app.config.get('YAML_CONFIG', {})
        bug_config = config.get('bug', {})
        severity_levels = bug_config.get('severity_levels', ['低', '中', '高', '严重'])
        status_flow = bug_config.get('status_flow', ['新建', '已分配', '处理中', '已解决', '已关闭'])
        
        return render_template('bug/edit.html',
                             bug=bug,
                             projects=projects,
                             testcases=testcases,
                             severity_levels=severity_levels,
                             status_flow=status_flow)
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        # 验证必填字段
        if not data.get('title'):
            return jsonify({'success': False, 'message': 'Bug标题不能为空'}), 400
        
        # 更新Bug信息
        bug.title = data['title']
        bug.description = data.get('description', '')
        bug.severity = data.get('severity', 'medium')
        bug.priority = data.get('priority', 'medium')
        bug.status = data.get('status', 'new')
        bug.type = data.get('type', '')
        bug.testcase_id = data.get('testcase_id')
        bug.assignee = data.get('assignee', '')
        bug.steps_to_reproduce = data.get('steps_to_reproduce', '')
        bug.environment_info = data.get('environment_info', '')
        
        bug.save()
        
        logger.info(f"Bug更新成功: {bug.title}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Bug更新成功',
                'data': bug.to_dict()
            })
        else:
            flash('Bug更新成功', 'success')
            return redirect(url_for('bug.detail', id=bug.id))
            
    except Exception as e:
        logger.error(f"Bug更新失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('Bug更新失败', 'error')
            return render_template('bug/edit.html', bug=bug)

@bug_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """删除Bug"""
    try:
        bug = Bug.query.get_or_404(id)
        bug_title = bug.title
        
        # 删除Bug
        bug.delete()
        
        logger.info(f"Bug删除成功: {bug_title}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Bug删除成功'
            })
        else:
            flash('Bug删除成功', 'success')
            return redirect(url_for('bug.index'))
            
    except Exception as e:
        logger.error(f"Bug删除失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash('Bug删除失败', 'error')
            return redirect(url_for('bug.index'))

@bug_bp.route('/<int:id>/ai-analyze', methods=['POST'])
def ai_analyze(id):
    """AI分析Bug根因"""
    try:
        bug = Bug.query.get_or_404(id)
        
        # 调用AI服务分析Bug
        ai_service = AIService()
        result = ai_service.analyze_bug_root_cause(bug)
        
        if result['success']:
            # 保存分析结果
            analysis = result['analysis']
            bug.ai_root_cause = analysis.get('root_cause', '')
            bug.ai_fix_suggestion = analysis.get('fix_suggestion', '')
            bug.save()
            
            logger.info(f"AI分析Bug完成: {bug.title}")
            
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
        logger.error(f"AI分析Bug失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bug_bp.route('/<int:id>/find-similar', methods=['POST'])
def find_similar(id):
    """查找相似Bug"""
    try:
        bug = Bug.query.get_or_404(id)
        
        # 调用AI服务查找相似Bug
        ai_service = AIService()
        result = ai_service.find_similar_bugs(bug)
        
        if result['success']:
            # 保存相似Bug列表
            similar_bugs = result['similar_bugs']
            bug.set_similar_bugs(similar_bugs)
            
            # 计算最高相似度
            if similar_bugs:
                max_similarity = max(item.get('similarity', 0) for item in similar_bugs)
                bug.ai_similarity_score = max_similarity
            
            bug.save()
            
            logger.info(f"查找相似Bug完成: {bug.title}")
            
            return jsonify({
                'success': True,
                'message': f'找到 {len(similar_bugs)} 个相似Bug',
                'data': similar_bugs
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '查找相似Bug失败')
            }), 500
            
    except Exception as e:
        logger.error(f"查找相似Bug失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bug_bp.route('/<int:id>/upload-attachment', methods=['POST'])
def upload_attachment(id):
    """上传Bug附件"""
    try:
        bug = Bug.query.get_or_404(id)
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择文件'}), 400
        
        # 检查文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'log', 'zip'}
        if not ('.' in file.filename and 
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'success': False, 'message': '不支持的文件类型'}), 400
        
        # 保存文件
        upload_folder = current_app.config['UPLOAD_FOLDER']
        bug_folder = os.path.join(upload_folder, 'bugs', str(bug.id))
        os.makedirs(bug_folder, exist_ok=True)
        
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        file_path = os.path.join(bug_folder, filename)
        file.save(file_path)
        
        # 添加到Bug附件列表
        relative_path = os.path.relpath(file_path, upload_folder)
        bug.add_attachment(relative_path)
        bug.save()
        
        logger.info(f"Bug附件上传成功: {bug.title} - {filename}")
        
        return jsonify({
            'success': True,
            'message': '附件上传成功',
            'data': {
                'filename': filename,
                'path': relative_path
            }
        })
        
    except Exception as e:
        logger.error(f"Bug附件上传失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bug_bp.route('/<int:id>/status/<status>', methods=['POST'])
def update_status(id, status):
    """更新Bug状态"""
    try:
        bug = Bug.query.get_or_404(id)
        
        # 验证状态值
        config = current_app.config.get('YAML_CONFIG', {})
        bug_config = config.get('bug', {})
        valid_statuses = bug_config.get('status_flow', ['新建', '已分配', '处理中', '已解决', '已关闭'])
        
        if status not in valid_statuses:
            return jsonify({'success': False, 'message': '无效的状态值'}), 400
        
        old_status = bug.status
        bug.status = status
        bug.save()
        
        logger.info(f"Bug状态更新: {bug.title} {old_status} -> {status}")
        
        return jsonify({
            'success': True,
            'message': f'Bug状态已更新为: {status}',
            'data': {
                'old_status': old_status,
                'new_status': status
            }
        })
        
    except Exception as e:
        logger.error(f"Bug状态更新失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bug_bp.route('/api/testcases/<int:project_id>')
def api_get_testcases(project_id):
    """获取项目下的测试用例列表API"""
    try:
        testcases = TestCase.query.filter_by(project_id=project_id).all()
        return jsonify({
            'success': True,
            'data': [{
                'id': tc.id,
                'title': tc.title,
                'module_name': tc.module.name if tc.module else ''
            } for tc in testcases]
        })
    except Exception as e:
        logger.error(f"获取测试用例列表失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bug_bp.route('/statistics')
def statistics():
    """Bug统计页面"""
    try:
        # 获取统计数据
        stats = get_bug_statistics()
        
        return render_template('bug/statistics.html', stats=stats)
    except Exception as e:
        logger.error(f"Bug统计页面加载失败: {e}")
        flash('Bug统计页面加载失败', 'error')
        return redirect(url_for('bug.index'))

def get_bug_statistics():
    """获取Bug统计数据"""
    # 总体统计
    total_bugs = Bug.query.count()
    open_bugs = Bug.query.filter(Bug.status.in_(['新建', '已分配', '处理中'])).count()
    resolved_bugs = Bug.query.filter_by(status='已解决').count()
    closed_bugs = Bug.query.filter_by(status='已关闭').count()
    
    # 按严重程度统计
    severity_stats = db.session.query(
        Bug.severity,
        func.count(Bug.id).label('count')
    ).group_by(Bug.severity).all()
    
    # 按状态统计
    status_stats = db.session.query(
        Bug.status,
        func.count(Bug.id).label('count')
    ).group_by(Bug.status).all()
    
    # 按项目统计
    project_stats = db.session.query(
        Project.name,
        func.count(Bug.id).label('count')
    ).join(Bug).group_by(Project.name).all()
    
    # 按月份统计（最近12个月）
    monthly_stats = db.session.query(
        func.date_format(Bug.created_at, '%Y-%m').label('month'),
        func.count(Bug.id).label('count')
    ).filter(
        Bug.created_at >= func.date_sub(func.now(), text('INTERVAL 12 MONTH'))
    ).group_by('month').order_by('month').all()
    
    return {
        'total': {
            'total_bugs': total_bugs,
            'open_bugs': open_bugs,
            'resolved_bugs': resolved_bugs,
            'closed_bugs': closed_bugs,
            'resolution_rate': round((resolved_bugs + closed_bugs) / total_bugs * 100, 2) if total_bugs > 0 else 0
        },
        'severity': [{'name': item[0], 'value': item[1]} for item in severity_stats],
        'status': [{'name': item[0], 'value': item[1]} for item in status_stats],
        'project': [{'name': item[0], 'value': item[1]} for item in project_stats],
        'monthly': [{'month': item[0], 'count': item[1]} for item in monthly_stats]
    }