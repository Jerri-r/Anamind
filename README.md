# Flask WeChat Chat Record Analysis Application

一个基于Flask的微信聊天记录分析应用，支持数据导入、客户选择和智能分析功能。

## 🚀 功能特性

- **数据导入**: 支持多种格式的微信聊天记录导入（TXT、PDF、HTML）
- **客户管理**: 智能识别和管理客户信息
- **数据分析**: 提供详细的聊天记录分析和统计
- **响应式设计**: 现代化的用户界面，支持多设备访问
- **部署友好**: 完整的Docker部署方案

## 📁 项目结构

```
├── app.py                 # 主应用文件
├── wsgi.py               # WSGI配置
├── requirements.txt       # Python依赖
├── Dockerfile           # Docker构建文件
├── docker-compose.yml   # Docker编排文件
├── nginx.conf           # Nginx配置
├── gunicorn.conf.py     # Gunicorn配置
├── run_production.py    # 生产环境启动脚本
├── start_public.py      # 公网访问启动脚本
├── deploy.py            # 部署助手
├── static/              # 静态文件
│   └── css/
│       └── style.css
├── templates/           # HTML模板
│   ├── index.html
│   ├── data_import.html
│   ├── dashboard.html
│   └── table.html
├── samples/             # 样本数据
├── uploads/             # 上传文件目录
└── docs/               # 文档
    ├── README_DEPLOY.md
    ├── 访问指南.md
    └── push_to_github.md
```

## 🛠️ 技术栈

- **后端**: Flask (Python)
- **数据库**: SQLite
- **前端**: HTML5, CSS3, JavaScript
- **部署**: Docker, Nginx, Gunicorn
- **Web服务器**: 支持本地和公网部署

## 📦 快速开始

### 方法1：本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/Jerri-r/Anamind.git
cd Anamind

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行应用
python app.py
```

### 方法2：Docker部署

```bash
# 1. 构建并启动
docker-compose up -d

# 2. 访问应用
# http://localhost:5000
```

### 方法3：公网访问

```bash
# 1. 使用一键启动脚本
python start_public.py

# 2. 或使用Windows批处理文件
start_public.bat
```

## 🌐 访问地址

- **本地访问**: http://localhost:5000
- **Docker访问**: http://localhost:5000
- **公网访问**: 启动后会显示隧道地址

## 📱 使用说明

1. **数据导入页面**: 上传微信聊天记录文件
2. **客户选择页面**: 选择要分析的客户
3. **分析结果页面**: 查看详细的分析结果和搜索功能

## 🔧 配置说明

### 环境变量
- `FLASK_ENV`: 运行环境 (development/production)
- `HOST`: 监听地址 (默认: 0.0.0.0)
- `PORT`: 监听端口 (默认: 5000)

### 数据库
- 使用SQLite数据库，文件位于项目根目录的 `wechat_analysis.db`
- 支持数据备份和恢复

## 🚀 部署指南

详细部署说明请参考：
- [README_DEPLOY.md](README_DEPLOY.md)
- [访问指南.md](访问指南.md)

### 生产环境部署

```bash
# 1. 使用生产环境启动脚本
python run_production.py

# 2. 或使用Gunicorn
gunicorn --config gunicorn.conf.py wsgi:app
```

### 内网穿透

支持多种内网穿透方案：
- ngrok
- 花生壳
- 其他隧道服务

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 支持

如有问题或建议，请：
- 创建 [Issue](https://github.com/Jerri-r/Anamind/issues)
- 或联系项目维护者

## 🔗 相关链接

- [Flask官方文档](https://flask.palletsprojects.com/)
- [Docker文档](https://docs.docker.com/)
- [Gunicorn文档](https://docs.gunicorn.org/)

---

**注意**: 本应用仅用于合法的数据分析目的，请确保遵守相关法律法规和隐私政策。