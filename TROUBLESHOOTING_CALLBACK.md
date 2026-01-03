# 红歌创作模块回调问题调试指南

## 问题描述

当在本地运行项目时，点击"生成旋律"按钮后，前端一直显示"AI正在谱曲中"状态，无法接收生成的歌曲。

## 问题根本原因

### 工作流程说明

```
前端 → POST /api/create/song/start 
      ↓
Flask → 调用 Kie API (携带 callBackUrl)
      ↓
Kie API → 异步生成歌曲 (需要 1-2 分钟)
      ↓
Kie API → 回调 callBackUrl (POST /api/kie/callback) 返回音频URL
      ↓
Flask → 保存到 temp_tasks/{task_id}.json
      ↓
前端 → 轮询 GET /api/create/song/status/{task_id}
      ↓
前端 → 显示生成的歌曲
```

### 失败原因

**之前的状态：**
- 回调URL被硬编码为: `https://redsong.bond/api/kie/callback`
- 本地运行时，Kie API 尝试回调这个生产地址
- 你本地的服务器无法接收到回调
- `temp_tasks/{task_id}.json` 文件永远不会被创建
- 前端轮询一直返回 `PROCESSING` 状态

**现在的状态：**
- 回调URL现可通过环境变量 `CALLBACK_URL` 配置
- 支持本地开发和生产环境的不同配置

## 解决方案

### 方案一：使用生产地址（推荐用于演示测试）

如果你只是想快速测试功能，可以使用生产地址接收回调：

```bash
# 在 .env 文件中配置
CALLBACK_URL=https://redsong.bond/api/kie/callback
```

**优点：**
- 简单快速，无需额外配置
- 立即可用

**缺点：**
- 生成的歌曲会保存到生产服务器，本地 `temp_tasks` 目录为空
- 生产环境需要保持运行

### 方案二：使用 ngrok 创建公网访问（推荐用于本地开发）

为本地服务器创建公网访问地址，让 Kie API 能够回调到你本地的服务器：

#### 1. 安装 ngrok

```bash
# macOS
brew install ngrok

# Linux
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin

# Windows
# 从 https://ngrok.com/download 下载并安装
```

#### 2. 启动 Flask 应用

```bash
cd /mnt/c/my_project/competition/深信服AI比赛/redsong_system
python3 app.py
```

#### 3. 在另一个终端启动 ngrok

```bash
ngrok http 5000
```

你会看到类似输出：

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:5000
```

#### 4. 配置 .env 文件

```bash
CALLBACK_URL=https://abc123.ngrok-free.app/api/kie/callback
```

**注意：** 将 `abc123.ngrok-free.app` 替换为你实际的 ngrok 地址

#### 5. 重启 Flask 应用

由于 `.env` 文件已更新，需要重启应用：

```bash
# 按 Ctrl+C 停止当前应用
python3 app.py
```

**优点：**
- 完整的本地开发体验
- 生成的歌曲保存在本地 `temp_tasks` 目录
- 可以调试验证回调处理逻辑

**缺点：**
- 需要安装和配置 ngrok
- ngrok 免费版地址每次启动会变化

### 方案三：直接使用轮询方式（无需回调）

修改代码，不使用回调机制，而是通过轮询 Kie API 状态：

这个方案需要修改 Kie API 的调用逻辑，将异步回调改为同步轮询或主动获取结果。

**优点：**
- 不需要公网访问地址
- 避免回调超时问题

**缺点：**
- 需要修改大量代码
- 用户体验可能受影响（需手动轮询）

## 调试步骤

### 1. 检查环境变量配置

```bash
# 查看 .env 文件配置
cat .env | grep CALLBACK_URL
```

### 2. 验证回调URL是否可访问

```bash
# 如果使用 ngrok，测试地址是否可访问
curl https://abc123.ngrok-free.app/api/kie/callback
```

### 3. 查看服务器日志

```bash
# 查看应用日志，确认是否收到回调
tail -f server.log
```

或者查看终端输出，查找 `api_kie_callback` 的日志

### 4. 检查 temp_tasks 目录

```bash
# 查看是否有生成的任务文件
ls -la temp_tasks/
```

如果有 `{task_id}.json` 文件，说明回调成功。

### 5. 手动测试回调接口

```bash
# 模拟 Kie API 的回调请求
curl -X POST http://localhost:5000/api/kie/callback \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "task_id": "test123",
      "data": [
        {
          "audio_url": "https://example.com/song.mp3"
        }
      ]
    }
  }'
