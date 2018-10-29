import os
import re
import json
import datetime, time
from PIL import Image
from flask import render_template, redirect, request, session, Response, make_response, url_for, jsonify
from flask_login import login_required,login_user,logout_user, current_user
from app import login_manager
# 导入蓝本 main
from . import login
from .form import LoginForm
from app import models
from db import session_conn
from cms_server import db
from flask import current_app
from app.new_flash.hadoop_service import upload_info_images_hdfs


@login_manager.user_loader  # 使用user_loader装饰器的回调函数非常重要，他将决定 user 对象是否在登录状态
def user_loader(id):  # 这个id参数的值是在 login_user(user)中传入的 user 的 id 属性
    user = models.User.query.filter_by(id=id).first()
    return user


@login.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        form = LoginForm()
        return render_template('login/user_login.html', form=form)
    else:
        try:
            form = LoginForm(request.form)
            if form.validate():
                username = form.username.data
                pwd = form.password.data
                user = models.User.query.filter_by(email=username, password=pwd).first()
                if user:
                    login_user(user)
                    user.last_seen = datetime.datetime.now()
                    db.session.commit()
                    session['user'] = {'user_id':user.id, 'username':user.email}
                    return redirect(url_for('main.index'))
                else:
                    form.username.errors = ['账号密码不匹配，请重新输入']
                    return render_template('login/user_login.html', form=form)
        except Exception as e:
            current_app.logger.error(e)
            return render_template('404.html')


@login.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


@login.route("/re_pwd", methods=['GET', 'POST'])
@login_required
def re_pwd():
    if request.method == 'GET':
        return render_template('login/reset_pwd.html')
    elif request.method == 'POST':
        current_user.password = request.form.get('password')
        db.session.commit()
        return jsonify({'success':'ok'})


@login.route('/index')
@login_required
def index():
    return render_template('index.html')


def scale_img(fileobj, filepath):
    try:
        img = Image.open(fileobj)
        if len(img.split()) == 4:
            # prevent IOError: cannot write mode RGBA as BMP
            r, g, b, a = img.split()
            img = Image.merge("RGB", (r, g, b))
        img_data = img.size[0] * img.size[1] * 3 / 1024
        if img_data > 1024:
            img.thumbnail((900, 900), Image.ANTIALIAS)
        img.save(filepath)
    except Exception as e:
        current_app.logger.error(e)
        return render_template("404.html")


@login.route('/ckupload/', methods=['POST'])
def ckupload():
    """CKEditor file upload"""
    try:
        error = ''
        url = ''
        callback = request.args.get("CKEditorFuncNum")
        if request.method == 'POST' and 'upload' in request.files:
            fileobj = request.files['upload']
            fname, fext = os.path.splitext(fileobj.filename)
            fname = fname.replace(' ','')
            # rnd_name = '%s%s' % (gen_rnd_filename(), fext)
            uu = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            up_pic_name = "ckup_"+ uu + fext
            filepath = os.path.join(current_app.static_folder, 'upload', up_pic_name)
            # 检查路径是否存在，不存在则创建
            dirname = os.path.dirname(filepath)
            if not os.path.exists(dirname):
                try:
                    os.makedirs(dirname)
                except Exception as e :
                    error = 'ERROR_CREATE_DIR'
                    current_app.logger.error(e,error)
            elif not os.access(dirname, os.W_OK):
                error = 'ERROR_DIR_NOT_WRITEABLE'
                current_app.logger.error(error)
            if not error:
                if os.path.exists(filepath):
                    os.remove(filepath)
                fileobj.save(filepath)
                # scale_img(fileobj, filepath)
                # 获取hadoop地址
                new_img_url = upload_info_images_hdfs(up_pic_name, filepath)
                # url = url_for('static', filename='%s/%s' % ('upload', up_pic_name))
                url=new_img_url
                os.remove(filepath)
        else:
            error = 'post error'
        res = """<script type="text/javascript">
      window.parent.CKEDITOR.tools.callFunction(%s, '%s', '%s');
    </script>""" % (callback, url, error)
        response = make_response(res)
        response.headers["Content-Type"] = "text/html"
        return response
    except Exception as e:
        current_app.logger.error(e)
        return render_template('404.html')


@login.route("/ckupload_pasteimg/", methods=['POST'])
def ckupload_pasteimg():
    try:
        error = ""
        fileobj = request.files['upload']
        fname, fext = os.path.splitext(fileobj.filename)
        fname = fname.replace(' ', '')
        uu = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        up_pic_name = "ckpaste_" + uu + fext
        filepath = os.path.join(current_app.static_folder, 'upload', up_pic_name)
        # 检查路径是否存在，不存在则创建
        dirname = os.path.dirname(filepath)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except Exception as e:
                error = 'ERROR_CREATE_DIR'
                current_app.logger.error(e, error)
        elif not os.access(dirname, os.W_OK):
            error = 'ERROR_DIR_NOT_WRITEABLE'
            current_app.logger.error(error)
        if not error:
            if os.path.exists(filepath):
                os.remove(filepath)
            scale_img(fileobj, filepath)
            new_img_url = upload_info_images_hdfs(up_pic_name, filepath)
            url = new_img_url
            data = {
                "uploaded":1,
                "fileName": up_pic_name,
                "url" : url
            }
            os.remove(filepath)
            return jsonify(data)
    except Exception as e :
        current_app.logger.error(e)
        return render_template("404.html")
