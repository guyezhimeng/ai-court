#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

INSTALL_DIR="${1:-/opt/ai-court}"

if [ ! -d "$INSTALL_DIR" ]; then
    log_warn "安装目录不存在: $INSTALL_DIR"
    exit 1
fi

cd "$INSTALL_DIR"

log_info "停止服务..."
docker compose down 2>/dev/null || docker-compose down 2>/dev/null

log_info "拉取最新代码..."
git pull

log_info "重新构建并启动..."
docker compose up -d --build 2>/dev/null || docker-compose up -d --build

log_info "更新完成！"
docker compose ps 2>/dev/null || docker-compose ps
