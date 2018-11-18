#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/11/14 下午 07:51
# @Author  : gao
# @File    : __init__.py.py
from flask import Blueprint

home = Blueprint('home', __name__)

import app.home.views