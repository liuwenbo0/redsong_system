# 使用官方 Python 轻量级镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量 (防止 Python 生成 .pyc 文件，让输出直接打印到控制台)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 合并安装命令：系统依赖 + ngrok + 清理
# 这样做可以将所有安装过程压缩在一个镜像层中，并在该层结束前清理掉缓存，极大减少体积
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    curl \
    jq \
    gnupg \
    unzip \
    # --- 开始配置 ngrok 源 ---
    && mkdir -p /etc/apt/keyrings \
    && curl -sS https://ngrok-agent.s3.amazonaws.com/ngrok.asc | gpg --dearmor -o /etc/apt/keyrings/ngrok.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/ngrok.gpg] https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list \
    # --- 安装 ngrok ---
    && apt-get update \
    && apt-get install -y ngrok \
    # --- 清理缓存 (关键步骤) ---
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 1. 先复制依赖文件
COPY requirements.txt .

# 合并 pip 安装命令
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

# 复制启动脚本
COPY start_with_ngrok.sh /start_with_ngrok.sh
RUN chmod +x /start_with_ngrok.sh

# 2. 复制静态资源
COPY static ./static
COPY templates ./templates

# 3. 复制剩余的项目代码
COPY . .

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["/start_with_ngrok.sh"]
