# 微信聊天记录分析系统 - 部署指南

## 🚀 快速开始

### 方式1: 使用部署助手（推荐）

运行部署助手，它会引导您完成整个部署过程：

```bash
python deploy.py
```

### 方式2: 直接启动

如果您已经安装了所有依赖，可以直接运行：

```bash
# 安装依赖
pip install -r requirements.txt

# 启动生产服务器
python run_production.py
```

## 📋 系统要求

- Python 3.7+
- 2GB+ RAM
- 1GB+ 磁盘空间

## 🌐 部署方式

### 1. 简单开发服务器

适合测试和小规模使用：

```bash
python run_production.py
```

**访问地址:**
- 本机: http://127.0.0.1:5000
- 局域网: http://[您的IP]:5000

### 2. Gunicorn生产服务器（推荐）

更好的性能和稳定性：

```bash
# 安装Gunicorn
pip install gunicorn

# 启动服务器
gunicorn --config gunicorn.conf.py --bind 0.0.0.0:5000 wsgi:application
```

或使用部署助手选择选项2。

### 3. Docker容器部署

最适合生产环境：

```bash
# 使用Docker Compose
docker-compose up --build

# 或仅使用Docker
docker build -t wechat-analysis .
docker run -p 5000:5000 -v $(pwd)/uploads:/app/uploads wechat-analysis
```

## 🔧 网络配置

### 防火墙设置

#### Windows
1. 打开"控制面板" > "Windows Defender防火墙"
2. 点击"高级设置"
3. 点击"入站规则" > "新建规则"
4. 选择"端口" > "TCP" > "特定本地端口: 5000"
5. 选择"允许连接"
6. 全选所有配置文件
7. 给规则命名，完成设置

#### macOS
系统偏好设置 > 安全性与隐私 > 防火墙 > 防火墙选项

#### Linux
```bash
sudo ufw allow 5000
# 或
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
```

### 路由器端口转发（可选）

如果需要从外网访问：

1. 登录路由器管理界面
2. 找到"端口转发"或"虚拟服务器"设置
3. 添加规则：
   - 外部端口: 5000
   - 内部端口: 5000
   - 内部IP: [您的电脑IP]
4. 保存设置

### 获取IP地址

**本机IP:**
```bash
# Windows
ipconfig
# macOS/Linux
ifconfig
```

**公网IP:**
访问 https://www.whatismyip.com/ 或在浏览器搜索"我的IP"

## 🌍 访问方式

### 局域网访问
在同一局域网内的其他设备使用以下地址访问：
```
http://[您的电脑IP]:5000
```

### 广域网访问（需要端口转发）
从互联网访问：
```
http://[您的公网IP]:5000
```

### 域名访问（可选）
如果拥有域名，可以通过域名解析指向您的公网IP。

## 🔒 安全建议

### 生产环境安全

1. **更改默认配置**
   - 修改默认端口
   - 使用强密码
   - 禁用调试模式

2. **HTTPS加密**
   - 配置SSL证书
   - 使用Nginx反向代理

3. **访问控制**
   - 配置防火墙规则
   - 限制访问IP范围
   - 使用VPN

### 数据安全

1. **定期备份**
   - 备份数据库文件
   - 备份上传的文件

2. **数据隔离**
   - 使用专用数据库服务器
   - 定期清理临时文件

## 📊 监控和维护

### 健康检查

应用提供健康检查端点：
```
GET /health
```

### 日志管理

- 应用日志：控制台输出
- 访问日志：配置文件中指定
- 错误日志：自动记录到控制台

### 性能监控

使用以下工具监控应用性能：
- **htop**: 系统资源监控
- **nginx**: Web服务器日志
- **Gunicorn**: 应用服务器统计

## 🐛 常见问题

### Q: 无法访问应用
A: 检查以下项目：
1. 防火墙设置
2. 端口是否被占用
3. IP地址是否正确
4. 服务是否正在运行

### Q: 上传文件失败
A: 检查以下项目：
1. uploads目录权限
2. 文件大小限制
3. 磁盘空间

### Q: 性能问题
A: 优化建议：
1. 使用Gunicorn代替Flask开发服务器
2. 增加工作进程数
3. 启用数据库索引
4. 使用缓存

### Q: 部署到云服务器
A: 推荐步骤：
1. 选择云服务提供商
2. 创建虚拟机实例
3. 配置安全组规则
4. 按照本指南部署应用

## 📞 技术支持

如果在部署过程中遇到问题，可以：

1. 查看错误日志
2. 运行部署助手获取帮助
3. 检查网络连接
4. 验证依赖安装

## 🔄 更新和维护

### 更新应用
```bash
git pull origin main  # 如果使用Git
pip install -r requirements.txt --upgrade
```

### 备份数据
```bash
# 备份数据库
cp wechat_analysis.db backup/wechat_analysis_$(date +%Y%m%d).db

# 备份上传文件
tar -czf backup/uploads_$(date +%Y%m%d).tar.gz uploads/
```

### 清理临时文件
```bash
# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 清理临时上传文件
find uploads/ -type f -mtime +7 -delete  # 删除7天前的文件
```

---

## 🎉 完成！

现在您的微信聊天记录分析系统已经可以在其他电脑上访问了！

如有任何问题，请参考本文档或运行 `python deploy.py` 获取帮助。