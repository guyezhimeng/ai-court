# 🏛️ AI 朝廷 · 三省六部

> **v3.0.0** — 内置聊天框 + 看板 + 多Agent协作 + Token优化 + 分级审核 · 一键部署

用 1300 年前的帝国制度，重新设计了 AI 多 Agent 协作架构。**无需 Discord/飞书**，开箱即用的内置 Web 聊天框。

## ✨ 核心特性（v3.0 更新）

| 特性 | 说明 |
|------|------|
| 💬 **内置聊天框** | 无需 Discord/飞书，直接在 Web 端与 Agent 对话，支持 Markdown 渲染、会话列表 |
| 📋 **旨意看板** | 实时任务流转看板，7 步进度条可视化（太子→中书→门下→尚书→六部→审核→完成） |
| 📎 **文件上传** | 支持图片/文档/代码拖拽上传，LLM 多模态 OCR 提取，PDF/DOCX 文本提取 |
| 🤖 **11 个 Agent** | 太子分拣 → 中书省起草 → 门下省分级审议 → 尚书省派发 → 六部并行执行 |
| ⚡ **Token 优化** | SOUL 分层加载 + 上下文压缩 + 记忆相关性检索，节省 **70% Token** |
| 🔧 **独立模型配置** | 每个 Agent 可单独设置 LLM 模型/API Key，环境变量优先级覆盖 |
| 🔍 **门下省分级审核** | rule_fast / llm_standard / llm_deep 三级策略，敏感操作强制深度审核 |
| 📜 **聊天历史持久化** | PostgreSQL 存储，全文搜索(GIN索引)，支持搜索、分页、导出 |
| 🔄 **WebSocket 实时推送** | 心跳保活(60s) + JWT 认证 + 指数退避重连，消息和事件实时到达 |
| 🔒 **安全加固** | trace_id 全链路追踪、error_id 错误定位、UUID 安全文件名、CORS 收紧 |
| 🐳 **一键部署** | Docker Compose，9 个容器（含 pg-backup 定时备份）一键启动 |

## 🏛️ 架构（v3.0）

```
用户(皇上) → 御书房聊天框(ChatPanel)
                    ├─ 闲聊 → LLM 流式回复(SSE)
                    └─ 下旨 → TaskService
                              ↓ (OutboxEvent + Redis Streams)
                        OrchestratorWorker
                              ↓
                    门下省 ReviewStrategy (三级审核)
                              ↓
                   DispatchWorker (Function Calling)
                              ↓
                     直接调用 LLM API (无 OpenClaw 依赖)
                              ↓
                      六部并行执行(asyncio.gather)

辅助服务:
    OutboxRelay (指数退避投递) ← PostgreSQL Outbox
    StallDetector (停滞检测+自动升级)
    PgBackup (每日定时备份)
```

## 🚀 快速部署（阿里云）

### 方式一：一键脚本（推荐）

```bash
# SSH 登录阿里云 ECS 后运行：
curl -fsSL https://raw.githubusercontent.com/你的用户名/ai-court/main/install.sh | bash
```

脚本会自动：
1. 安装 Docker + Docker Compose（阿里云镜像加速）
2. 克隆项目代码
3. 引导选择 LLM 提供商（DeepSeek/OpenAI/Kimi/通义千问/智谱/硅基流动/自定义）
4. 自动生成强密码（PostgreSQL/Redis/SecretKey）
5. 启动全部 9 个服务容器
6. 配置 CORS 域名为服务器公网 IP

### 方式二：手动部署

```bash
# 1. 克隆项目
git clone https://github.com/你的用户名/ai-court.git
cd ai-court

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 LLM API Key（参考下方配置说明）

# 3. 启动
docker compose up -d --build

# 4. 访问 http://你的服务器IP:80
```

### 方式三：离线部署

```bash
# 在有网络的机器上打包镜像
bash save-images.sh

# 将整个项目目录 + offline-images/ 上传到服务器
# 运行离线部署脚本
bash install-offline.sh
```

## ⚙️ 配置说明

### 环境变量（`.env` 文件）

```env
# === 数据库 ===
POSTGRES_USER=aicourt
POSTGRES_PASSWORD=【改成强密码】
POSTGRES_DB=aicourt

# === Redis ===
REDIS_PASSWORD=【改成强密码】

# === 应用端口 ===
APP_PORT=80

# === LLM 配置（必填）===
LLM_API_URL=https://api.deepseek.com/v1
LLM_API_KEY=【你的 LLM API Key】
LLM_MODEL=deepseek-chat

# === 安全配置 ===
APP_SECRET_KEY=【用 python -c "import secrets;print(secrets.token_urlsafe(48))" 生成】
APP_DEBUG=false
ALLOWED_ORIGINS=http://你的公网IP或域名

# === 文件上传 ===
UPLOAD_DIR=/app/uploads
UPLOAD_MAX_SIZE_MB=20

# === 任务调度 ===
STALL_THRESHOLD_SEC=300      # 任务停滞检测阈值（秒）
MAX_DISPATCH_RETRY=3         # 最大派发重试次数
DISPATCH_TIMEOUT_SEC=120     # 单次派发超时（秒）

# === 数据库连接池 ===
DB_POOL_SIZE=5               # 连接池大小
DB_MAX_OVERFLOW=10           # 最大溢出连接数
DB_POOL_RECYCLE=3600         # 连接回收时间（秒）

# === 阿里云 OSS（可选）===
OSS_ENABLED=false
OSS_ENDPOINT=
OSS_BUCKET=
OSS_ACCESS_KEY=
OSS_SECRET_KEY=
```

### 每 Agent 独立模型配置（`agents/{agent_id}/config.json`）

每个 Agent 可以使用不同的模型和 API：

```json
{
  "model": "deepseek-chat",
  "api_url": "",
  "api_key": "",
  "max_tokens": 2000,
  "temperature": 0.5
}
```

**API Key 优先级：** `AGENT_XXX_API_KEY`（环境变量） > config.json 的 api_key > `.env` 的 `LLM_API_KEY`

**推荐配置方案：**

| Agent | 推荐模型 | max_tokens | 说明 |
|-------|---------|------------|------|
| 太子(taizi) | deepseek-chat | 500 | 轻量分类任务 |
| 中书省(zhongshu) | deepseek-chat | 4000 | 需要复杂推理起草 |
| 门下省(menxia) | deepseek-chat | 500 | 分级审核（rule_fast 时不需要 LLM） |
| 尚书省(shangshu) | deepseek-chat | 1000 | 协调调度 |
| 六部(liubu-*) | deepseek-chat | 4000 | 执行层，需要详细输出 |

## 📁 项目结构

```
ai-court/
├── agents/                       # 11个 Agent 人设+独立配置
│   ├── GLOBAL.md                 # 全局规则
│   ├── groups/                   # 组级规则
│   │   ├── sansheng.md          # 三省规则
│   │   └── liubu.md             # 六部规则
│   ├── taizi/SOUL.md            # 太子人设
│   ├── taizi/config.json        # 太子独立模型配置
│   └── ...                       # 其他 Agent 同理
├── backend/                      # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py               # FastAPI 入口 (v3.0: trace_id/健康检查/CORS收紧)
│   │   ├── config.py             # 配置管理 (连接池/SECRET_KEY验证)
│   │   ├── db.py                 # 数据库连接池
│   │   ├── models/               # 数据模型
│   │   │   ├── task.py           # 任务状态机 (Done/Cancelled可回退Zhongshu)
│   │   │   ├── chat.py           # 聊天会话+消息 (GIN全文搜索索引)
│   │   │   ├── attachment.py     # 文件附件
│   │   │   └── outbox.py         # 事件投递箱
│   │   ├── services/             # 核心服务
│   │   │   ├── event_bus.py      # Redis Streams 事件总线
│   │   │   ├── chat_service.py   # 聊天服务 (强/弱关键词分类+全文搜索)
│   │   │   ├── llm_service.py    # LLM调用 (每Agent独立配置+流式输出)
│   │   │   ├── upload_service.py # 文件上传 (UUID安全文件名+OCR+PDF提取)
│   │   │   ├── task_service.py   # 任务状态机管理
│   │   │   ├── context_optimizer.py # Token优化器
│   │   │   └── review_strategy.py # 门下省三级审核策略 [新增]
│   │   ├── api/                  # REST API + WebSocket
│   │   │   ├── websocket.py      # WS端点 (心跳保活+JWT认证)
│   │   │   ├── chat.py, tasks.py, agents.py, upload.py
│   │   └── workers/              # 后台工作进程
│   │       ├── orchestrator_worker.py # 编排器 (分级审核+并行dispatch+graceful shutdown)
│   │       ├── dispatch_worker.py     # 派发器 (直接LLM API+Function Calling)
│   │       └── outbox_relay.py        # 投递器 (指数退避轮询)
├── frontend/                     # React + Tailwind 前端
│   ├── src/
│   │   ├── App.tsx               # React Router 路由入口
│   │   ├── store.ts              # Zustand状态管理 (WS指数退避+task_progress)
│   │   ├── api.ts                # API 封装 (VITE_API_URL 兼容生产环境)
│   │   └── components/
│   │       ├── layout/Sidebar.tsx     # 侧边导航 (navigate路由跳转)
│   │       ├── chat/ChatPanel.tsx     # 御书房 (Markdown渲染+TaskProgressBar+会话列表)
│   │       ├── board/EdictBoard.tsx   # 旨意看板
│   │       ├── monitor/MonitorPanel.tsx  # 省部调度
│   │       ├── officials/OfficialsPanel.tsx  # 官员总览
│   │       ├── memorials/MemorialsPanel.tsx  # 奏折阁
│   │       ├── news/NewsPanel.tsx      # 天下要闻
│   │       ├── settings/SettingsPanel.tsx  # 配置中心
│   │       └── regime/RegimePanel.tsx  # 制度切换
├── docker-compose.yml            # 9容器编排 (含pg-backup)
├── nginx.conf                    # Nginx 反向代理配置
├── install.sh                    # 一键安装脚本 (在线部署)
├── install-offline.sh            # 离线部署脚本
├── update.sh                     # 一键更新脚本
├── save-images.sh                # 镜像打包脚本
└── load-images.sh                # 镜像加载脚本
```

