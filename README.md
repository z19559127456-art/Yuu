# Yu — AI Agent Messenger OS

> Windows 桌面应用，微信式 UI，以 AI Agent 为核心的操作系统级平台。  
> 让 AI Agent 像微信好友一样：创建、聊天、群聊协作、执行任务。

---

## 功能总览

| 模块 | 状态 | 说明 |
|------|------|------|
| 微信三栏 UI | 完成 | 导航栏 + Agent 列表 + 聊天区，支持暗色/浅色主题 |
| Agent 管理 | 完成 | 创建/编辑/删除 Agent，每个 Agent 独立 LLM 配置、工具集、人格 |
| 单 Agent 对话 | 完成 | WebSocket 实时通信、LLM 流式输出、Markdown + 代码高亮渲染 |
| LLM 多提供商 | 完成 | OpenAI / Anthropic / 自定义兼容（DeepSeek、Ollama 等） |
| CLI 工具 | 完成 | 命令白名单/黑名单 + 目录安全控制 + 超时/取消令牌 + 流式回显 |
| Web 自动化 | 完成 | Playwright 驱动，8 种操作（导航/点击/输入/截图/提取/滚动/等待/执行JS） |
| PWC 三角架构 | 完成 | Planner（拆解）+ Worker（执行）+ Critic（评审），含完整状态机 |
| 群聊协作 | 完成 | 任务模式（Coordinator 调度）+ 讨论模式（自由发言），支持 @mention |
| 防死循环 | 完成 | 三层检测：环路检测 + Token/轮次预算 + 超时无响应 |
| 记忆管理 | 完成 | L1 进程缓存 + L2 LLM 摘要压缩 + L3 ChromaDB 向量记忆 |
| 并发控制 | 完成 | 优先级任务队列 + 信号量限制 + 指数退避重试 |
| Skill 插件 | 完成 | 热重载注册中心 + code_review / summarize 内置技能 |
| 安全系统 | 部分 | PermissionChecker / AuditLogger 类已实现，ws_handler 集成待完善 |
| 应用内更新 | 完成 | electron-updater 自动检查 + 下载进度 + 一键重启安装 |
| CI/CD | 完成 | GitHub Actions：打 tag 自动构建 → 发布 GitHub Release |

---

## 项目架构

```
frontend (Electron + React + TypeScript)
    ↕ 单一 WebSocket (ws://localhost:7890/ws)
backend (Python Flask + Flask-Sock)
    ↕
┌─────────────────────────────────────────────────┐
│  LLM Client  │  Tools  │  Skills  │  Memory     │
│  OpenAI      │  CLI    │  Code    │  L1 Cache   │
│  Anthropic   │  Web    │  Review  │  L2 Summary │
│  自定义      │  UI     │  Summar- │  L3 ChromaDB│
│              │  Vision │  ize     │             │
├─────────────────────────────────────────────────┤
│  Orchestrator (PWC 状态机)                      │
│  CollaborationEngine + GroupChatBus              │
│  Security (Permission / Audit)                   │
│  Concurrency (Queue / Retry)                     │
└─────────────────────────────────────────────────┘
    ↕
SQLite + ChromaDB
```

---

## 目录结构

```
├── frontend/                 # Electron + React + TypeScript
│   ├── electron/             # Electron 主进程 (main.js / preload.js)
│   ├── src/
│   │   ├── components/       # React 组件 (17个)
│   │   ├── hooks/            # useWebSocket
│   │   ├── store/            # Zustand 全局状态
│   │   └── types/            # TypeScript 类型定义
│   └── package.json
├── backend/                  # Python Flask
│   ├── app/                  # 核心模块 (26个 .py 文件)
│   │   ├── main.py           # Flask 入口 (端口 7890)
│   │   ├── ws_handler.py     # WebSocket 集中路由
│   │   ├── llm_client.py     # 统一 LLM 客户端
│   │   ├── orchestrator.py   # PWC 任务编排状态机
│   │   ├── collaboration_engine.py  # 多 Agent 协作引擎
│   │   ├── group_chat_bus.py # 群聊消息总线
│   │   ├── models.py         # SQLAlchemy ORM 模型
│   │   └── ...               # 工具/技能/记忆/安全/并发
│   ├── tests/                # 单元测试 + 集成测试 (22个文件)
│   └── requirements.txt
├── .github/workflows/        # GitHub Actions CI/CD
├── AI_Agent_Messenger_OS_SPEC_完整版_v0.5.md  # 完整技术规格
└── README.md
```

