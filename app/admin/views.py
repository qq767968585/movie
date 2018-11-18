#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/11/14 下午 07:54
# @Author  : gao
# @File    : views.py
from app.admin import admin


@admin.route('/')
def index():
    return '后台主页'