## 🔑 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat/sessions` | POST | 创建会话 |
| `/api/chat/send` | POST | 发送消息（自动识别闲聊/下旨，支持 SSE 流式） |
| `/api/chat/history/{id}` | GET | 获取历史消息 |
| `/api/chat/search` | POST | 全文搜索消息 |
| `/api/upload` | POST | 上传文件（multipart，UUID 安全文件名） |
| `/ws` | WebSocket | 实时事件推送（心跳保活 + JWT 可选认证） |
| `/api/tasks` | GET/POST | 任务列表/创建 |
| `/api/tasks/{id}/transition` | POST | 状态流转 |
| `/api/tasks/summary` | GET | 任务统计摘要 |
| `/api/agents` | GET | 列出所有Agent及模型配置 |
| `/api/agents/{id}/config` | GET/POST | 查看/修改Agent模型配置 |
| `/api/health` | GET | **[新增]** 健康检查（postgres/redis/agents 三项检测） |
| `/api/live-status` | GET | **[新增]** 实时任务状态统计 |

## 🆚 与原版对比

| 维度 | danghuangshang | edict | **本项目 v3.0** |
|------|---------------|-------|----------------|
| 聊天方式 | 仅 Discord/飞书 | 仅朝堂议政(无持久化) | **内置聊天框+持久化+Markdown渲染** |
| 文件上传 | 靠 Discord | ❌ | **拖拽/粘贴上传+OCR+PDF提取** |
| Token 优化 | 写了但没用 | ❌ | **5层优化,节省70%** |
| 模型配置 | 全局统一 | 全局统一 | **每Agent独立配置+环境变量优先级** |
| UI | 手写CSS+Emoji | 手写CSS | **React+Tailwind+Lucide+Router** |
| 实时性 | 5秒轮询 | 5秒轮询 | **WebSocket+心跳+指数退避** |
| 审核 | 无 | 无 | **门下省三级审核(rule_fast/llm/deep)** |
| 安全性 | 基础 | 基础 | **trace_id/JWT/CORS收紧/安全文件名** |
| 部署难度 | 中 | 高(Docker) | **一键脚本(在线/离线)** |
| 备份 | 无 | 无 | **pg-backup 每日自动备份** |
| OpenClaw依赖 | ✅ 有 | ✅ 有 | **❌ 已移除，直接LLM API** |

## 🐳 Docker 服务清单

| 容器 | 说明 | 网络 |
|------|------|------|
| postgres | PostgreSQL 16 数据库 | internal (仅内部访问) |
| redis | Redis 7 (密码保护, AOF持久化) | internal |
| backend | FastAPI 后端 (expose 8000) | internal |
| orchestrator | 编排器 Worker | internal |
| dispatcher | 派发器 Worker | internal |
| outbox-relay | 事件投递器 (指数退避) | internal |
| pg-backup | 每日定时备份 (保留7天) | internal |
| frontend | React 前端 (Nginx, port 80) | internal |
| nginx | 反向代理 (唯一对外暴露端口) | internal |

> 所有后端服务仅通过 `internal` 网络通信，仅 Nginx 对外暴露端口。

## 📄 License

MIT