---

## 快速开始

### 环境要求

- **Windows** 10/11
- **Python** 3.10+
- **Node.js** 18+

### 1. 后端启动

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
# 启动在 http://localhost:7890
```

### 2. 前端启动

```bash
cd frontend
npm install
npm run dev          # Vite 开发服务器 → http://localhost:3000
npm run electron:dev # 启动 Electron 窗口（开发模式）
```

### 3. 配置 API Key

在 Agent 创建面板中直接填写 API Key，或设置环境变量：

```env
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

每个 Agent 可以使用不同的 LLM 提供商和模型。

---

## Agent 能力矩阵

每个 Agent 是一个可独立配置的 AI 实体：

| 配置项 | 说明 |
|--------|------|
| 系统提示词 | 自定义角色、行为边界 |
| LLM 模型 | OpenAI / Anthropic / DeepSeek / Ollama 等 |
| 人格 | 严谨 / 活泼 / 简洁 + 语气 + 详细程度 |
| CLI 工具 | 命令白名单/黑名单 + 目录权限控制 |
| Web 工具 | 域名白名单/黑名单 + Playwright 浏览器自动化 |
| UI 自动化 | PyAutoGUI 桌面操作（受保护窗口需确认） |
| Vision 工具 | 截图分析 + OCR 文字识别 |
| 技能 | code_review / summarize，支持热重载自定义技能 |
| 记忆 | L1(缓存) + L2(摘要) + L3(向量语义搜索) |

---

## 群聊协作

### 任务模式
Coordinator Agent 接收指令 → Planner 拆解为子任务 → 按依赖拓扑排序分发执行 → Critic 评审 → 汇总输出

### 讨论模式
多 Agent 自由发言 → 每轮自主判断发言/跳过(`<pass>`)/宣布共识(`<consensus>`) → 三层防死循环保护 → 自动收敛终止

---

## 开发命令

```bash
# 后端测试
cd backend && venv\Scripts\activate && pytest

# 前端测试
cd frontend && npm test

# TypeScript 类型检查
cd frontend && npx tsc --noEmit

# Electron 打包
cd frontend && npm run electron:build:nsis
```

---

## 发布流程

```bash
# 1. 更新版本号
# frontend/package.json → version
# frontend/electron/preload.js → getVersion()

# 2. 打 tag 推送
git tag v0.1.7
git push origin v0.1.7

# 3. GitHub Actions 自动：
#    构建后端 EXE → 构建前端 → Electron 打包 → 发布 GitHub Release
#    用户下次启动应用时 autoUpdater 自动检测到新版本
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 桌面框架 | Electron 28 |
| 前端 UI | React 18 + TypeScript + Tailwind CSS |
| 状态管理 | Zustand |
| 后端 | Python Flask + Flask-Sock (WebSocket) |
| LLM | OpenAI SDK / Anthropic SDK / 自定义兼容 |
| 数据库 | SQLite (SQLAlchemy ORM) + ChromaDB (向量) |
| Web 自动化 | Playwright |
| 桌面自动化 | PyAutoGUI |
| 打包 | electron-builder (NSIS 安装程序) |
| CI/CD | GitHub Actions |
| 自动更新 | electron-updater (GitHub Releases) |

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [完整技术规格](AI_Agent_Messenger_OS_SPEC_完整版_v0.5.md) | 系统设计、数据模型、API 协议、架构图 |
| [开发流程](DEVELOPMENT.md) | 分阶段开发计划、环境配置、规范 |
| [快速上手](QUICKSTART.md) | 5 分钟上手指南 |
| [提示词模板](PROMPTS.md) | Agent System Prompt 模板库 |
| [并行计划](PARALLEL_PLAN.md) | 多 Agent 并行开发计划 |
| [待办事项](TASKLIST.md) | 当前任务清单 |
| [遗留工作](REMAINING_WORK.md) | 已知问题和待修复项 |

---

## 版本

**v0.1.7**
