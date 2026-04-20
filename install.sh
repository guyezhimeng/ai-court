#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     🏛️  AI 朝廷 · 三省六部 · 一键部署脚本                  ║"
    echo "║                                                           ║"
    echo "║     内置聊天框 + 看板 + 多Agent协作 + Token优化            ║"
    echo "║     流式输出 + 截断续写 + 阿里云镜像加速                    ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

configure_docker_mirror() {
    log_step "配置 Docker 阿里云镜像加速..."

    mkdir -p /etc/docker

    if [ -f /etc/docker/daemon.json ]; then
        if grep -q "registry-mirrors" /etc/docker/daemon.json 2>/dev/null; then
            log_info "Docker 镜像加速已配置，跳过"
            return
        fi
    fi

    cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.m.daocloud.io",
    "https://dockerhub.azk8s.cn"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

    if systemctl is-active docker &> /dev/null; then
        systemctl daemon-reload
        systemctl restart docker
        log_info "Docker 镜像加速配置完成，已重启 Docker"
    else
        log_warn "Docker 未运行，镜像加速将在 Docker 启动后生效"
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

select_llm_provider() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  请选择默认 LLM 模型提供商${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} DeepSeek (推荐，性价比高)"
    echo -e "      模型: deepseek-chat / deepseek-reasoner"
    echo ""
    echo -e "  ${GREEN}2)${NC} OpenAI"
    echo -e "      模型: gpt-4o-mini / gpt-4o / gpt-4.1"
    echo ""
    echo -e "  ${GREEN}3)${NC} 月之暗面 (Kimi)"
    echo -e "      模型: moonshot-v1-8k / 32k / 128k"
    echo ""
    echo -e "  ${GREEN}4)${NC} 通义千问"
    echo -e "      模型: qwen-plus / qwen-turbo / qwen-max"
    echo ""
    echo -e "  ${GREEN}5)${NC} 智谱 (GLM)"
    echo -e "      模型: glm-4-flash / glm-4-plus / glm-4"
    echo ""
    echo -e "  ${GREEN}6)${NC} 硅基流动"
    echo -e "      模型: Qwen2.5-7B / DeepSeek-V3 等"
    echo ""
    echo -e "  ${GREEN}7)${NC} 自定义 (兼容 OpenAI API 格式)"
    echo ""
    echo -ne "  请选择 [1-7, 默认1]: "

    read -r PROVIDER_CHOICE
    PROVIDER_CHOICE=${PROVIDER_CHOICE:-1}

    case $PROVIDER_CHOICE in
        1)
            API_URL="https://api.deepseek.com/v1"
            DEFAULT_MODEL="deepseek-chat"
            log_info "已选择: DeepSeek"
            ;;
        2)
            API_URL="https://api.openai.com/v1"
            DEFAULT_MODEL="gpt-4o-mini"
            log_info "已选择: OpenAI"
            ;;
        3)
            API_URL="https://api.moonshot.cn/v1"
            DEFAULT_MODEL="moonshot-v1-8k"
            log_info "已选择: 月之暗面(Kimi)"
            ;;
        4)
            API_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
            DEFAULT_MODEL="qwen-plus"
            log_info "已选择: 通义千问"
            ;;
        5)
            API_URL="https://open.bigmodel.cn/api/paas/v4"
            DEFAULT_MODEL="glm-4-flash"
            log_info "已选择: 智谱(GLM)"
            ;;
        6)
            API_URL="https://api.siliconflow.cn/v1"
            DEFAULT_MODEL="Qwen/Qwen2.5-7B-Instruct"
            log_info "已选择: 硅基流动"
            ;;
        7)
            read -p "  请输入自定义 API URL: " API_URL
            read -p "  请输入默认模型名称: " DEFAULT_MODEL
            API_URL=${API_URL:-https://api.openai.com/v1}
            DEFAULT_MODEL=${DEFAULT_MODEL:-gpt-4o-mini}
            log_info "已选择: 自定义"
            ;;
        *)
            API_URL="https://api.deepseek.com/v1"
            DEFAULT_MODEL="deepseek-chat"
            log_info "默认选择: DeepSeek"
            ;;
    esac
}

configure_env() {
    local ENV_FILE="$1"
    local API_URL="$2"
    local DEFAULT_MODEL="$3"

    if [ -f "$ENV_FILE" ]; then
        log_info "检测到已有 .env 文件"
        read -p "是否重新配置？(y/N): " RECONFIG
        if [[ ! "$RECONFIG" =~ ^[Yy]$ ]]; then
            return
        fi
    fi

    log_step "配置环境变量..."

    read -p "请输入 LLM API Key: " API_KEY
    while [ -z "$API_KEY" ]; do
        log_error "API Key 不能为空"
        read -p "请输入 LLM API Key: " API_KEY
    done

    read -p "请输入模型名称 [默认: $DEFAULT_MODEL]: " MODEL
    MODEL=${MODEL:-$DEFAULT_MODEL}

    read -p "请输入应用端口 [默认: 80]: " APP_PORT
    APP_PORT=${APP_PORT:-80}

    read -p "是否配置阿里云 OSS？(y/N): " USE_OSS
    if [[ "$USE_OSS" =~ ^[Yy]$ ]]; then
        read -p "OSS Endpoint: " OSS_ENDPOINT
        read -p "OSS Bucket: " OSS_BUCKET
        read -p "OSS Access Key: " OSS_ACCESS_KEY
        read -p "OSS Secret Key: " OSS_SECRET_KEY
    fi

    cat > "$ENV_FILE" << EOF
POSTGRES_USER=aicourt
POSTGRES_PASSWORD=aicourt_secret_$(openssl rand -hex 8)
POSTGRES_DB=aicourt

APP_PORT=$APP_PORT

LLM_API_URL=$API_URL
LLM_API_KEY=$API_KEY
LLM_MODEL=$MODEL

APP_SECRET_KEY=$(openssl rand -hex 32)
APP_DEBUG=false

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
    log_info "  API URL: $API_URL"
    log_info "  模型: $MODEL"
}

start_services() {
    log_step "正在启动服务 (使用阿里云镜像加速)..."

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
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo '服务器IP')
    echo -e "  🌐 访问地址: ${BLUE}http://${SERVER_IP}:${PORT}${NC}"
    echo ""
    echo "  📋 常用命令:"
    echo "     查看日志:   docker compose logs -f"
    echo "     重启服务:   docker compose restart"
    echo "     停止服务:   docker compose down"
    echo "     更新部署:   git pull && docker compose up -d --build"
    echo ""
    echo "  🤖 Agent 配置:"
    echo "     每个Agent可独立设置API和模型"
    echo "     默认使用全局配置，可在后台'百官'页面单独修改"
    echo "     太子(max_tokens=500) / 中书省(4000) / 六部(4000)"
    echo ""
    echo "  🔄 流式输出:"
    echo "     已启用SSE流式输出，AI回复逐字显示"
    echo "     截断检测自动续写，确保输出完整"
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

    log_step "检查系统环境..."

    if ! check_command docker; then
        install_docker
    else
        log_info "Docker 已安装: $(docker --version)"
    fi

    configure_docker_mirror

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

    select_llm_provider

    configure_env ".env" "$API_URL" "$DEFAULT_MODEL"

    start_services

    show_success "$APP_PORT"
}

main "$@"
