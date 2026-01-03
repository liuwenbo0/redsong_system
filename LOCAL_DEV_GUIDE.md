# 本地开发快速指南

## 方式 1: 使用 Docker 开发 (推荐 - 一键配置)

这是最简单的开发方式，无需手动安装 ngrok 或 Python 环境，只需 Docker。

### 快速开始

#### 步骤 1: 配置 .env 文件

在项目根目录创建 `.env` 文件，并添加你的配置：

```bash
# 必需配置
OPENROUTER_API_KEY=sk-or-v1-xxxx
KIE_API_KEY=xxxx
FLASK_DEBUG=True

# Ngrok 配置 (用于自动内网穿透)
NGROK_AUTHTOKEN=2Roxxxxx  # 从 dashboard.ngrok.com 获取
# NGROK_DOMAIN=my-domain.ngrok-free.app  # (可选) 如果你有固定域名
```

#### 步骤 2: 一键启动

运行项目提供的启动脚本：

```bash
./start_docker.sh
```

脚本会自动：
1. 构建 Docker 镜像
2. 启动应用
3. 启动内置的 ngrok
4. 自动获取公网 URL 并配置到应用中

你会看到如下输出：

```
============================================================
 Ngrok 启动成功!
 公网地址 (Public URL): https://a1b2c3d4.ngrok-free.app
 回调地址 (Callback URL): https://a1b2c3d4.ngrok-free.app/api/kie/callback
============================================================
```

现在你可以直接访问 `http://localhost:5000` 进行测试，回调功能已自动就绪！

---

## 方式 2: 本地手动开发 (传统方式)

如果你不想使用 Docker，可以按照以下步骤手动配置环境。

### 使用 ngrok 进行本地开发

这是手动配置的方式，可以让 Kie API 成功回调到你本地的开发服务器。

### 快速开始（3步走）

#### 步骤 1: 安装 ngrok

```bash
# macOS
brew install ngrok

# Linux
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Windows
# 访问 https://ngrok.com/download 下载安装程序
```

#### 步骤 2: 启动本地服务器

```bash
cd /mnt/c/my_project/competition/深信服AI比赛/redsong_system
python3 app.py
```

服务器会在 http://localhost:5000 启动

#### 步骤 3: 在新终端窗口启动 ngrok

不要关闭第一个终端（Flask 服务器），打开新的终端窗口：

```bash
ngrok http 5000
```
前往https://dashboard.ngrok.com/signup进行注册，获取authtoken：https://dashboard.ngrok.com/get-started/your-authtoken
你会看到类似输出（注意你的 URL 会不同）：

```
Session Status                Online
Account                       your-name
Version                       3.x.x
Forwarding                    https://a1b2c3d4.ngrok-free.app -> http://localhost:5000
Forwarding                    https://a1b2c3d4.ngrok.io -> http://localhost:5000
```

复制你的 ngrok URL（例如：`https://a1b2c3d4.ngrok-free.app`）

#### 步骤 4: 配置 .env 文件

编辑 `.env` 文件，添加或修改 `CALLBACK_URL`：

```bash
CALLBACK_URL=https://a1b2c3d4.ngrok-free.app/api/kie/callback
```

#### 步骤 5: 重启 Flask 服务器

回到第一个终端（运行 Flask 的那个）：

```bash
# 按 Ctrl+C 停止服务器
# 然后重新启动
python3 app.py
```

#### 步骤 6: 测试红歌创作功能

1. 打开浏览器访问 http://localhost:5000/creation
2. 输入歌词主题，点击"生成歌词"
3. 选择曲风，点击"生成旋律"
4. 等待 1-2 分钟（Kie API 需要时间生成歌曲）
5. 应该能看到生成的歌曲并播放

### 临时解决方案（如果你不想用 ngrok）

如果你想快速测试，可以使用生产地址接收回调：

```bash
# .env 文件中配置
CALLBACK_URL=https://redsong.bond/api/kie/callback
```

**注意：**
- 这种方式生成的歌曲会保存到生产服务器
- 本地 `temp_tasks` 目录会保持为空
- 生产服务器需要保持运行

