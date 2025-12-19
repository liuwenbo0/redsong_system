#!/bin/bash

# 数智红韵网 - 本地部署脚本
# 作者: AI Assistant
# 版本: 1.0

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查Python版本
check_python() {
    log_info "检查Python环境..."
    
    if ! command_exists python3; then
        log_error "Python 3 未安装。请先安装Python 3.8+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.8"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        log_error "Python版本过低。当前版本: $PYTHON_VERSION, 要求: $REQUIRED_VERSION+"
        exit 1
    fi
    
    log_success "Python版本检查通过: $PYTHON_VERSION"
}

# 创建虚拟环境
create_venv() {
    log_info "创建Python虚拟环境..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "虚拟环境创建完成"
    else
        log_warning "虚拟环境已存在，跳过创建"
    fi
}

# 激活虚拟环境
activate_venv() {
    log_info "激活虚拟环境..."
    source venv/bin/activate
    log_success "虚拟环境已激活"
}

# 安装依赖
install_dependencies() {
    log_info "安装Python依赖包..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "依赖包安装完成"
    else
        log_error "requirements.txt 文件不存在"
        exit 1
    fi
}

# 检查和创建环境变量文件
setup_env() {
    log_info "设置环境变量..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "已从 .env.example 创建 .env 文件"
            log_warning "请编辑 .env 文件，填入您的API密钥"
            echo
            echo "必需的API密钥:"
            echo "- OPENROUTER_API_KEY: OpenRouter API密钥"
            echo "- KIE_API_KEY: Kie.ai API密钥"
            echo
            read -p "是否现在编辑 .env 文件? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                ${EDITOR:-nano} .env
            fi
        else
            log_error ".env.example 文件不存在"
            exit 1
        fi
    else
        log_success ".env 文件已存在"
    fi
}

# 检查数据库
check_database() {
    log_info "检查数据库..."
    
    if [ ! -f "project.db" ]; then
        log_info "数据库文件不存在，将在首次运行时自动创建"
    else
        log_success "数据库文件存在"
    fi
}

# 测试应用启动
test_app() {
    log_info "测试应用启动..."
    
    # 导入Flask应用测试
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from app import create_app
    app = create_app()
    print('Flask应用创建成功')
except Exception as e:
    print(f'Flask应用创建失败: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "应用测试通过"
    else
        log_error "应用测试失败"
        exit 1
    fi
}

# 创建启动脚本
create_start_script() {
    log_info "创建启动脚本..."
    
    cat > start.sh << 'EOF'
#!/bin/bash
# 数智红韵网启动脚本

# 激活虚拟环境
source venv/bin/activate

# 设置环境变量
export FLASK_APP=app.py

# 启动应用
echo "正在启动数智红韵网..."
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务"
echo

python app.py
EOF
    
    chmod +x start.sh
    log_success "启动脚本 start.sh 创建完成"
}

# 创建Gunicorn启动脚本
create_gunicorn_script() {
    log_info "创建Gunicorn启动脚本..."
    
    cat > start_gunicorn.sh << 'EOF'
#!/bin/bash
# 数智红韵网 Gunicorn启动脚本

# 激活虚拟环境
source venv/bin/activate

# 设置环境变量
export FLASK_APP=app.py

# 启动Gunicorn
echo "正在使用Gunicorn启动数智红韵网..."
echo "访问地址: http://localhost:8000"
echo "按 Ctrl+C 停止服务"
echo

gunicorn --workers 3 --bind 0.0.0.0:8000 app:app
EOF
    
    chmod +x start_gunicorn.sh
    log_success "Gunicorn启动脚本 start_gunicorn.sh 创建完成"
}

# 检查端口占用
check_port() {
    local port=$1
    if command_exists lsof; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
            log_warning "端口 $port 已被占用"
            return 1
        else
            return 0
        fi
    else
        log_info "无法检查端口占用 (lsof 未安装)"
        return 0
    fi
}

# 主函数
main() {
    echo "=========================================="
    echo "  数智红韵网 - 本地部署脚本"
    echo "=========================================="
    echo
    
    # 检查当前目录
    if [ ! -f "app.py" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 执行部署步骤
    check_python
    create_venv
    activate_venv
    install_dependencies
    setup_env
    check_database
    test_app
    create_start_script
    create_gunicorn_script
    
    echo
    log_success "部署完成！"
    echo
    echo "=========================================="
    echo "  启动方式:"
    echo "=========================================="
    echo "开发模式: ./start.sh"
    echo "生产模式: ./start_gunicorn.sh"
    echo "=========================================="
    echo
    
    # 检查端口并提示启动
    if check_port 5000; then
        log_info "端口5000可用，可以直接启动开发模式"
    else
        log_warning "端口5000被占用，请检查或使用其他端口"
    fi
    
    if check_port 8000; then
        log_info "端口8000可用，可以直接启动生产模式"
    else
        log_warning "端口8000被占用，请检查或使用其他端口"
    fi
    
    echo
    log_info "如需配置Nginx，请参考 README.md 中的生产环境部署指南"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi