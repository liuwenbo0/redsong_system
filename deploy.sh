#!/bin/bash

# 数智红韵网 - 本地部署脚本 (macOS/Linux with uv)
# 版本: 2.0 (uv adaptation)

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

# 准备系统基础环境
prepare_system() {
    local sys_type="unknown"
    if command_exists apt-get; then sys_type="apt"; fi
    if command_exists apk; then sys_type="apk"; fi
    if command_exists dnf; then sys_type="dnf"; elif command_exists yum; then sys_type="yum"; fi

    if [ "$sys_type" != "unknown" ]; then
        log_info "检测到包管理器: $sys_type，正在检查基础依赖..."
        
        # 定义通用依赖名，特定系统可能需要映射
        # 核心依赖: curl, python3, pip, venv, jq
        local deps=("curl" "python3" "jq")
        # 根据系统差异调整包名或添加特定包
        case $sys_type in
            apt)
                deps+=("python3-venv" "python3-pip")
                ;;
            apk)
                # Alpine 分得比较细
                deps+=("py3-pip" "py3-virtualenv")
                ;;
            dnf|yum)
                # RHEL 系通常 python3 自带 venv，但有时需要单独装
                # 尝试通用的 python3-pip，有些旧版可能需要 python3-devel
                deps+=("python3-pip") 
                ;;
        esac

        local missing_deps=()
        for dep in "${deps[@]}"; do
            if ! command_exists "$dep"; then
                # 简单的命令名检查可能不准确 (例如 py3-pip 对应命令 pip3)
                # 这里主要依赖包管理器去尝试安装，不做过于严格的预检
                missing_deps+=("$dep")
            fi
        done

        # 只要不是全齐，就尝试运行安装命令 (包管理器通常会自动跳过已安装的)
        if [ ${#missing_deps[@]} -eq 0 ] && command_exists python3 && command_exists curl; then
             log_success "基础依赖看起来已就绪"
             return
        fi
        
        log_info "正在尝试安装/更新依赖..."
        case $sys_type in
            apt)
                cmd_prefix=""
                if [ "$EUID" -ne 0 ] && command_exists sudo; then cmd_prefix="sudo"; fi
                $cmd_prefix apt-get update
                $cmd_prefix apt-get install -y "${deps[@]}"
                ;;
            apk)
                # Alpine 通常是 root 运行
                apk update
                apk add --no-cache "${deps[@]}"
                ;;
            dnf)
                $cmd_prefix dnf install -y "${deps[@]}"
                ;;
            yum)
                $cmd_prefix yum install -y "${deps[@]}"
                ;;
        esac
    else
        log_warning "未识别的 Linux 发行版，跳过自动依赖安装。请确保已安装 curl 和 Python3。"
    fi
}

# 检查并安装 curl (保留作为兼容性检查)
check_curl() {
    if ! command_exists curl; then
        prepare_system
    fi
}

# 检查uv是否安装
check_uv() {
    log_info "检查uv环境..."
    if ! command_exists uv; then
        log_warning "uv 未安装。尝试安装 uv..."
        if command_exists brew; then
            brew install uv
        else
            curl -LsSf https://astral.sh/uv/install.sh | sh
            # 某些系统安装后需要加载路径
            if [ -f "$HOME/.cargo/env" ]; then
                source "$HOME/.cargo/env"
            fi
        fi
        
        # 再次检查路径，如果 sh 安装后不在 PATH 中，尝试常见路径
        if ! command_exists uv && [ -f "$HOME/.local/bin/uv" ]; then
            export PATH="$HOME/.local/bin:$PATH"
        fi

        if ! command_exists uv; then
             log_error "uv 安装失败，请手动安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
             exit 1
        fi
    fi
    log_success "uv 已安装: $(uv --version)"
}

# 创建虚拟环境 (使用 uv)
create_venv() {
    log_info "创建Python虚拟环境 (.venv)..."
    
    # 检查 venv 是否真的有效 (通过检查配置文件)，而不仅是检查目录存在
    if [ ! -f ".venv/pyvenv.cfg" ]; then
        uv venv .venv
        log_success "虚拟环境创建完成"
    else
        log_warning "虚拟环境 .venv 已存在且有效，跳过创建"
    fi
}

# 激活虚拟环境 (仅用于当前 shell 上下文，脚本内部使用完整路径)
activate_venv() {
    log_info "检查虚拟环境..."
    if [ ! -f ".venv/bin/activate" ]; then
        log_error "虚拟环境未找到，请检查创建步骤"
        exit 1
    fi
    # source .venv/bin/activate  # 在脚本中source不一定影响父shell，主要依靠路径调用
}

