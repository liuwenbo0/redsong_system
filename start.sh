#!/bin/bash
# 数智红韵网启动脚本

# 激活虚拟环境
source .venv/bin/activate

# 设置环境变量
export FLASK_APP=app.py
export PORT=5001

# 启动应用
echo "正在启动数智红韵网..."
echo "访问地址: http://localhost:5001"
echo "按 Ctrl+C 停止服务"
echo

python app.py