```

### 6. 检查浏览器控制台

打开浏览器开发者工具（F12），查看 Network 标签：

- 查看 `POST /api/create/song/start` 请求是否成功（返回 task_id）
- 查看 `GET /api/create/song/status/{task_id}` 轮询请求
- 检查是否有错误信息

## 常见错误排查

### 错误 1: "Kie API Key未配置"

**原因：** `.env` 文件中未配置 `KIE_API_KEY`

**解决：**
```bash
# 确保在 .env 文件中配置了 KIE_API_KEY
KIE_API_KEY=your_key_here
```

### 错误 2: "连接失败: 无法访问Kie接口"

**原因：** 网络问题或 API 地址配置错误

**解决：**
```bash
# 检查 KIE_API_HOST 配置
cat .env | grep KIE_API_HOST
```

### 错误 3: "API权限错误: 本地IP不在白名单"

**原因：** Kie API 的 IP 白名单限制

**解决：**
- 登录 Kie.ai 后台
- 将本地公网 IP 或 ngrok 服务器 IP 添加到白名单
- 或联系 Kie.ai 客服解决

### 错误 4: 前端一直显示"正在生成中"

**原因：** 回调未成功执行

**解决：**
1. 检查 `temp_tasks` 目录是否有生成的文件
2. 查看服务器日志是否收到回调请求
3. 确认 `CALLBACK_URL` 配置正确且可访问

## 代码修改说明

### 修改 1: app.py

添加了 `CALLBACK_URL` 配置项：

```python
class Config:
    # ...
    CALLBACK_URL = os.getenv(
        "CALLBACK_URL", "https://redsong.bond/api/kie/callback"
    )
```

修改了 `/api/create/song/start` 路由：

```python
@app.route("/api/create/song/start", methods=["POST"])
def api_create_song_start():
    # ...
    p = {
        # ...
        "callBackUrl": app.config.get("CALLBACK_URL"),
    }
    # ...
```

### 修改 2: .env.example

添加了回调URL配置说明：

```bash
# 回调URL配置
CALLBACK_URL=https://redsong.bond/api/kie/callback
```

## 最佳实践

### 开发环境

- 使用 ngrok 创建稳定的公网访问
- 配置本地 `CALLBACK_URL` 指向 ngrok 地址
- 保持 ngrok 会话活跃

### 生产环境

- 使用固定的域名（如 `https://redsong.bond`）
- 配置 HTTPS 证书
- 确保 API 白名单配置正确

### 测试建议

1. 先测试 Kie API 是否可正常调用（检查 task_id 是否成功返回）
2. 再测试回调机制是否正常工作（检查 temp_tasks 目录）
3. 最后测试前端轮询和显示（检查浏览器控制台）

## 相关文件

- `app.py` - 主应用文件，包含回调处理逻辑
- `.env` - 环境变量配置文件
- `.env.example` - 环境变量配置模板
- `temp_tasks/` - 存储回调结果的临时目录
- `templates/creation.html` - 前端红歌创作页面

## 技术支持

如果问题仍未解决，请检查：

1. 服务器日志: `server.log`
2. 应用终端输出（直接运行时的日志）
3. 浏览器开发者工具（F12 → Network）
4. Kie API 后台的调用记录

确保每一步都正常工作后再继续下一步。