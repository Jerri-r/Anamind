#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信聊天记录分析系统 - 公网启动脚本
一键启动，其他设备可访问
"""

import os
import sys
import socket
import subprocess
import webbrowser
import time

def get_local_ip():
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 微信聊天记录分析系统 - 公网启动")
    print("=" * 60)
    
    # 检查文件
    if not os.path.exists("app.py"):
        print("❌ 找不到app.py文件")
        input("按任意键退出...")
        return
    
    # 初始化数据库
    print("📊 正在初始化数据库...")
    try:
        from app import init_db
        init_db()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        input("按任意键退出...")
        return
    
    # 获取IP信息
    local_ip = get_local_ip()
    port = 5000
    
    print("\n🌐 网络信息:")
    print(f"  本机IP地址: {local_ip}")
    print(f"  访问端口: {port}")
    
    print("\n📱 访问地址:")
    print(f"  本机访问: http://127.0.0.1:{port}")
    print(f"  局域网访问: http://{local_ip}:{port}")
    print(f"  其他设备访问: http://{local_ip}:{port}")
    
    print("\n📋 其他设备访问步骤:")
    print("  1. 确保所有设备在同一WiFi网络")
    print("  2. 在其他设备浏览器输入上述地址")
    print("  3. 如无法访问，检查防火墙设置")
    
    print("\n⚠️  防火墙设置提示:")
    print("  Windows: 允许Python程序通过防火墙")
    print("  或手动开放5000端口")
    
    # 询问是否自动打开浏览器
    auto_open = input("\n🌍 是否自动打开浏览器? (y/n): ").lower().strip()
    
    print("\n" + "=" * 60)
    print("🔄 正在启动服务器...")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    # 自动打开浏览器
    if auto_open in ['y', 'yes', '是']:
        def open_browser():
            time.sleep(2)  # 等待服务器启动
            webbrowser.open(f"http://127.0.0.1:{port}")
        
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
    
    # 启动服务器
    try:
        from app import app
        app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
    except KeyboardInterrupt:
        print("\n\n✅ 服务器已停止")
    except Exception as e:
        print(f"\n\n❌ 服务器启动失败: {e}")
        input("按任意键退出...")

if __name__ == "__main__":
    main()