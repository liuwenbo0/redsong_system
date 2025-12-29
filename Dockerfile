# 使用官方 Python 轻量级镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量 (防止 Python 生成 .pyc 文件，让输出直接打印到控制台)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖 (如果需要编译某些库，可能需要 gcc 等，这里先安装基础的)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 1. 先复制依赖文件 (利用 Docker 缓存层，如果 requirements.txt 没变，就不重新安装依赖)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn  # 生产环境使用 gunicorn 启动

# 2. 复制静态资源 (这部分最大，放在中间)
COPY static ./static
COPY templates ./templates

# 3. 复制剩余的项目代码
COPY . .

# 暴露端口
EXPOSE 5000

# 启动命令 (使用 Gunicorn 启动 Flask)
# -w 4: 4个工作进程
# -b 0.0.0.0:5000: 绑定端口
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
