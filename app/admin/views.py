#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/11/14 下午 07:54
# @Author  : gao
# @File    : views.py
import datetime
import os
import uuid
from functools import wraps

from flask import url_for, redirect, render_template, flash, session, request, abort
from werkzeug.utils import secure_filename

from app import db, app
from app.admin import admin
from app.admin.forms import LoginForm, TagForm, MovieForm, PreviewForm, PwdForm, AuthForm, RoleForm, AdminForm
from app.models import Admin, Tag, Movie, Preview, User, Comment, Moviecol, Oplog, Adminlog, Userlog, Auth, Role


# 上下文处理器,显示时间,请求时更新
@admin.context_processor
def tpl_extra():
    data = dict(
        online_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    return data


def admin_login_req(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if session.get('admin', None) is None:
            return redirect(url_for('admin.login', next=request.url))
        return func(*args, **kwargs)

    return decorated_function


def admin_auth(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        admin = Admin.query.join(
            Role
        ).filter(
            Role.id == Admin.role_id,
            Admin.id==session['admin_id']
        ).first()

        auths = admin.role.auths
        auths = list(map(lambda x: int(x), auths.split(',')))

        auth_list = Auth.query.all()
        urls = [v.url for v in auth_list for val in auths if val == v.id]
        rule = request.url_rule

        print(urls)
        print(rule)

        if str(rule) not in urls:
            abort(404)
        return func(*args, **kwargs)
    return decorated_function


def change_filename(filename):
    fileinfo = os.path.splitext(filename)
    filename = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(uuid.uuid4().hex) + fileinfo[-1]
    return filename


@admin.route('/')
@admin_login_req
# @admin_auth
def index():
    return render_template('admin/index.html')


@admin.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        data = form.data
        admin = Admin.query.filter_by(name=data['account']).first()
        if not admin.check_pwd(data['pwd']):
            flash("账号或密码错误! ", 'error')
            return redirect(url_for('admin.login'))
        session['admin'] = data['account']
        session['admin_id'] = admin.id

        adminlog = Adminlog(
            admin_id=admin.id,
            ip=request.remote_addr,
        )
        db.session.add(adminlog)
        db.session.commit()
        return redirect((request.args.get('next') or url_for('admin.index')))
    return render_template('admin/login.html', form=form)


@admin.route('/logout/')
@admin_login_req
def logout():
    session.pop('admin')
    session.pop('admin_id')
    return redirect(url_for('admin.login'))


@admin.route('/pwd/', methods=['GET', 'POST'])
@admin_login_req
def pwd():
    form = PwdForm()
    if form.validate_on_submit():
        data = form.data
        admin = Admin.query.filter_by(name=session['admin']).first()

        from werkzeug.security import generate_password_hash
        admin.pwd = generate_password_hash(data['new_pwd'])

        db.session.add(admin)
        db.session.commit()

        flash("密码修改成功,请重新登录!", 'info')
        return redirect(url_for('admin.logout'))
    return render_template('admin/pwd.html', form=form)


@admin.route('/tag/add/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def tag_add():
    form = TagForm()
    if form.validate_on_submit():
        data = form.data
        tag = Tag.query.filter_by(name=data['name']).count()
        if tag == 1:
            flash("标签已存在!", 'error')
            return redirect(url_for('admin.tag_add'))
        tag = Tag(
            name=data['name']
        )
        db.session.add(tag)
        db.session.commit()
        flash("标签添加成功!", 'info')

        oplog = Oplog(
            admin_id=session['admin_id'],
            ip=request.remote_addr,
            reason='添加标签< {} >'.format(data['name'])
        )

        db.session.add(oplog)
        db.session.commit()
        return redirect(url_for('admin.tag_add'))
    return render_template('admin/tag_add.html', form=form)


@admin.route('/tag/list/<int:page>/')
@admin_login_req
# @admin_auth
def tag_list(page=1):
    if page <= 0:
        page = 1
    page_data = Tag.query.order_by(
        Tag.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/tag_list.html', page_data=page_data)


@admin.route('/tag/del/<int:id>/')
@admin_login_req
# @admin_auth
def tag_del(id=None):
    tag = Tag.query.filter_by(id=id).first_or_404()
    db.session.delete(tag)
    db.session.commit()
    flash('删除标签成功!', 'info')
    return redirect(url_for('admin.tag_list', page=1))


@admin.route('/tag/edit/<int:id>/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def tag_edit(id=None):
    form = TagForm()
    tag = Tag.query.get_or_404(id)
    if form.validate_on_submit():
        data = form.data
        tag_count = Tag.query.filter_by(name=data['name']).count()
        if tag.name != data['name'] and tag_count == 1:
            flash("标签已存在!", 'error')
            return redirect(url_for('admin.tag_edit', id=id))
        tag.name = data['name']
        db.session.add(tag)
        db.session.commit()
        flash("标签修改成功!", 'info')
        return redirect(url_for('admin.tag_list', page=1))
    return render_template('admin/tag_edit.html', form=form, tag=tag)


@admin.route('/movie/add/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def movie_add():
    form = MovieForm()
    if form.validate_on_submit():
        data = form.data
        file_url = secure_filename(form.url.data.filename)
        file_logo = secure_filename(form.logo.data.filename)

        if not os.path.exists(app.config['UP_DIR']):
            os.makedirs(app.config['UP_DIR'])
            os.chmod(app.config['UP_DIR'], 6)

        url = change_filename(file_url)
        logo = change_filename(file_logo)
        form.url.data.save(app.config['UP_DIR'] + url)
        form.logo.data.save(app.config['UP_DIR'] + logo)

        movie = Movie(
            title=data['title'],
            url=url,
            info=data['info'],
            logo=logo,
            star=int(data['star']),
            playnum=0,
            commentnum=0,
            tag_id=int(data['tag_id']),
            area=data['area'],
            release_time=data['release_time'],
            length=data['length']
        )
        db.session.add(movie)
        db.session.commit()
        flash('电影添加成功!', 'info')
        return redirect(url_for('admin.movie_add'))
    return render_template('admin/movie_add.html', form=form)


@admin.route('/movie/list/<int:page>/')
@admin_login_req
# @admin_auth
def movie_list(page=1):
    if page <= 0:
        page = 1
    page_data = Movie.query.join(Tag).filter(
        Tag.id == Movie.tag_id
    ).order_by(
        Movie.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/movie_list.html', page_data=page_data)


@admin.route('/movie/del/<int:id>/')
@admin_login_req
# @admin_auth
def movie_del(id=None):
    movie = Movie.query.get_or_404(int(id))
    db.session.delete(movie)
    db.session.commit()
    flash('电影删除成功!', 'info')
    return redirect(url_for('admin.movie_list', page=1))


@admin.route('/movie/edit/<int:id>', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def movie_edit(id=None):
    form = MovieForm()

    # 如果不设置,默认依然会让上传文件
    form.url.flags.required = False
    form.logo.flags.required = False

    # 取消校验,可能没有上传文件
    form.url.validators=[]
    form.logo.validators=[]
    # 取消后如果没有上传文件,form.url.data是一个str对象
    # 上传文件后是才是一个文件对象
    # 为了方便,设置必须上传文件

    movie = Movie.query.get_or_404(int(id))
    if request.method == 'GET':
        form.info.data = movie.info
        form.tag_id.data = movie.tag_id
        form.star.data = movie.star
    if form.validate_on_submit():
        data = form.data
        movie_count = Movie.query.filter_by(title=data['title']).count()
        if movie_count == 1 and movie.title != data['title']:
            flash('该电影已存在!', 'error')
            return redirect(url_for('admin.movie_edit', id=id))

        if not os.path.exists(app.config['UP_DIR']):
            os.makedirs(app.config['UP_DIR'])
            os.chmod(app.config['UP_DIR'], 6)

        if getattr(form.url.data, 'filename', ''):
            file_url = secure_filename(form.url.data.filename)
            movie.url = change_filename(file_url)
            form.url.data.save(app.config['UP_DIR'] + movie.url)

        if getattr(form.logo.data, 'filename', ''):
            file_logo = secure_filename(form.logo.data.filename)
            movie.logo = change_filename(file_logo)
            form.logo.data.save(app.config['UP_DIR'] + movie.logo)

        movie.star = data['star']
        movie.tag_id = data['tag_id']
        movie.info = data['info']
        movie.title = data['title']
        movie.area = data['area']
        movie.length = data['length']
        movie.release_time = data['release_time']

        db.session.add(movie)
        db.session.commit()
        flash('电影修改成功!', 'info')
        return redirect(url_for('admin.movie_edit', id=movie.id))
    return render_template('admin/movie_edit.html', form=form, movie=movie)


@admin.route('/preview/add/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def preview_add():
    form = PreviewForm()
    if form.validate_on_submit():
        data = form.data
        file_logo = secure_filename(form.logo.data.filename)

        if not os.path.exists(app.config['UP_DIR']):
            os.makedirs(app.config['UP_DIR'])
            os.chmod(app.config['UP_DIR'], 6)

        logo = change_filename(file_logo)
        form.logo.data.save(app.config['UP_DIR'] + logo)
        preview = Preview(
            title=data['title'],
            logo=logo
        )
        db.session.add(preview)
        db.session.commit()
        flash("预告添加成功!", 'info')
        return redirect(url_for('admin.preview_add'))
    return render_template('admin/preview_add.html', form=form)


@admin.route('/preview/list/<int:page>/')
@admin_login_req
# @admin_auth
def preview_list(page=1):
    if page <= 0:
        page = 1
    page_data = Preview.query.order_by(
        Preview.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/preview_list.html', page_data=page_data)


@admin.route('/preview/del/<int:id>/')
@admin_login_req
# @admin_auth
def preview_del(id=None):
    preview = Preview.query.get_or_404(int(id))
    db.session.delete(preview)
    db.session.commit()
    flash('预告删除成功!', 'info')
    return redirect(url_for('admin.preview_list', page=1))


@admin.route('/preview/edit/<int:id>/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def preview_edit(id=None):
    form = PreviewForm()
    preview = Preview.query.get_or_404(int(id))

    if request.method == 'GET':
        form.title.data = preview.title
    if form.validate_on_submit():
        data = form.data

        if not os.path.exists(app.config['UP_DIR']):
            os.makedirs(app.config['UP_DIR'])
            os.chmod(app.config['UP_DIR'], 6)

        if form.logo.data.filename != '':
            file_logo = secure_filename(form.logo.data.filename)
            preview.logo = change_filename(file_logo)
            form.logo.data.save(app.config['UP_DIR'] + preview.logo)

        preview.title = data['title']
        db.session.add(preview)
        db.session.commit()

        flash('预告修改成功!', 'info')
        return redirect(url_for('admin.preview_edit', id=id))
    return render_template('admin/preview_edit.html', form=form, preview=preview)


@admin.route('/user/view/<int:id>/')
@admin_login_req
# @admin_auth
def user_view(id=None):
    user = User.query.get_or_404(int(id))
    return render_template('admin/user_view.html', user=user)


@admin.route('/user/list/<int:page>/')
@admin_login_req
# @admin_auth
def user_list(page=1):
    if page <= 0:
        page = 1
    page_data = User.query.order_by(
        User.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/user_list.html', page_data=page_data)


@admin.route('/user/del/<int:id>/')
@admin_login_req
# @admin_auth
def user_del(id=None):
    user = User.query.get_or_404(int(id))
    db.session.delete(user)
    db.session.commit()
    flash('会员删除成功!', 'info')
    return redirect(url_for('admin.user_list', page=1))


@admin.route('/comment/list/<int:page>/')
@admin_login_req
# @admin_auth
def comment_list(page=1):
    if page <= 0:
        page = 1
    page_data = Comment.query.join(
        Movie
    ).join(
        User
    ).filter(
        Movie.id == Comment.movie_id,
        User.id == Comment.user_id
    ).order_by(
        Comment.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/comment_list.html', page_data=page_data)


@admin.route('/comment/del/<int:id>/')
@admin_login_req
# @admin_auth
def comment_del(id=None):
    comment = Comment.query.get_or_404(int(id))
    db.session.delete(comment)
    db.session.commit()
    flash('评论删除成功!', 'info')
    return redirect(url_for('admin.comment_list', page=1))


@admin.route('/moviecol/list/<int:page>/')
@admin_login_req
# @admin_auth
def moviecol_list(page=1):
    if page <= 0:
        page = 1
    page_data = Moviecol.query.join(
        Movie
    ).join(
        User
    ).filter(
        Movie.id == Moviecol.movie_id,
        User.id == Moviecol.user_id
    ).order_by(
        Moviecol.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/moviecol_list.html', page_data=page_data)


@admin.route('/moviecol/del/<int:id>/')
@admin_login_req
# @admin_auth
def moviecol_del(id=None):
    moviecol = Moviecol.query.get_or_404(int(id))
    db.session.delete(moviecol)
    db.session.commit()
    flash('收藏删除成功!', 'info')
    return redirect(url_for('admin.moviecol_list', page=1))


@admin.route('/oplog/list/<int:page>/')
@admin_login_req
# @admin_auth
def oplog_list(page=1):
    if page <= 0:
        page = 1
    page_data = Oplog.query.join(
        Admin
    ).filter(
        Admin.id == Oplog.admin_id,
    ).order_by(
        Oplog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/oplog_list.html', page_data=page_data)


@admin.route('/adminloginlog/list/<int:page>/')
@admin_login_req
# @admin_auth
def adminloginlog_list(page=1):
    if page <= 0:
        page = 1
    page_data = Adminlog.query.join(
        Admin
    ).filter(
        Admin.id == Adminlog.admin_id,
    ).order_by(
        Adminlog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/adminloginlog_list.html', page_data=page_data)


@admin.route('/userloginlog/list/<int:page>/')
@admin_login_req
# @admin_auth
def userloginlog_list(page=1):
    if page <= 0:
        page = 1
    page_data = Userlog.query.join(
        User
    ).filter(
        User.id == Userlog.user_id,
    ).order_by(
        Userlog.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/userloginlog_list.html', page_data=page_data)


@admin.route('/role/add/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def role_add():
    form = RoleForm()
    if form.validate_on_submit():
        data = form.data
        role = Role(
            name=data['name'],
            auths=','.join(map(lambda v: str(v), data['auths']))
        )

        db.session.add(role)
        db.session.commit()
        flash('角色添加成功!', 'info')
    return render_template('admin/role_add.html', form=form)


@admin.route('/role/list/<int:page>/')
@admin_login_req
# @admin_auth
def role_list(page=1):
    if page <= 0:
        page = 1
    page_data = Role.query.order_by(
        Role.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/role_list.html', page_data=page_data)


@admin.route('/role/del/<int:id>/')
@admin_login_req
# @admin_auth
def role_del(id=None):
    role = Role.query.get_or_404(int(id))
    db.session.delete(role)
    db.session.commit()
    flash('角色删除成功!', 'info')
    return redirect(url_for('admin.role_list', page=1))


@admin.route('/role/edit/<int:id>/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def role_edit(id=None):
    form = RoleForm()
    role = Role.query.get_or_404(int(id))

    if request.method == 'GET':
        auths = role.auths
        form.auths.data = list(map(lambda x: int(x), auths.split(',')))

    if form.validate_on_submit():
        data = form.data
        role.name = data['name']
        role.auths = ','.join(map(lambda v: str(v), data['auths']))

        db.session.add(role)
        db.session.commit()
        flash('角色修改成功!', 'info')
    return render_template('admin/role_edit.html', form=form, role=role)


@admin.route('/auth/add/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def auth_add():
    form = AuthForm()
    if form.validate_on_submit():
        data = form.data
        auth = Auth(
            name=data['name'],
            url=data['url']
        )

        db.session.add(auth)
        db.session.commit()

        flash('权限添加成功!', 'info')
    return render_template('admin/auth_add.html', form=form)


@admin.route('/auth/list/<int:page>/')
@admin_login_req
# @admin_auth
def auth_list(page=1):
    if page <= 0:
        page = 1
    page_data = Auth.query.order_by(
        Auth.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/auth_list.html', page_data=page_data)


@admin.route('/auth/del/<int:id>/')
@admin_login_req
# @admin_auth
def auth_del(id=None):
    auth = Auth.query.get_or_404(int(id))
    db.session.delete(auth)
    db.session.commit()
    flash('权限删除成功!', 'info')
    return redirect(url_for('admin.auth_list', page=1))


@admin.route('/auth/edit/<int:id>/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def auth_edit(id=None):
    form = AuthForm()
    auth = Auth.query.get_or_404(int(id))

    if form.validate_on_submit():
        data = form.data
        auth.name = data['name']
        auth.url = data['url']

        db.session.add(auth)
        db.session.commit()

        flash('权限修改成功!', 'info')
        return redirect(url_for('admin.auth_edit', id=id))
    return render_template('admin/auth_edit.html', form=form, auth=auth)


@admin.route('/admin/add/', methods=['GET', 'POST'])
@admin_login_req
# @admin_auth
def admin_add():
    form = AdminForm()

    from werkzeug.security import generate_password_hash

    if form.validate_on_submit():
        data = form.data
        admin = Admin(
            name=data['name'],
            pwd=generate_password_hash(data['pwd']),
            role_id=data['role_id'],
            is_super=1,
        )

        db.session.add(admin)
        db.session.commit()

        flash('管理员添加成功!', 'info')

    return render_template('admin/admin_add.html', form=form)


@admin.route('/admin/list/<int:page>/')
@admin_login_req
# @admin_auth
def admin_list(page=1):
    if page <= 0:
        page = 1
    page_data = Admin.query.join(
        Role
    ).filter(
        Role.id == Admin.role_id
    ).order_by(
        Admin.addtime.desc()
    ).paginate(page=page, per_page=10)
    return render_template('admin/admin_list.html', page_data=page_data)
