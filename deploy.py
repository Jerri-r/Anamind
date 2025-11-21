#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信聊天记录分析系统 - 部署助手
提供多种部署方式的配置和指导
"""

import os
import sys
import subprocess
import socket
import platform

def get_local_ip():
    """获取本机IP地址"""
    try:
        # 连接到一个外部地址来获取本地IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def check_port_available(port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return True
        except:
            return False

def install_requirements():
    """安装依赖包"""
    print("正在安装Python依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖包安装完成！")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依赖包安装失败！")
        return False

def run_simple_server():
    """运行简单的Flask开发服务器"""
    print("启动简单Flask服务器...")
    print("=" * 50)
    
    local_ip = get_local_ip()
    port = 5000
    
    if not check_port_available(port):
        print(f"❌ 端口 {port} 已被占用！")
        return False
    
    print(f"服务器配置:")
    print(f"  - 本地访问: http://127.0.0.1:{port}")
    print(f"  - 局域网访问: http://{local_ip}:{port}")
    print(f"  - 局域网其他设备访问: http://[您的IP]:{port}")
    print()
    print("注意: 这是开发服务器，适合测试和小规模使用")
    print("生产环境建议使用Gunicorn或Docker部署")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        subprocess.run([sys.executable, "run_production.py"])
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        return False

def run_gunicorn_server():
    """使用Gunicorn运行服务器"""
    print("正在使用Gunicorn启动服务器...")
    print("=" * 50)
    
    # 检查是否安装了Gunicorn
    try:
        subprocess.run([sys.executable, "-c", "import gunicorn"], check=True)
    except subprocess.CalledProcessError:
        print("正在安装Gunicorn...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gunicorn"])
    
    local_ip = get_local_ip()
    port = 5000
    
    print(f"服务器配置:")
    print(f"  - 本地访问: http://127.0.0.1:{port}")
    print(f"  - 局域网访问: http://{local_ip}:{port}")
    print()
    print("使用Gunicorn生产服务器，性能更好")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        cmd = [sys.executable, "-m", "gunicorn", 
               "--config", "gunicorn.conf.py", 
               "--bind", f"0.0.0.0:{port}",
               "--workers", "4",
               "wsgi:application"]
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        return False

def run_docker():
    """使用Docker运行服务器"""
    print("正在使用Docker启动服务器...")
    print("=" * 50)
    
    # 检查Docker是否安装
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        print("✅ Docker已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker未安装，请先安装Docker")
        print("安装方法: https://docs.docker.com/get-docker/")
        return False
    
    # 检查Docker Compose是否安装
    try:
        subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
        print("✅ Docker Compose已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker Compose未安装，请先安装Docker Compose")
        return False
    
    print("构建并启动Docker容器...")
    try:
        subprocess.run(["docker-compose", "up", "--build"], check=True)
    except KeyboardInterrupt:
        print("\n正在停止Docker容器...")
        subprocess.run(["docker-compose", "down"])
        print("Docker容器已停止")
    except Exception as e:
        print(f"❌ Docker启动失败: {e}")
        return False

def show_network_info():
    """显示网络配置信息"""
    print("=" * 50)
    print("网络访问配置指南")
    print("=" * 50)
    
    local_ip = get_local_ip()
    
    print(f"本机IP地址: {local_ip}")
    print()
    print("访问方式:")
    print(f"1. 本机访问: http://127.0.0.1:5000")
    print(f"2. 局域网访问: http://{local_ip}:5000")
    print()
    print("要让其他电脑访问，请确保:")
    print("1. 防火墙允许5000端口")
    print("2. 所有设备在同一局域网内")
    print("3. 使用正确的IP地址访问")
    print()
    
    # Windows防火墙配置提示
    if platform.system() == "Windows":
        print("Windows防火墙配置:")
        print("1. 打开'控制面板' > 'Windows Defender防火墙'")
        print("2. 点击'高级设置'")
        print("3. 点击'入站规则' > '新建规则'")
        print("4. 选择'端口' > 'TCP' > '特定本地端口: 5000'")
        print("5. 选择'允许连接'")
        print("6. 全选所有配置文件")
        print("7. 给规则命名，完成设置")
        print()
    
    # macOS/Linux防火墙配置提示
    else:
        print("macOS/Linux防火墙配置:")
        print("macOS: 系统偏好设置 > 安全性与隐私 > 防火墙 > 防火墙选项")
        print("Linux: sudo ufw allow 5000 或 sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT")
        print()

def main():
    """主函数"""
    print("微信聊天记录分析系统 - 部署助手")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        sys.exit(1)
    
    print("✅ Python版本检查通过")
    
    # 检查必要文件
    required_files = ["app.py", "run_production.py", "requirements.txt"]
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ 缺少必要文件: {file}")
            sys.exit(1)
    
    print("✅ 必要文件检查通过")
    print()
    
    while True:
        print("请选择部署方式:")
        print("1. 简单开发服务器 (适合测试)")
        print("2. Gunicorn生产服务器 (推荐)")
        print("3. Docker容器部署 (高级)")
        print("4. 查看网络配置指南")
        print("5. 安装依赖包")
        print("0. 退出")
        print()
        
        choice = input("请输入选项 (0-5): ").strip()
        
        if choice == "1":
            if not install_requirements():
                continue
            run_simple_server()
        elif choice == "2":
            if not install_requirements():
                continue
            run_gunicorn_server()
        elif choice == "3":
            run_docker()
        elif choice == "4":
            show_network_info()
        elif choice == "5":
            install_requirements()
        elif choice == "0":
            print("退出部署助手")
            break
        else:
            print("❌ 无效选项，请重新选择")
        
        print()

if __name__ == "__main__":
    main()