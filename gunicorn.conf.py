#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gunicorn配置文件 for 微信聊天记录分析系统
"""

# 服务器套接字
bind = "0.0.0.0:5000"
backlog = 2048

# 工作进程
workers = 4                    # 工作进程数（建议CPU核心数 * 2 + 1）
worker_class = "sync"         # 同步工作模式（适合Flask应用）
worker_connections = 1000      # 每个工作进程的连接数
max_requests = 1000           # 每个工作进程处理的最大请求数
max_requests_jitter = 50       # 最大请求数的随机变化

# 超时设置
timeout = 30                  # 工作进程超时时间（秒）
keepalive = 2                 # 保持连接时间
graceful_timeout = 30         # 优雅重启超时时间

# 日志配置
accesslog = "-"               # 访问日志输出到标准输出
errorlog = "-"                # 错误日志输出到标准输出
loglevel = "info"             # 日志级别
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "wechat_analysis"

# 安全设置
user = None                   # 不切换用户
group = None                  # 不切换组
tmp_upload_dir = None

# 服务器机制
daemon = False                # 不以守护进程方式运行
pidfile = None                # 不创建PID文件
user = None
group = None

# 监控
statsd_host = None           # 不使用statsd

# 进程文件
preload_app = False          # 不预加载应用
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Python优化
pythonpath = '.'              # 添加当前目录到Python路径