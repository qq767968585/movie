#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/11/14 下午 07:55
# @Author  : gao
# @File    : manage.py
from app import app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')