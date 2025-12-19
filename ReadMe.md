# 数智红韵网 - 本地部署指南

一个融合了文化展示、学习与AI创作的交互式红歌文化平台，支持本地快速部署和开发。

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+ (可选，用于前端工具)
- SQLite 3 (自动创建)
- 2GB+ 内存

### 一键部署

```bash
# 克隆项目
git clone <your-repo-url> redsong_system
cd redsong_system

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

## 📋 手动部署步骤

### 1. 环境配置

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install torch==1.13.0+cu116 torchvision==0.14.0+cu116 torchaudio==0.13.0 --extra-index-url https://download.pytorch.org/whl/cu116
pip install Flask Flask-CORS Flask-SQLAlchemy
pip install -q -U google-genai
pip install pytz
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件，填入您的API密钥
nano .env
```

**必需配置项：**
- `OPENROUTER_API_KEY`: OpenRouter API密钥 (AI聊天和歌词生成)
- `KIE_API_KEY`: Kie.ai API密钥 (AI音乐生成)

### 3. 数据库初始化

数据库会在应用启动时自动创建和初始化，无需手动操作。

### 4. 启动应用

```bash
# 开发模式
python app.py

# 或使用Gunicorn (推荐用于生产)
gunicorn --workers 3 --bind 0.0.0.0:8000 app:app
```

访问 `http://localhost:8000` 查看应用。

## 🏗️ 生产环境部署

### 使用 Nginx + Gunicorn

#### 1. 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install nginx -y

# CentOS/RHEL
sudo yum install nginx -y
```

#### 2. 配置 Nginx

```bash
# 复制配置模板
sudo cp nginx.conf.example /etc/nginx/sites-available/redsong_system

# 创建软链接
sudo ln -s /etc/nginx/sites-available/redsong_system /etc/nginx/sites-enabled/

# 移除默认配置
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

#### 3. 配置 Systemd 服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/redsong_system.service
```

```ini
[Unit]
Description=Red Song System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/project
Environment=PATH=/path/to/your/project/venv/bin
ExecStart=/path/to/your/project/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 启动并启用服务
sudo systemctl start redsong_system
sudo systemctl enable redsong_system
# 如果修改了.service文件
sudo systemctl daemon-reload
sudo systemctl restart redsong_system

```

## 🔧 开发指南

### 项目结构

```
redsong_system/
├── app.py                 # 主应用文件
├── database.py            # 数据库模型和初始化
├── .env.example          # 环境变量模板
├── requirements.txt       # Python依赖
├── deploy.sh            # 一键部署脚本
├── nginx.conf.example    # Nginx配置模板
├── static/              # 静态资源
│   ├── assets/
│   │   ├── css/        # 样式文件
│   │   ├── js/         # JavaScript文件
│   │   └── ...
│   ├── images/          # 图片资源
│   └── ...
└── templates/           # HTML模板
    ├── index.html
    ├── circle.html
    └── ...
```

### API 接口

#### 用户认证
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/status` - 认证状态
- `POST /api/auth/logout` - 用户登出

#### 红歌功能
- `GET /api/songs/search?q=关键词` - 搜索红歌
- `GET /api/songs/by_region/地区` - 按地区获取红歌
- `POST /api/song/toggle_favorite/{id}` - 切换收藏状态
- `GET /api/songs/favorites` - 获取收藏列表

#### AI 功能
- `POST /api/song/chat` - AI聊天
- `POST /api/create/lyrics` - AI作词
- `POST /api/create/song/start` - 开始AI作曲
- `GET /api/create/song/status/{task_id}` - 查询作曲状态

### 数据库模型

- **User**: 用户信息
- **Song**: 红歌数据
- **Article**: 红歌微课
- **HistoricalEvent**: 历史事件
- **ChatHistory**: 聊天记录

## 🔐 安全配置

### 1. 环境变量安全

```bash
# 设置文件权限
chmod 600 .env
chown www-data:www-data .env
```

### 2. HTTPS 配置

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取SSL证书
sudo certbot --nginx -d your-domain.com
```

### 3. 防火墙设置

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 🐛 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库文件权限
ls -la project.db
chmod 664 project.db
```

#### 2. API密钥错误
```bash
# 检查环境变量
cat .env
# 确保API密钥格式正确
```

#### 3. 静态文件404
```bash
# 检查Nginx配置
sudo nginx -t
# 检查文件路径
ls -la static/
```

#### 4. Gunicorn进程崩溃
```bash
# 查看日志
sudo journalctl -u redsong_system.service -f
# 检查端口占用
sudo netstat -tlnp | grep :5000
```

### 日志位置

- **应用日志**: `/var/log/nginx/redsong_system.error.log`
- **系统服务日志**: `sudo journalctl -u redsong_system.service`
- **Nginx访问日志**: `/var/log/nginx/redsong_system.access.log`

## 📊 性能优化

### 1. 数据库优化
- 定期清理聊天历史
- 为常用查询字段添加索引
- 考虑使用PostgreSQL替代SQLite

### 2. 静态资源优化
- 启用Gzip压缩
- 设置合理的缓存策略
- 使用CDN加速

### 3. 应用优化
- 调整Gunicorn worker数量
- 启用连接池
- 实现API响应缓存

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如有问题，请：
1. 查看本文档的故障排除部分
2. 检查 [Issues](../../issues) 页面
3. 创建新的 Issue 描述问题

---

**注意**: 本项目仅用于教育和研究目的。请确保遵守相关API服务的使用条款。