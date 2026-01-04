#!/bin/bash

# --- 配置 ---
IMAGE_NAME="redsong-system"
DOCKER_USER="webliu"  # 请修改为你的 Docker Hub 用户名
TAG="test"

FULL_IMAGE_NAME="$DOCKER_USER/$IMAGE_NAME:$TAG"

echo "=== 1. 准备构建多架构 Docker 镜像: $FULL_IMAGE_NAME ==="
echo "目标平台: linux/amd64 (标准服务器) 和 linux/arm64 (Apple Silicon/M1/M2)"
echo "注意：多架构构建需要使用 buildx，且构建完成后会自动推送到 Docker Hub。"
echo "请确保你已经运行过 'docker login'。"

read -p "按回车键开始构建并推送，或按 Ctrl+C 取消..."

# 检查 buildx 是否可用
if docker buildx version >/dev/null 2>&1; then
    echo "检测到 buildx，准备进行多架构构建..."
    
    # 检查并创建 buildx builder (如果需要)
    if ! docker buildx inspect redsong_builder > /dev/null 2>&1; then
        echo "创建新的 buildx 构建器: redsong_builder"
        docker buildx create --name redsong_builder --use
    else
        echo "使用现有的 buildx 构建器: redsong_builder"
        docker buildx use redsong_builder
    fi

    echo "=== 2. 开始构建并推送 (这可能需要几分钟) ==="
    docker buildx build --platform linux/amd64,linux/arm64 -t $FULL_IMAGE_NAME --push .

else
    echo "警告: 未检测到 'docker buildx' 插件。"
    echo "将降级为标准构建 (仅构建当前架构) 并推送。"
    
    echo "=== 2. 开始构建并推送 (这可能需要几分钟) ==="
    docker build -t $FULL_IMAGE_NAME .
    docker push $FULL_IMAGE_NAME
fi

if [ $? -ne 0 ]; then
    echo "构建或推送失败！请检查 Docker 运行状态及网络连接。"
    exit 1
fi

echo "=== 3. 完成！ ==="
echo "镜像已推送到 Docker Hub，支持多架构。"
echo "本地运行 (Docker 会自动拉取适配你本机架构的版本):"
echo "docker run -d -p 5000:5000 $FULL_IMAGE_NAME"