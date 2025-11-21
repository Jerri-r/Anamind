#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信聊天记录分析系统 - 生产环境启动脚本
"""

import os
import sys
from app import app, init_db

def main():
    """生产环境启动函数"""
    
    # 初始化数据库
    print("正在初始化数据库...")
    init_db()
    print("数据库初始化完成！")
    
    # 生产环境配置
    production_config = {
        'debug': False,              # 关闭调试模式
        'host': '0.0.0.0',         # 监听所有网络接口
        'port': 5000,               # 使用5000端口
        'threaded': True,           # 启用多线程
        'processes': 1,             # 单进程（适合小型应用）
    }
    
    print(f"启动服务器配置:")
    print(f"  - 主机: {production_config['host']}")
    print(f"  - 端口: {production_config['port']}")
    print(f"  - 调试模式: {production_config['debug']}")
    print(f"  - 多线程: {production_config['threaded']}")
    print(f"  - 进程数: {production_config['processes']}")
    print()
    print("服务器正在启动...")
    print("访问地址:")
    print(f"  - 本地访问: http://127.0.0.1:5000")
    print(f"  - 局域网访问: http://[您的IP地址]:5000")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        # 启动Flask应用
        app.run(**production_config)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()