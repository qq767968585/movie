#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/11/14 下午 07:55
# @Author  : gao
# @File    : manage.py
from app import app
from flask_script import Manager

manage = Manager(app)
if __name__ == '__main__':
    manage.run()
