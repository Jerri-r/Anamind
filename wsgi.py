#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point for 微信聊天记录分析系统
"""

from app import app, init_db

def application(environ, start_response):
    """WSGI application entry point"""
    # 确保数据库已初始化
    init_db()
    
    # 返回Flask应用的WSGI处理器
    return app(environ, start_response)

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)