#!/bin/bash
set -e

# 数智红韵网 Docker 启动脚本 (支持 ngrok)

# 加载 .env 环境变量 (如果存在)
if [ -f .env ]; then
    echo ">>> 加载 .env 配置文件..."
    # 导出所有非注释行
    export $(grep -v '^#' .env | xargs)
fi

# 1. 尝试配置并启动 ngrok
if [ -n "$NGROK_AUTHTOKEN" ]; then
    echo ">>> 检测到 NGROK_AUTHTOKEN，正在配置 ngrok..."
    
    # 添加 auth token (即使已存在也覆盖，确保是新的)
    ngrok config add-authtoken "$NGROK_AUTHTOKEN" > /dev/null

    # 构建 ngrok 命令
    # 默认绑定到本地 5000 端口，或者环境变量 PORT
    TARGET_PORT=${PORT:-5000}
    # 必须清除代理设置，否则免费版 ngrok 会报错 ERR_NGROK_9009
    NGROK_CMD="env -u HTTP_PROXY -u HTTPS_PROXY ngrok http ${TARGET_PORT} --log=stdout"
    
    # 支持在环境变量中配置固定的 Domain (如果用户有)
    if [ -n "$NGROK_DOMAIN" ]; then
        echo ">>> 使用固定域名: $NGROK_DOMAIN"
        NGROK_CMD="$NGROK_CMD --domain=$NGROK_DOMAIN"
    fi

    # 后台启动 ngrok
    echo ">>> 启动 ngrok..."
    $NGROK_CMD > ngrok.log 2>&1 &
    
    # 等待 ngrok 初始化
    echo ">>> 等待 ngrok 连接..."
    sleep 5
    
    # 从本地 API 获取公网 URL
    # 尝试 5 次
    for i in {1..5}; do
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')
        if [ "$NGROK_URL" != "null" ] && [ -n "$NGROK_URL" ]; then
            break
        fi
        echo ">>> 等待获取 URL ($i/5)..."
        sleep 2
    done

    if [ "$NGROK_URL" != "null" ] && [ -n "$NGROK_URL" ]; then
        export CALLBACK_URL="${NGROK_URL}/api/kie/callback"
        
        echo "============================================================"
        echo " Ngrok 启动成功!"
        echo " 公网地址 (Public URL): $NGROK_URL"
        echo " 回调地址 (Callback URL): $CALLBACK_URL"
        echo "============================================================"
    else
        echo "!!! 警告: 无法启动 ngrok 或获取 URL。请检查 ngrok.log:"
        cat ngrok.log
        echo "!!! 将使用默认或已配置的 CALLBACK_URL"
    fi
else
    echo ">>> 未检测到 NGROK_AUTHTOKEN，跳过 ngrok 配置。"
fi

# 2. 启动主应用
# 逻辑：优先使用 Gunicorn。如果失败（崩溃或未安装），则回退到 Python 原生启动。
TARGET_PORT=${PORT:-5000}
echo ">>> 准备启动应用 (端口: $TARGET_PORT)..."

if command -v gunicorn >/dev/null 2>&1; then
    echo ">>> 正在使用 Gunicorn 启动..."
    # 运行 gunicorn。如果它以非零状态退出（崩溃），if 条件成立，执行回退逻辑。
    # 正常停止（Ctrl+C）通常返回 0，不会触发回退。
    if ! gunicorn --workers 3 --bind 0.0.0.0:$TARGET_PORT app:app; then
        echo ">>> 警告: Gunicorn 启动失败或异常退出。"
        echo ">>> 正在尝试切换到 Python 原生启动模式..."
        exec python app.py
    else
        echo ">>> Gunicorn 已正常停止。"
    fi
else
    echo ">>> 未检测到 Gunicorn，直接使用 Python 启动..."
    exec python app.py
fi
