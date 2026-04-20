#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║     🏛️  AI 朝廷 · 离线部署脚本                            ║"
    echo "║                                                           ║"
    echo "║     无需联网，100% 离线部署                                ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="/opt/ai-court"

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        log_info "正在尝试安装 Docker..."

        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
        else
            log_error "无法检测操作系统，请手动安装 Docker"
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
                apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
                ;;
            centos|rhel|alinux)
                yum install -y yum-utils
                yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
                yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
                ;;
            *)
                log_error "不支持的操作系统: $OS，请手动安装 Docker"
                exit 1
                ;;
        esac

        systemctl start docker
        systemctl enable docker
        log_info "Docker 安装完成"
    else
        log_info "Docker 已安装: $(docker --version)"
    fi

    if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null; then
        log_warn "Docker Compose 未安装"
        if command -v apt-get &> /dev/null; then
            apt-get install -y docker-compose-plugin
        elif command -v yum &> /dev/null; then
            yum install -y docker-compose-plugin
        fi
    fi
}

load_images() {
    local IMG_DIR="$1"
    local TAR_COUNT=$(find "$IMG_DIR" -maxdepth 1 -name "*.tar" | wc -l)

    if [ "$TAR_COUNT" -eq 0 ]; then
        log_warn "未找到 .tar 镜像文件，跳过加载（可能已加载）"
        return
    fi

    log_step "加载离线镜像 ($TAR_COUNT 个文件)..."
    for tar_file in "$IMG_DIR"/*.tar; do
        local filename=$(basename "$tar_file")
        log_info "加载: $filename"
        docker load -i "$tar_file" || log_warn "$filename 加载失败，可能已存在"
    done
    log_info "镜像加载完成"
}

select_llm_provider() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  请选择默认 LLM 模型提供商${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} DeepSeek (推荐)"
    echo -e "  ${GREEN}2)${NC} OpenAI"
    echo -e "  ${GREEN}3)${NC} 月之暗面 (Kimi)"
    echo -e "  ${GREEN}4)${NC} 通义千问"
    echo -e "  ${GREEN}5)${NC} 智谱 (GLM)"
    echo -e "  ${GREEN}6)${NC} 硅基流动"
    echo -e "  ${GREEN}7)${NC} 自定义"
    echo ""
    echo -ne "  请选择 [1-7, 默认1]: "

    read -r PROVIDER_CHOICE
    PROVIDER_CHOICE=${PROVIDER_CHOICE:-1}

    case $PROVIDER_CHOICE in
        1) API_URL="https://api.deepseek.com/v1"; DEFAULT_MODEL="deepseek-chat"; log_info "已选择: DeepSeek" ;;
        2) API_URL="https://api.openai.com/v1"; DEFAULT_MODEL="gpt-4o-mini"; log_info "已选择: OpenAI" ;;
        3) API_URL="https://api.moonshot.cn/v1"; DEFAULT_MODEL="moonshot-v1-8k"; log_info "已选择: 月之暗面" ;;
        4) API_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"; DEFAULT_MODEL="qwen-plus"; log_info "已选择: 通义千问" ;;
        5) API_URL="https://open.bigmodel.cn/api/paas/v4"; DEFAULT_MODEL="glm-4-flash"; log_info "已选择: 智谱" ;;
        6) API_URL="https://api.siliconflow.cn/v1"; DEFAULT_MODEL="Qwen/Qwen2.5-7B-Instruct"; log_info "已选择: 硅基流动" ;;
        7)
            read -p "  API URL: " API_URL
            read -p "  模型名称: " DEFAULT_MODEL
            API_URL=${API_URL:-https://api.deepseek.com/v1}
            DEFAULT_MODEL=${DEFAULT_MODEL:-deepseek-chat}
            ;;
        *) API_URL="https://api.deepseek.com/v1"; DEFAULT_MODEL="deepseek-chat"; log_info "默认: DeepSeek" ;;
    esac
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

    log_step "配置环境变量..."

    read -p "请输入 LLM API Key: " API_KEY
    while [ -z "$API_KEY" ]; do
        log_error "API Key 不能为空"
        read -p "请输入 LLM API Key: " API_KEY
    done

    read -p "模型名称 [默认: $DEFAULT_MODEL]: " MODEL
    MODEL=${MODEL:-$DEFAULT_MODEL}

    read -p "应用端口 [默认: 80]: " APP_PORT
    APP_PORT=${APP_PORT:-80}

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

OSS_ENABLED=false
EOF

    chmod 600 "$ENV_FILE"
    log_info "配置文件已保存"
}

start_services() {
    log_step "启动服务..."

    cd "$INSTALL_DIR"

    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose up -d
    elif command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        log_error "Docker Compose 未安装"
        exit 1
    fi

    log_info "等待服务启动..."
    sleep 10

    docker compose ps 2>/dev/null || docker-compose ps 2>/dev/null
}

main() {
    print_banner

    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户或 sudo 运行此脚本"
        exit 1
    fi

    check_docker

    read -p "安装目录 [默认: /opt/ai-court]: " INPUT_DIR
    INSTALL_DIR=${INPUT_DIR:-$INSTALL_DIR}

    mkdir -p "$INSTALL_DIR"

    log_step "复制部署文件..."
    if [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then
        cp "$SCRIPT_DIR/docker-compose.yml" "$INSTALL_DIR/"
    fi
    if [ -f "$SCRIPT_DIR/nginx.conf" ]; then
        cp "$SCRIPT_DIR/nginx.conf" "$INSTALL_DIR/"
    fi
    if [ -d "$SCRIPT_DIR/agents" ]; then
        cp -r "$SCRIPT_DIR/agents" "$INSTALL_DIR/"
    fi

    load_images "$SCRIPT_DIR"

    select_llm_provider

    configure_env "$INSTALL_DIR/.env"

    start_services

    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo '服务器IP')
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✅ AI 朝廷离线部署成功！                     ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  🌐 访问地址: ${CYAN}http://${SERVER_IP}:${APP_PORT:-80}${NC}"
    echo ""
    echo "  📋 常用命令:"
    echo "     查看日志:   docker compose logs -f"
    echo "     重启服务:   docker compose restart"
    echo "     停止服务:   docker compose down"
    echo ""
}

main "$@"
