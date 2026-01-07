# 数智红韵网

一个融合了文化展示、学习与 AI 创作的交互式红歌文化平台，支持本地快速部署和开发。

## 📌 项目名称

**数智红韵网** - 智能红歌文化学习与创作平台

## 💻 运行环境

### 必需环境

- **Python 3.8+** - 主要开发语言
- **SQLite 3** - 数据库（自动创建）

### 可选环境

- **Node.js 16+** - 用于前端开发工具
- **Docker** - 用于容器化部署
- **Nginx** - 用于生产环境反向代理

### 系统要求

- **内存**: 2GB+
- **磁盘空间**: 500MB+
- **操作系统**: Linux / macOS / WSL

## 📦 依赖库


| 依赖库           | 版本   | 用途             |
| ---------------- | ------ | ---------------- |
| Flask            | 2.3.2  | Web 框架         |
| Flask-CORS       | 4.0.0  | 跨域资源共享     |
| Flask-Login      | 0.6.3  | 用户认证管理     |
| Flask-SQLAlchemy | 3.0.5  | 数据库 ORM       |
| SQLAlchemy       | 2.0.21 | SQL 工具包       |
| python-dotenv    | 1.0.0  | 环境变量管理     |
| requests         | 2.31.0 | HTTP 请求库      |
| pytz             | -      | 时区处理         |
| gunicorn         | -      | WSGI HTTP 服务器 |
| Werkzeug         | 2.3.7  | WSGI 工具库      |


## 🚀 详细运行步骤



### 步骤一：部署应用

这一步有两种方式:

#### I. 拉取Docker镜像直接运行

我们利用Costrict将项目封装到了一个Docker镜像中,安装[docker](https://docs.docker.com/desktop/)后,运行下面的命令可以直接部署(默认使用5001端口)
此方式支持全平台部署

```bash
docker run -d -p 5001:5001 webliu/redsong-system:test
```


#### II. 配置本地环境部署

注意此方法目前只适配Debian系的linux系统

##### 首先获取项目文件
```bash
# 克隆项目（如果您有 Git 仓库）
git clone https://github.com/liuwenbo0/redsong_system.git
cd redsong_system

# 或者直接下载项目文件夹并进入目录
wget https://github.com/liuwenbo0/redsong_system/archive/refs/heads/main.zip
cd redsong_system
```

##### 配置本地环境

```bash
./deploy.sh
# 此脚本会自动检查依赖、配置环境，并赋予启动脚本执行权限。
```

##### 启动应用

```bash
./start_with_ngrok.sh
# 此脚本会启动应用（默认使用Gunicorn，失败则回退到Python），并可选启动ngrok内网穿透。
```

### 步骤二：访问应用

1. 打开浏览器
2. 在地址栏输入：`http://localhost:5001`(端口号取决于环境变量文件.env中PORT的值,默认是5001)
3. 您将看到数智红韵网的主页

**主要功能页面：**

- 主页：`http://localhost:5001/`
- 听·山河（红歌）：`http://localhost:5001/circle`
- 问·古今（对话）：`http://localhost:5001/making`
- 阅·峥嵘（视频）：`http://localhost:5001/plaza`
- 谱·华章（创作）：`http://localhost:5001/creation`
- 我的收藏：`http://localhost:5001/favorites`

### 步骤三：首次使用指南

1. **注册账号**

   - 点击页面右上角的"注册"按钮
   - 输入用户名（不超过 15 个字符）
   - 输入密码并确认
   - 点击"注册"完成

2. **登录系统**

   - 使用注册的用户名和密码登录
   - 登录后可使用收藏,评论等高级功能

3. **体验主要功能**
   - **红歌欣赏**：在"听·山河"中搜索和播放红歌
   - **AI 对话**：在"问·古今"中与"红小韵"AI 助手聊天
   - **音乐创作**：在"谱·华章"中创作红歌歌词和音乐
   - **成就系统**：通过答题、创作等解锁成就徽章


## 📁 项目结构

```
redsong_system/
├── app.py                 # 主应用文件（路由和业务逻辑）
├── database.py            # 数据库模型和初始化
├── config.py              # 配置文件（常量管理）
├── requirements.txt       # Python 依赖列表
├── .env                   # 环境变量配置（需手动创建）
├── README.md              # 本文档
├── deploy.sh              # 一键部署脚本
├── start_with_ngrok.sh    # 一键启动脚本
├── build_and_push.sh      # 一键构建docker镜像并推送脚本
├── Dockerfile             # Docker 容器配置
├── services/              # 业务服务层
│   ├── __init__.py
│   ├── agent_service.py   # AI 对话服务
│   └── llm_service.py     # LLM API 调用服务
├── static/                # 静态资源
│   ├── assets/
│   │   ├── css/          # 样式文件
│   │   ├── js/           # JavaScript 文件
│   │   └── ...
│   ├── images/           # 图片资源
│   ├── fonts/            # 字体文件
│   ├── music/            # 音乐文件
│   └── videos/           # 视频文件
└── templates/             # HTML 模板
    ├── index.html        # 主页
    ├── circle.html       # 红歌页面
    ├── making.html       # 对话页面
    ├── plaza.html        # 视频页面
    ├── creation.html     # 创作页面
    ├── favorites.html    # 收藏页面
    └── ...
```

## 🔧 API 接口文档

### 用户认证

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/status` - 获取认证状态
- `POST /api/auth/logout` - 用户登出

### 红歌功能

- `GET /api/songs/search?q=关键词` - 搜索红歌
- `GET /api/songs/by_region/地区` - 按地区获取红歌
- `POST /api/song/toggle_favorite/{id}` - 切换收藏状态
- `GET /api/songs/favorites` - 获取收藏列表

### AI 功能

- `POST /api/agent/chat` - AI 对话（红小韵）
- `POST /api/create/lyrics` - AI 作词
- `POST /api/create/song/start` - 开始 AI 作曲
- `GET /api/create/song/status/{task_id}` - 查询作曲状态

### 答题和成就

- `GET /api/quiz/questions` - 获取答题题目
- `POST /api/quiz/submit` - 提交答案
- `GET /api/achievements` - 获取成就列表

## 🐛 故障排除

### 问题 1：虚拟环境激活失败

```bash
# 错误提示：command not found: .venv/bin/activate
# 解决方案：确保项目目录下有 .venv 文件夹
ls -la .venv  # 检查虚拟环境是否存在

# 如果不存在，重新创建
python3 -m venv .venv
```

### 问题 2：依赖安装失败

```bash
# 错误提示：Permission denied
# 解决方案：使用 --user 参数或检查权限
pip install --user -r requirements.txt

# 或者使用国内镜像加速
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 3：端口被占用

```bash
# 错误提示：Address already in use
# 解决方案一：修改 .env 文件中的 PORT
PORT=5000  # 改为其他端口

# 解决方案二：停止占用端口的程序
# 查找占用端口的进程
lsof -i :5001
# 杀死进程
kill -9 <PID>
```

### 问题 4：API 密钥错误

```bash
# 错误提示：API Key not configured or invalid
# 解决方案：检查 .env 文件中的 API 密钥配置
cat .env  # 查看 API 密钥是否正确填写

# 确保 API 密钥格式正确（没有多余的空格或引号）
```

### 问题 5：数据库连接失败

```bash
# 错误提示：database is locked
# 解决方案：检查数据库文件权限
ls -la project.db  # 查看文件权限
chmod 664 project.db  # 修改权限

# 或者删除数据库文件重新创建
rm project.db
python app.py  # 重新启动会自动创建
```
