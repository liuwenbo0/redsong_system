#!/bin/bash

# --- 配置 ---
IMAGE_NAME="redsong-system"
DOCKER_USER="webliu"  # 请修改为你的 Docker Hub 用户名
TAG="test"

FULL_IMAGE_NAME="$DOCKER_USER/$IMAGE_NAME:$TAG"

echo "=== 1. 开始构建 Docker 镜像: $FULL_IMAGE_NAME ==="
# --platform linux/amd64 确保在 Mac M1/M2 上构建出通用的 x86 镜像，兼容大多数服务器
# --no-cache 防止复用本地 ARM64 架构的缓存层导致构建失败
docker build --no-cache --platform linux/amd64 -t $FULL_IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "构建失败！"
    exit 1
fi

echo "=== 2. 准备推送到 Docker Hub ==="
echo "请确保你已经运行过 'docker login'"
read -p "按回车键继续推送，或按 Ctrl+C 取消..."

docker push $FULL_IMAGE_NAME

echo "=== 3. 完成！ ==="
echo "用户可以使用以下命令拉取并运行："
echo "docker run -d -p 5000:5000 $FULL_IMAGE_NAME"
