#!/bin/bash
set -e

# 数智红韵网 - Docker 一键启动脚本
# 功能：自动构建镜像并启动容器，支持从 .env 读取配置（包括 ngrok）

echo "=== 数智红韵网 Docker 启动向导 ==="

# 1. 检查 .env 文件
if [ ! -f .env ]; then
    echo "错误: 未找到 .env 配置文件。"
    echo "请先创建 .env 文件 (参考 .env.example)"
    exit 1
fi

# 2. 检查 NGROK 配置提醒
if ! grep -q "NGROK_AUTHTOKEN" .env; then
    echo "提示: .env 中未检测到 NGROK_AUTHTOKEN。"
    echo "如果需要外网回调功能，请在 .env 中添加: NGROK_AUTHTOKEN=your_token"
    echo "按回车继续，或 Ctrl+C 退出修改..."
    read -r
fi

# 3. 构建镜像
echo "正在构建 Docker 镜像 (redsong-system:latest)..."
docker build -t redsong-system:latest .

# 4. 启动容器
echo "正在启动容器..."
echo "-------------------------------------------------------"
echo "本地访问: http://localhost:5000"
echo "日志将显示在下方 (包含 ngrok 公网地址)..."
echo "按 Ctrl+C 停止"
echo "-------------------------------------------------------"

# 使用 --env-file 将本地 .env 配置全部注入容器
docker run -it --rm \
  -p 5001:5000 \
  --env-file .env \
  redsong-system:latest
