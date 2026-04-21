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

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log_step "AI 朝廷 - 离线镜像加载工具"
echo ""

if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，请先安装 Docker"
    exit 1
fi

TAR_COUNT=$(find "$SCRIPT_DIR" -maxdepth 1 -name "*.tar" | wc -l)

if [ "$TAR_COUNT" -eq 0 ]; then
    log_error "当前目录下未找到 .tar 镜像文件"
    log_info "请确保 offline-images 目录内容完整"
    exit 1
fi

log_info "找到 $TAR_COUNT 个镜像文件"
echo ""

TOTAL_SIZE=$(du -sh "$SCRIPT_DIR"/*.tar 2>/dev/null | tail -1 | cut -f1)
log_info "总大小约: $TOTAL_SIZE"
echo ""

log_step "开始加载镜像..."

SUCCESS=0
FAIL=0

for tar_file in "$SCRIPT_DIR"/*.tar; do
    filename=$(basename "$tar_file")
    log_info "加载: $filename"
    if docker load -i "$tar_file"; then
        SUCCESS=$((SUCCESS + 1))
        log_info "✓ $filename 加载成功"
    else
        FAIL=$((FAIL + 1))
        log_error "✗ $filename 加载失败"
    fi
done

echo ""
log_step "加载完成: 成功 $SUCCESS / 失败 $FAIL"

if [ -f "$SCRIPT_DIR/manifest.txt" ]; then
    log_step "验证镜像..."
    while IFS='|' read -r filename img_name; do
        filename=$(echo "$filename" | xargs)
        img_name=$(echo "$img_name" | xargs)
        [ -z "$filename" ] && continue
        [[ "$filename" == \#* ]] && continue

        if docker image inspect "$img_name" &> /dev/null; then
            log_info "✓ $img_name"
        else
            log_warn "✗ $img_name 未找到"
        fi
    done < "$SCRIPT_DIR/manifest.txt"
fi

echo ""
if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ 所有镜像加载成功！可以执行 install-offline.sh 开始部署${NC}"
else
    echo -e "${YELLOW}⚠️  部分镜像加载失败，请检查错误信息${NC}"
fi
