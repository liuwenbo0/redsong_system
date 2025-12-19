<!-- 自动生成：为 AI 编码代理提供此仓库的快速入门知识 -->
# 红歌项目 — Copilot 使用说明（精简版）

本文件向 AI 编码代理（Copilot/agent）提供在此仓库中立即上手所需的可执行、可验证知识点。

**Big Picture**
- **应用类型**: 单体 Flask 应用（入口 `app.py`），使用工厂模式 (`create_app`) 并在文件底部创建了 `app` 实例用于直接启动。
- **部署架构**: 开发可用 `python3 app.py`；生产使用 `gunicorn --bind 127.0.0.1:8000 app:app` + Nginx 反向代理（详见 `ReadMe.md`）。
- **持久化**: SQLite（默认 `project.db`），数据库模型和所有 DB 操作封装在 `database.py` 的 `DataService` 中。
- **异步/回调点**: 第三方音乐服务 Kie.ai 的生成通过回调写入 `temp_tasks/<task_id>.json`（参见 `app.py` 的 `/api/kie/callback` 与 `/api/create/song/status/<task_id>`）。

**关键文件 & 作用**
- `app.py`: 应用工厂、路由注册、第三方 API（OpenRouter/Kie.ai）调用封装、认证（Flask-Login）、CORS（`supports_credentials=True`）等。
- `database.py`: SQLAlchemy 模型、`DataService`（所有 DB 操作封装）、`init_db()` 和 `register_commands(app)`（注册 `flask init-db` CLI）。
- `ReadMe.md`: 部署与运行（production 使用 gunicorn + nginx + systemd），包含常用命令示例。
- `requirements.txt`: 依赖清单（包含指定的 torch wheel 备注），安装时注意 CUDA 版本兼容。
- `restart.sh`: 简单 systemd 重启脚本，示例如何使用 `systemctl` 管理服务。
- `templates/` 与 `static/`: 前端页面与静态资源，Nginx 可直接提供 `/static` 路径以提升性能。

**项目约定 / 重要模式**
- **封装 DB 操作**: 所有数据库查询/修改通过 `DataService`，调用方通常传入 `current_user` 或 `user_id` 来判断收藏/点赞等状态。
- **接口风格**: 所有后端对外接口返回 JSON（`/api/*` 路径），页面路由直接返回模板（`/`, `/circle`, `/creation` 等）。
- **第三方 AI 调用**: `_call_openrouter_api()` 为统一的 OpenRouter 调用点；`generate_openrouter_content()` 返回纯文本。若期待 JSON，请使用 `response_format={"type": "json_object"}` 并在调用端做容错（仓库示例会清理 markdown 后再 json.loads）。
- **Kie.ai 任务流**: `POST /api/create/song/start` -> Kie.ai 返回 `taskId` -> Kie.ai 回调写入 `temp_tasks/<taskId>.json` -> 前端轮询 `GET /api/create/song/status/<taskId>`。代理修改/调试时请保留该文件缓存模式。
- **登录/会话**: 使用 `flask_login`，`login_user`/`current_user` 在很多 `DataService` 操作中被依赖；CORS 中 `supports_credentials=True` 对前端会话维持关键。

**常用开发/运行命令（可验证）**
- 本地开发（快速启动）: `python3 app.py`（会在 `0.0.0.0:5000` 启动）
- 使用 Flask CLI:
  - `export FLASK_APP=app.py`
  - `python3 -m flask init-db`  # 由 `database.register_commands` 提供，创建并填充初始数据
- 生产模拟（单机）: `gunicorn --bind 127.0.0.1:8000 app:app`
- systemd 管理: `sudo systemctl start|stop|status red_song_project.service`（ReadMe 提供示例 systemd unit）

**可试的 API 示例（curl）**
- 注册用户:
  - `curl -X POST -H "Content-Type: application/json" -d '{"username":"u","password":"P1w2","confirm_password":"P1w2"}' http://127.0.0.1:5000/api/auth/register`
- AI 聊天（前端会话中发送）:
  - `curl -X POST -H "Content-Type: application/json" -d '{"question":"红歌有什么代表性？"}' http://127.0.0.1:5000/api/song/chat`
- 开始作曲任务:
  - `curl -X POST -H "Content-Type: application/json" -d '{"lyrics":"我的家乡","title":"新歌"}' http://127.0.0.1:5000/api/create/song/start`

**注意与防坑指南（仅记录可验证事实）**
- `Config` 在 `app.py` 中包含示例 API Key 字段（`OPENROUTER_API_KEY`, `KIE_API_KEY`）。仓库中直接硬编码示例密钥 — 在真实协作中请将密钥移至环境变量或 secrets 管理（但这是仓库当前可见的事实）。
- 回调写文件路径 `temp_tasks/`：变更该逻辑时务必保持文件命名约定 `<taskId>.json`，并保证 Flask 运行用户对该目录有读写权限。
- 对 OpenRouter 的调用有多处容错（返回 code 401/402/500 的处理），当修改核心调用 `_call_openrouter_api()` 时，请保留错误码分支以免破坏上层调用假设。
- 时间与时区: `database.py` 使用 `Asia/Shanghai`（CST）格式化时间戳，前端依赖这个格式进行展示。

如果需要，我可以：
- 把上述内容细化为更详细的 `AGENT.md`（包含更多调用示例与调试命令），或
- 将 README 中的部署 systemd 单元模板自动改写为更通用的示例。

请告知哪些部分需要补充或修正（例如：私钥/环境变量约定、CI 流水线、测试命令等）。
