# 🏛️ AI 朝廷 · 三省六部

> 内置聊天框 + 看板 + 多Agent协作 + Token优化 · 一键部署

用 1300 年前的帝国制度，重新设计了 AI 多 Agent 协作架构。**无需 Discord/飞书**，开箱即用的内置 Web 聊天框。

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 💬 **内置聊天框** | 无需 Discord/飞书，直接在 Web 端与 Agent 对话 |
| 📋 **旨意看板** | 实时任务流转看板，MiniPipe 可视化 |
| 📎 **文件上传** | 支持图片/文档/代码拖拽上传，自动 OCR 提取 |
| 🤖 **11 个 Agent** | 太子分拣 → 中书省起草 → 门下省审议 → 尚书省派发 → 六部执行 |
| ⚡ **Token 优化** | SOUL 分层加载 + 上下文压缩 + 记忆相关性检索，节省 **70% Token** |
| 🔧 **独立模型配置** | 每个 Agent 可单独设置 LLM 模型/API Key |
| 📜 **聊天历史持久化** | PostgreSQL 存储，支持搜索、分页、导出 |
| 🔄 **WebSocket 实时推送** | 替代轮询，消息和事件实时到达 |
| 🐳 **一键部署** | Docker Compose，8 个容器一键启动 |

## 🏛️ 架构

```
用户(皇上) → 御书房聊天框 → ChatService
                          ├─ 闲聊 → 直接 LLM 回复
                          └─ 下旨 → TaskService
                                    ↓ (Redis Streams)
                              OrchestratorWorker
                                    ↓
                              DispatchWorker (快慢分桶)
                                    ↓
                            openclaw agent --agent xxx
```

## 🚀 快速部署（阿里云）

### 方式一：一键脚本（推荐）

```bash
# SSH 登录阿里云 ECS 后运行：
curl -fsSL https://raw.githubusercontent.com/你的用户名/ai-court/main/install.sh | bash
```

脚本会自动：
1. 安装 Docker + Docker Compose
2. 克隆项目代码
3. 引导配置 LLM API Key / 模型
4. 启动全部服务（PostgreSQL + Redis + Backend + Workers + Frontend）

### 方式二：手动部署

```bash
# 1. 克隆项目
git clone https://github.com/你的用户名/ai-court.git
cd ai-court

# 2. 配置环境变量
cp backend/.env.example .env
# 编辑 .env 填入你的 LLM API Key

# 3. 启动
docker compose up -d --build

# 4. 访问 http://你的服务器IP:80
```

## ⚙️ 配置说明

### 全局 LLM 配置（`.env` 文件）

```env
LLM_API_URL=https://api.openai.com/v1    # OpenAI 兼容接口
LLM_API_KEY=sk-xxx                        # API Key
LLM_MODEL=gpt-4o-mini                     # 默认模型
```

### 每 Agent 独立配置（`agents/{agent_id}/config.json`）

每个 Agent 可以使用不同的模型和 API：

```json
{
  "model": "gpt-4o",           // 该 Agent 使用的模型
  "api_url": "",               // 留空则使用全局配置
  "api_key": "",               // 留空则使用全局配置
  "max_tokens": 2000,
  "temperature": 0.5
}
```

**推荐配置方案：**

| Agent | 推荐模型 | 说明 |
|-------|---------|------|
| 太子 | gpt-4o-mini | 轻量分类任务 |
| 中书省 | gpt-4o | 需要复杂推理 |
| 门下省 | gpt-4o | 需要严格审核 |
| 尚书省 | gpt-4o-mini | 协调调度 |
| 六部 | gpt-4o-mini | 执行层，便宜够用 |
| 早朝官 | deepseek-chat | 新闻采集，性价比高 |

通过 API 动态修改：
```bash
# 修改中书省的模型为 GPT-4o
POST /api/agents/zhongshu/config
{"model": "gpt-4o", "max_tokens": 2000}
```

## 📁 项目结构

```
ai-court/
├── agents/                  # 11个 Agent 人设+独立配置
│   ├── GLOBAL.md            # 全局规则
│   ├── groups/              # 组级规则
│   │   ├── sansheng.md     # 三省规则
│   │   └── liubu.md        # 六部规则
│   ├── taizi/SOUL.md       # 太子人设（核心段+详细段）
│   ├── taizi/config.json   # 太子独立模型配置
│   └── ...                  # 其他 Agent 同理
├── backend/                 # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── config.py       # 配置管理
│   │   ├── models/         # 数据库模型 (Task/Chat/Attachment)
│   │   ├── services/       # 核心服务
│   │   │   ├── event_bus.py        # Redis Streams 事件总线
│   │   │   ├── chat_service.py     # 聊天服务(闲聊/下旨路由)
│   │   │   ├── llm_service.py      # LLM调用(支持每Agent独立模型)
│   │   │   ├── upload_service.py   # 文件上传
│   │   │   ├── context_optimizer.py # Token优化器
│   │   │   └── task_service.py     # 任务状态机
│   │   ├── api/             # REST API + WebSocket
│   │   ├── channels/        # 多通道(Web/Discord/飞书)
│   │   └── workers/         # 编排器/派发器/投递器
├── frontend/                # React + Tailwind 前端
│   ├── src/components/
│   │   ├── layout/Sidebar.tsx      # 侧边导航
│   │   ├── chat/ChatPanel.tsx      # 御书房聊天框(拖拽上传)
│   │   └── board/EdictBoard.tsx    # 旨意看板(MiniPipe)
├── docker-compose.yml       # 8容器编排
├── install.sh               # 一键安装脚本
└── update.sh                # 一键更新脚本
```

## 🔑 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat/sessions` | POST | 创建会话 |
| `/api/chat/send` | POST | 发送消息（自动识别闲聊/下旨） |
| `/api/chat/history/{id}` | GET | 获取历史消息 |
| `/api/upload` | POST | 上传文件（multipart） |
| `/ws` | WebSocket | 实时事件推送 |
| `/api/tasks` | GET/POST | 任务列表/创建 |
| `/api/tasks/{id}/transition` | POST | 状态流转 |
| `/api/agents` | GET | 列出所有Agent及模型配置 |
| `/api/agents/{id}/config` | GET/POST | 查看/修改Agent模型配置 |

## 🆚 与原版对比

| 维度 | danghuangshang | edict | **本项目** |
|------|---------------|-------|-----------|
| 聊天方式 | 仅 Discord/飞书 | 仅朝堂议政(无持久化) | **内置聊天框+持久化** |
| 文件上传 | 靠 Discord | ❌ | **拖拽/粘贴上传** |
| Token 优化 | 写了但没用 | ❌ | **5层优化,节省70%** |
| 模型配置 | 全局统一 | 全局统一 | **每Agent独立配置** |
| UI | 手写CSS+Emoji | 手写CSS | **React+Tailwind+Lucide** |
| 实时性 | 5秒轮询 | 5秒轮询 | **WebSocket** |
| 部署难度 | 中 | 高(Docker) | **一键脚本** |

## 📄 License

MIT
