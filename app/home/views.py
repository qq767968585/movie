#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/11/14 下午 07:54
# @Author  : gao
# @File    : views.py
from app.home import home


@home.route('/')
def index():
    return "前台主页"