## 验证配置是否成功

### 方法 1: 检查 temp_tasks 目录

```bash
ls -la temp_tasks/
```

如果看到 `{task_id}.json` 文件，说明回调成功！

### 方法 2: 查看 Flask 日志

在运行 Flask 的终端窗口中，你会看到:

```
INFO:kie_callback:Received callback for task_id: abc123
```

### 方法 3: 使用浏览器开发者工具

按 F12 打开开发者工具，查看 Network 标签：

1. `POST /api/create/song/start` - 应返回 `{"task_id": "...", "provider": "kie"}`
2. `GET /api/create/song/status/{task_id}` - 最终应返回 `{"status": "SUCCESS", "audio_url": "..."}`

## 常见问题

### Q: ngrok 每次启动 URL 都不同，怎么办？

A: ngrok 免费版的 URL 确实会变化。你可以：
1. 购买 ngrok 付费版获得固定域名
2. 或者每次启动后更新 .env 文件中的 CALLBACK_URL
3. 或者使用生产地址作为回调（见上文的临时解决方案）

### Q: 看到错误 "IP whitelist" 怎么办？

A: 这表示 Kie API 的 IP 白名单限制。解决方法：
1. 登录 Kie.ai 控制台
2. 将你的公网 IP 添加到白名单
3. 如果使用 ngrok，将 ngrok 服务器的 IP 添加到白名单

### Q: 本地开发时，音乐播放器显示加载但播放不了？

A: 可能是音频 URL 有问题，检查：
1. 浏览器控制台是否有错误
2. Network 标签中音频 URL 是否能访问
3. 音频文件是否真的存在且可访问

### Q: 想要完全离线开发？

A: Kie API 是在线服务，无法完全离线。但你可以：
1. 使用 mock 数据模拟音乐生成（需要修改代码）
2. 或记录一次成功的 callback，重用那次生成的音频文件

## 开发工作流建议

### 日常开发工作流

```bash
# 1. 启动 Flask 服务器
cd /mnt/c/my_project/competition/深信服AI比赛/redsong_system
python3 app.py

# [新终端窗口]
# 2. 启动 ngrok
ngrok http 5000

# [复制 ngrok URL，编辑 .env]
# 3. 更新 CALLBACK_URL
CALLBACK_URL=https://xxxxx.ngrok-free.app/api/kie/callback

# [回到 Flask 终端]
# 4. 重启 Flask 服务器
Ctrl+C
python3 app.py

# 5. 在浏览器测试功能
# http://localhost:5000/creation
```

### 使用 screen 或 tmux（推荐）

使用 screen 可以在一个终端窗口中管理多个会话：

```bash
# 创建一个 Flask 会话
screen -S flask
python3 app.py
# 按 Ctrl+A 然后 D 退出会话

# 创建一个 ngrok 会话
screen -S ngrok
ngrok http 5000
# 按 Ctrl+A 然后 D 退出会话

# 查看所有会话
screen -ls

# 重新连接到会话
screen -r flask
# 或
screen -r ngrok
```

## 性能优化建议

### ngrok 免费版限制

- 每个 ngrok 会话只能维持 8 小时
- 流量有限制（不适合高并发测试）
- URL 每次重启会变化

### 开发环境优化

1. **缓存机制**: 如果需要频繁测试，可以缓存一些生成的歌曲
2. **错误处理**: 添加更完善的错误提示和重试机制
3. **日志记录**: 保存详细的回调日志便于调试

## 替代方案

### 使用其他隧道工具

除了 ngrok，你还可以使用：

- **cloudflare tunnel**: `cloudflared tunnel`
- **localtunnel**: `npx localtunnel --port 5000`
- **serveo**: `ssh -R 80:localhost:5000 serveo.net`

### 使用内网穿透服务

如果你有其他内网穿透服务（如花生壳、frp），也可以使用。

## 下一步

完成配置后，请参考 [`TROUBLESHOOTING_CALLBACK.md`](TROUBLESHOOTING_CALLBACK.md) 了解详细的调试方法和故障排除。

祝你开发愉快！🎵
