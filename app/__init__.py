#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/11/14 下午 07:51
# @Author  : gao
# @File    : __init__.py.py
import os

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_redis import FlaskRedis

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+cymysql://root:123456@127.0.0.1:3306/movie'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config["REDIS_URL"] = "redis://:123456@localhost:6379/1"
app.config['SECRET_KEY'] = 'cb349581-5c5d-4c77-85f5-89bae30d90f6'
app.config['UP_DIR'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads/')
app.config["FC_DIR"] = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static/uploads/users/")


db = SQLAlchemy(app)
rd = FlaskRedis(app)

from app.home import home as home_blueprint
from app.admin import admin as admin_blueprint


app.register_blueprint(home_blueprint)
app.register_blueprint(admin_blueprint, url_prefix='/admin')

@app.errorhandler(404)
def page_not_found(err):
    return render_template('home/404.html'), 404
