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
OUTPUT_DIR="${1:-$SCRIPT_DIR/offline-images}"

mkdir -p "$OUTPUT_DIR"

log_step "AI 朝廷 - 离线镜像打包工具"
echo ""
echo "  输出目录: $OUTPUT_DIR"
echo ""

if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，无法打包镜像"
    exit 1
fi

BASE_IMAGES=(
    "registry.cn-hangzhou.aliyuncs.com/library/postgres:16-alpine"
    "registry.cn-hangzhou.aliyuncs.com/library/redis:7-alpine"
    "registry.cn-hangzhou.aliyuncs.com/library/nginx:alpine"
    "registry.cn-hangzhou.aliyuncs.com/library/python:3.12-slim"
    "registry.cn-hangzhou.aliyuncs.com/library/node:20-alpine"
)

log_step "第1步: 拉取基础镜像..."
for img in "${BASE_IMAGES[@]}"; do
    if docker image inspect "$img" &> /dev/null; then
        log_info "已存在: $img"
    else
        log_info "拉取: $img"
        docker pull "$img" || {
            log_warn "阿里云镜像拉取失败，尝试 Docker Hub..."
            hub_img=$(echo "$img" | sed 's|registry.cn-hangzhou.aliyuncs.com/library/||')
            docker pull "$hub_img" && docker tag "$hub_img" "$img"
        }
    fi
done

log_step "第2步: 构建应用镜像..."
cd "$SCRIPT_DIR"

if [ ! -f docker-compose.yml ]; then
    log_error "未找到 docker-compose.yml"
    exit 1
fi

docker compose build backend frontend 2>/dev/null || docker-compose build backend frontend

log_step "第3步: 打包基础镜像为 tar 文件..."
for img in "${BASE_IMAGES[@]}"; do
    filename=$(echo "$img" | sed 's|/|_|g' | sed 's|:|_g|' | sed 's|\.|_|g')
    tar_path="$OUTPUT_DIR/${filename}.tar"
    if [ -f "$tar_path" ]; then
        log_info "已存在: $tar_path (跳过)"
    else
        log_info "打包: $img -> $tar_path"
        docker save -o "$tar_path" "$img"
    fi
done

log_step "第4步: 打包应用镜像为 tar 文件..."
APP_IMAGES=$(docker compose images -q backend frontend 2>/dev/null || docker-compose images -q backend frontend)

for img_id in $APP_IMAGES; do
    img_name=$(docker inspect --format='{{index .RepoTags 0}}' "$img_id" 2>/dev/null || echo "aicourt_$img_id")
    safe_name=$(echo "$img_name" | sed 's|/|_|g' | sed 's|:|_|g' | sed 's|\.|_|g')
    tar_path="$OUTPUT_DIR/${safe_name}.tar"
    log_info "打包: $img_name -> $tar_path"
    docker save -o "$tar_path" "$img_id"
done

log_step "第5步: 生成镜像清单..."
cat > "$OUTPUT_DIR/manifest.txt" << 'MANIFEST_EOF'
# AI 朝廷 - 离线镜像清单
# 使用 load-images.sh 加载所有镜像
# 
# 格式: 文件名 | 镜像名称
MANIFEST_EOF

for img in "${BASE_IMAGES[@]}"; do
    filename=$(echo "$img" | sed 's|/|_|g' | sed 's|:|_g|' | sed 's|\.|_|g')
    echo "${filename}.tar | $img" >> "$OUTPUT_DIR/manifest.txt"
done

for img_id in $APP_IMAGES; do
    img_name=$(docker inspect --format='{{index .RepoTags 0}}' "$img_id" 2>/dev/null || echo "")
    safe_name=$(echo "$img_name" | sed 's|/|_|g' | sed 's|:|_|g' | sed 's|\.|_|g')
    echo "${safe_name}.tar | $img_name" >> "$OUTPUT_DIR/manifest.txt"
done

log_step "第6步: 复制部署文件..."
cp "$SCRIPT_DIR/docker-compose.yml" "$OUTPUT_DIR/"
cp "$SCRIPT_DIR/nginx.conf" "$OUTPUT_DIR/"
cp "$SCRIPT_DIR/load-images.sh" "$OUTPUT_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/install-offline.sh" "$OUTPUT_DIR/" 2>/dev/null || true

if [ -d "$SCRIPT_DIR/agents" ]; then
    cp -r "$SCRIPT_DIR/agents" "$OUTPUT_DIR/"
fi

TOTAL_SIZE=$(du -sh "$OUTPUT_DIR" | cut -f1)
FILE_COUNT=$(find "$OUTPUT_DIR" -name "*.tar" | wc -l)

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ 离线镜像打包完成！                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  📦 输出目录: $OUTPUT_DIR"
echo "  📊 镜像数量: $FILE_COUNT 个 tar 文件"
echo "  💾 总大小: $TOTAL_SIZE"
echo ""
echo "  📋 部署步骤:"
echo "     1. 将 $OUTPUT_DIR 整个目录上传到服务器:"
echo "        scp -r $OUTPUT_DIR root@服务器IP:/opt/ai-court-offline/"
echo ""
echo "     2. 在服务器上执行:"
echo "        cd /opt/ai-court-offline"
echo "        bash load-images.sh"
echo "        bash install-offline.sh"
echo ""
