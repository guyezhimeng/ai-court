#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     🏛️  AI 朝廷 · 三省六部 · 一键部署脚本                  ║"
    echo "║                                                           ║"
    echo "║     内置聊天框 + 看板 + 多Agent协作 + Token优化            ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

install_docker() {
    log_info "检测到未安装 Docker，正在安装..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y ca-certificates curl gnupg
            install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            chmod a+r /etc/apt/keyrings/docker.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        centos|rhel|alinux)
            yum install -y yum-utils
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        *)
            log_error "不支持的操作系统: $OS"
            log_info "请手动安装 Docker: https://docs.docker.com/engine/install/"
            exit 1
            ;;
    esac
    
    systemctl start docker
    systemctl enable docker
    log_info "Docker 安装完成"
}

install_git() {
    log_info "检测到未安装 Git，正在安装..."
    
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y git
    elif command -v yum &> /dev/null; then
        yum install -y git
    else
        log_error "无法自动安装 Git，请手动安装"
        exit 1
    fi
    log_info "Git 安装完成"
}

clone_or_update() {
    local REPO_URL="$1"
    local TARGET_DIR="$2"
    
    if [ -d "$TARGET_DIR/.git" ]; then
        log_info "项目已存在，正在更新..."
        cd "$TARGET_DIR"
        git pull
    else
        log_info "正在克隆项目..."
        git clone "$REPO_URL" "$TARGET_DIR"
        cd "$TARGET_DIR"
    fi
}

configure_env() {
    local ENV_FILE="$1"
    
    if [ -f "$ENV_FILE" ]; then
        log_info "检测到已有 .env 文件"
        read -p "是否重新配置？(y/N): " RECONFIG
        if [[ ! "$RECONFIG" =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    log_info "开始配置环境变量..."
    
    read -p "请输入 LLM API URL (默认: https://api.openai.com/v1): " API_URL
    API_URL=${API_URL:-https://api.openai.com/v1}
    
    read -p "请输入 LLM API Key: " API_KEY
    while [ -z "$API_KEY" ]; do
        log_error "API Key 不能为空"
        read -p "请输入 LLM API Key: " API_KEY
    done
    
    read -p "请输入默认模型 (默认: gpt-4o-mini): " MODEL
    MODEL=${MODEL:-gpt-4o-mini}
    
    read -p "请输入应用端口 (默认: 80): " APP_PORT
    APP_PORT=${APP_PORT:-80}
    
    read -p "是否配置阿里云 OSS？(y/N): " USE_OSS
    if [[ "$USE_OSS" =~ ^[Yy]$ ]]; then
        read -p "OSS Endpoint: " OSS_ENDPOINT
        read -p "OSS Bucket: " OSS_BUCKET
        read -p "OSS Access Key: " OSS_ACCESS_KEY
        read -p "OSS Secret Key: " OSS_SECRET_KEY
    fi
    
    cat > "$ENV_FILE" << EOF
# AI 朝廷配置文件
# 由 install.sh 自动生成

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=aicourt
POSTGRES_PASSWORD=aicourt_secret_$(openssl rand -hex 8)
POSTGRES_DB=aicourt

REDIS_URL=redis://redis:6379/0

APP_PORT=8000
APP_SECRET_KEY=$(openssl rand -hex 32)
APP_DEBUG=false

LLM_API_URL=$API_URL
LLM_API_KEY=$API_KEY
LLM_MODEL=$MODEL

UPLOAD_DIR=/app/uploads
UPLOAD_MAX_SIZE_MB=20

STALL_THRESHOLD_SEC=180
MAX_DISPATCH_RETRY=3
DISPATCH_TIMEOUT_SEC=300

OSS_ENABLED=${USE_OSS:-false}
OSS_ENDPOINT=${OSS_ENDPOINT:-}
OSS_BUCKET=${OSS_BUCKET:-}
OSS_ACCESS_KEY=${OSS_ACCESS_KEY:-}
OSS_SECRET_KEY=${OSS_SECRET_KEY:-}
EOF
    
    chmod 600 "$ENV_FILE"
    log_info "配置文件已保存到 $ENV_FILE"
}

start_services() {
    log_info "正在启动服务..."
    
    docker compose pull 2>/dev/null || docker-compose pull 2>/dev/null
    
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose up -d --build
    elif command -v docker-compose &> /dev/null; then
        docker-compose up -d --build
    else
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    log_info "等待服务启动..."
    sleep 10
    
    log_info "检查服务状态..."
    docker compose ps 2>/dev/null || docker-compose ps 2>/dev/null
}

show_success() {
    local PORT="$1"
    
    echo ""
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║              ✅ AI 朝廷部署成功！                         ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo -e "  🌐 访问地址: ${BLUE}http://$(curl -s ifconfig.me 2>/dev/null || echo '服务器IP'):${PORT}${NC}"
    echo ""
    echo "  📋 常用命令:"
    echo "     查看日志:   docker compose logs -f"
    echo "     重启服务:   docker compose restart"
    echo "     停止服务:   docker compose down"
    echo "     更新部署:   git pull && docker compose up -d --build"
    echo ""
    echo "  📚 文档: https://github.com/guyezhimeng/ai-court"
    echo ""
}

main() {
    print_banner
    
    local REPO_URL="https://github.com/guyezhimeng/ai-court.git"
    local INSTALL_DIR="/opt/ai-court"
    local APP_PORT=80
    
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户或 sudo 运行此脚本"
        exit 1
    fi
    
    log_info "检查系统环境..."
    
    if ! check_command docker; then
        install_docker
    else
        log_info "Docker 已安装: $(docker --version)"
    fi
    
    if ! check_command git; then
        install_git
    else
        log_info "Git 已安装: $(git --version)"
    fi
    
    if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null; then
        log_warn "Docker Compose 未安装，正在安装..."
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        log_info "Docker Compose 安装完成"
    fi
    
    read -p "安装目录 [默认: /opt/ai-court]: " INPUT_DIR
    INSTALL_DIR=${INPUT_DIR:-$INSTALL_DIR}
    
    read -p "Git 仓库地址 [默认: $REPO_URL]: " INPUT_REPO
    REPO_URL=${INPUT_REPO:-$REPO_URL}
    
    clone_or_update "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    configure_env ".env"
    
    read -p "应用端口 [默认: 80]: " INPUT_PORT
    APP_PORT=${INPUT_PORT:-$APP_PORT}
    
    sed -i "s/\"80:80\"/\"$APP_PORT:80\"/" docker-compose.yml 2>/dev/null || \
    sed -i '' "s/\"80:80\"/\"$APP_PORT:80\"/" docker-compose.yml
    
    start_services
    
    show_success "$APP_PORT"
}

main "$@"