# 安装依赖 (使用 uv)
install_dependencies() {
    log_info "安装Python依赖包 (via uv)..."
    
    if [ -f "requirements.txt" ]; then
        # 使用虚拟环境中的 pip
        uv pip install -p .venv -r requirements.txt
        log_success "依赖包安装完成"
    else
        log_error "requirements.txt 文件不存在"
        exit 1
    fi
}

# 检查和创建环境变量文件
setup_env() {
    log_info "检查环境变量..."
    
    if [ ! -f ".env" ]; then
        log_error ".env 文件不存在！请确保项目包含 .env 文件。"
        # 不强制退出，允许用户手动解决
    else
        log_success ".env 文件已存在"
    fi
}

# 检查数据库
check_database() {
    log_info "检查数据库..."
    
    if [ ! -f "instance/project.db" ] && [ ! -f "project.db" ]; then
        log_info "数据库文件不存在，将在首次运行时自动创建"
    else
        log_success "数据库文件存在"
    fi
}

# 测试应用启动
test_app() {
    log_info "测试应用启动..."
    
    # 使用虚拟环境的 python
    ./.venv/bin/python3 -c "
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


# 检查并安装 ngrok (仅 Linux/apt)
install_ngrok() {
    if command_exists ngrok; then
        return 0
    fi
    
    if [ "$(uname)" == "Linux" ] && command_exists apt-get; then
        log_info "正在安装 ngrok..."
        
        # 添加 ngrok GPG key 和源
        if ! [ -f /etc/apt/keyrings/ngrok.gpg ]; then
            if [ "$EUID" -ne 0 ] && command_exists sudo; then
                sudo mkdir -p /etc/apt/keyrings
                curl -sS https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo gpg --dearmor -o /etc/apt/keyrings/ngrok.gpg
                echo "deb [signed-by=/etc/apt/keyrings/ngrok.gpg] https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
                sudo apt-get update
                sudo apt-get install -y ngrok
            else
                mkdir -p /etc/apt/keyrings
                curl -sS https://ngrok-agent.s3.amazonaws.com/ngrok.asc | gpg --dearmor -o /etc/apt/keyrings/ngrok.gpg
                echo "deb [signed-by=/etc/apt/keyrings/ngrok.gpg] https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list
                apt-get update
                apt-get install -y ngrok
            fi
        fi
        
        if command_exists ngrok; then
            log_success "ngrok 安装成功"
        else
            log_warning "ngrok 安装失败，请稍后手动安装"
        fi
    fi
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
        # macOS 通常有 lsof，如果没有则跳过检查
        return 0
    fi
}

# 主函数
main() {
    echo "=========================================="
    echo "  数智红韵网 - 本地部署脚本 (uv版)"
    echo "=========================================="
    echo
    
    # 检查当前目录
    if [ ! -f "app.py" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 执行部署步骤
    prepare_system
    check_curl
    check_uv
    create_venv
    # activate_venv # 脚本中不需要 source，直接引用路径
    install_dependencies
    setup_env
    check_database
    test_app
    
    # 安装 ngrok (如果需要)
    install_ngrok
    
    # 额外工具检查
    log_info "检查辅助工具..."
    if ! command_exists jq; then
        log_warning "未检测到 'jq'。start_with_ngrok.sh 需要 jq 来解析 ngrok URL。"
        log_info "推荐安装: brew install jq (macOS) 或 apt install jq (Linux)"
    fi
    if ! command_exists ngrok; then
        log_warning "未检测到 'ngrok'。如果需要外网访问，请安装 ngrok。"
    fi
    
    # 赋予脚本执行权限
    chmod +x start_with_ngrok.sh build_and_push.sh
    
    # 获取端口配置
    APP_PORT=5000
    if [ -f ".env" ]; then
        # 尝试从 .env 读取 PORT，忽略注释
        ENV_PORT=$(grep "^PORT=" .env | cut -d '=' -f2 | tr -d '[:space:]')
        if [ -n "$ENV_PORT" ]; then
            APP_PORT=$ENV_PORT
        fi
    fi
    
    echo
    log_success "部署完成！"
    echo
    echo "=========================================="
    echo "  启动方式:"
    echo "=========================================="
    echo "运行以下脚本启动应用 (支持 ngrok):"
    echo "   ./start_with_ngrok.sh"
    echo
    echo "启动后，您可以通过以下地址访问:"
    echo "   本地访问: http://localhost:$APP_PORT"
    echo "=========================================="
    echo
    
    # 检查端口并提示启动
    if check_port $APP_PORT; then
        log_info "端口$APP_PORT 可用，可以直接启动应用"
    else
        log_warning "端口$APP_PORT 被占用！"
        log_info "请修改 .env 文件中的 PORT 变量更换为其他可用端口 (例如: PORT=$((APP_PORT + 1)))"
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
