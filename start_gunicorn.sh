#!/bin/bash
# 数智红韵网 Gunicorn启动脚本

# 激活虚拟环境
source .venv/bin/activate

# 设置环境变量
export FLASK_APP=app.py

# 启动Gunicorn
echo "正在使用Gunicorn启动数智红韵网..."
echo "访问地址: http://localhost:8000"
echo "按 Ctrl+C 停止服务"
echo

gunicorn --workers 3 --bind 0.0.0.0:8000 app:app
