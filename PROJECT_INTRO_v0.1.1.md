# vx版Agent集合体 v0.1.1 — 项目介绍

> **定位**：Windows 桌面应用，微信式 UI，以 AI Agent 为核心的操作系统级平台
>
> **当前版本**：v0.1.1  
> **仓库地址**：`c:/Users/Z1004/Desktop/cc/ds/vx版agent集合体`  
> **发布日期**：2026-05-07

---

## 一、项目概述

**vx版Agent集合体** 是一个桌面端 AI Agent 管理平台，采用微信风格的交互界面。每个 AI Agent 像一个"智能联系人"，你可以像聊天一样与它对话、给它配置不同的 LLM、授权它使用工具，甚至把多个 Agent 拉到群聊里协作。

### 核心理念

```
微信交互范式 × AI Agent 管理 × 多 Agent 协作
```

| 维度 | 说明 |
|------|------|
| 像微信一样简单 | 三栏布局（导航 / 联系人列表 / 聊天区），零学习成本 |
| Agent 像好友 | 每个 Agent 有独立身份、角色、记忆，可创建/编辑/删除 |
| 群聊即协作 | 多个 Agent 进入群聊，各自独立回复，@提及精准点名 |
| 自带 LLM 接入 | 内置 OpenAI / Anthropic 支持，自定义 Base URL 接入任意兼容 API |

---

## 二、技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | React 18 + TypeScript + Vite 5 | SPA 单页应用 |
| **状态管理** | Zustand 4 | 轻量级全局状态 |
| **通信** | WebSocket（Flask-Sock） | 全双工实时通信 |
| **UI 样式** | Tailwind CSS 3 | 微信风格设计 |
| **Markdown** | react-markdown + highlight.js | 消息富文本渲染 |
| **桌面端** | Electron 28 | Windows/Mac 桌面应用 |
| **后端** | Python 3.10+ + Flask 3 | REST + WebSocket |
| **数据库** | SQLite（SQLAlchemy ORM） | 本地持久化 |
| **向量存储** | ChromaDB | L3 长期记忆检索 |
| **LLM SDK** | openai + anthropic（Python） | 双协议流式调用 |
| **测试** | pytest（后端）+ vitest（前端） | 277+71 个测试用例 |

---

## 三、界面布局

```
┌─────────────────────────────────────────────────────┐
│  ┌──────┐ ┌──────────┐ ┌────────────────────────┐ │
│  │      │ │  消息     │ │   Agent 名称 / 群聊名   │ │
│  │  导  │ │  搜索     │ │                        │ │
│  │  航  │ │          │ │   ┌────────────────┐   │ │
│  │  栏  │ │  对话1 ✓  │ │   │  消息气泡列表   │   │ │
│  │      │ │  对话2    │ │   │                │   │ │
│  │ 消息  │ │  对话3    │ │   │  用户消息       │   │ │
│  │ 通讯录│ │          │ │   │  AI 回复(流式)   │   │ │
│  │ 设置  │ │  ───────  │ │   │  工具调用状态   │   │ │
│  │      │ │  群聊      │ │   └────────────────┘   │ │
│  │      │ │  群聊A ●  │ │                        │ │
│  │      │ │  群聊B    │ │   ┌─[输入框]──[@]─[↑]┐│ │
│  │      │ │          │ │   └────────────────────┘│ │
│  └──────┘ └──────────┘ └────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 四、核心功能详解

### 4.1 Agent 管理

每个 Agent 拥有完整配置项，像创建一个"AI 员工"一样灵活：

| 配置项 | 说明 |
|--------|------|
| **名称 / 角色** | Agent 的身份标识 |
| **系统提示词** | 自定义 System Prompt，定义行为边界 |
| **LLM 提供商** | OpenAI / Anthropic / 自定义（OpenAI 兼容） |
| **模型名称** | 自由输入：gpt-4o / deepseek-chat / qwen-plus 等 |
| **Base URL** | 自定义 API 端点，支持 DeepSeek / Ollama / Qwen 等 |
| **API Key** | 每 Agent 独立密钥，覆盖服务端默认配置 |
| **温度参数** | 0~2 滑块控制回复随机性 |
| **人格配置** | 风格（严谨/活泼/简洁/友好/专业）+ 语气（专业/轻松/正式/幽默/温暖） |
| **工具授权** | CLI 命令执行 / Web 网页抓取 / Vision 视觉识别 |

**Agent 列表可增删改查**，编辑和删除交互采用"hover 显示操作按钮 + 二次确认"模式。

---

### 4.2 第三方 LLM 接入

v0.1.1 的核心亮点：**不依赖特定模型厂商，任意 OpenAI 兼容 API 都能接入。**

| 接入场景 | Base URL 示例 | 模型示例 |
|----------|---------------|----------|
| **DeepSeek** | `https://api.deepseek.com` | `deepseek-chat` / `deepseek-reasoner` |
| **Ollama 本地** | `http://localhost:11434` | `llama3` / `qwen2.5` |
| **通义千问** | `https://dashscope.aliyuncs.com/compatible-mode` | `qwen-plus` / `qwen-max` |
| **OpenAI 代理** | 你的代理地址 | `gpt-4o` 等 |
| **智谱 GLM** | `https://open.bigmodel.cn/api/paas` | `glm-4` |

Base URL 自动补全 `/v1` 后缀，输 `api.deepseek.com` 自动变成 `api.deepseek.com/v1`。

---

### 4.3 对话系统

| 功能 | 说明 |
|------|------|
| **流式输出** | LLM 回复逐字显示，打字机效果 |
| **Markdown 渲染** | 代码高亮、表格、列表等富文本 |
| **上下文管理** | 自动维护对话历史，支持滑动窗口截断 |
| **AI 回复状态** | 发送中 / 思考中动画 / 完成 / 失败 |
| **删除对话** | hover 显示垃圾桶，二次确认删除 |
| **对话重命名** | 首条消息自动截取为对话标题 |

---

### 4.4 群聊系统

多个 Agent 可在同一群聊中各自独立回复：

```
用户 ──→ 群聊发送消息
              │
              ├──→ Agent A（用 LLM-A 生成回复）
              ├──→ Agent B（用 LLM-B 生成回复）
              └──→ Agent C（用 LLM-C 生成回复）
```

| 功能 | 说明 |
|------|------|
| **创建群聊** | 点 + 按钮 → 输入名称 → 勾选 2+ 个 Agent |
| **自动进入** | 创建后直接进入群聊界面 |
| **独立回复** | 每个 Agent 用自己的 LLM 配置生成回复 |
| **发送者标识** | 每条消息前缀标注 Agent 名称 |
| **刷新持久** | 刷新页面后群聊列表自动加载 |

---

### 4.5 @提及系统

群聊中通过 @ 点名指定 Agent 回复：

| 触发方式 | 说明 |
|----------|------|
| **输入 `@`** | 输入框中输入 @ 自动弹出 Agent 列表，按名字筛选 |
| **点击 @ 按钮** | 输入框左侧 @ 按钮（群聊模式专属），点开展示全部 Agent |

**回复规则**：
- 没有 @ 任何人 → **所有** Agent 都回复
- @ 了某个 Agent → **只有被 @ 的** Agent 回复
- @ 了多个 Agent → **所有被 @ 的** 都回复

---

### 4.6 工具层

Agent 可被授权使用工具，在对话中自动调用：

| 工具 | 功能 | 安全控制 |
|------|------|----------|
| **CLI 工具** | 执行命令行指令 | 白名单/黑名单命令过滤 |
| **Web 工具** | 网页导航、内容抓取 | 域名白名单/黑名单、页面数限制 |
| **Vision 工具** | 截图分析、图片理解 | 独立授权开关 |

工具执行有超时控制、执行状态提示、结果日志记录。

---

### 4.7 更多功能

| 功能模块 | 具体能力 |
|----------|----------|
| **记忆系统** | L1 对话缓存 + L2 历史摘要 + L3 向量检索（ChromaDB） |
| **PWC 编排** | Plan → Work → Critic 三阶段任务规划与执行 |
| **技能插件** | 代码审查（code_review）/ 内容总结（summarize）可扩展 |
| **消息操作** | 编辑已发消息 / 撤回消息 / 引用回复 |
| **安全审计** | 审计日志记录、权限检查、CLI 安全策略配置 |
| **导入导出** | Agent + 对话数据 JSON 导入导出 |
| **多语言** | 中英文 i18n 框架已就绪 |
| **连接状态** | WebSocket 连接/断开实时显示，自动重连（1s→10s 递增） |

---

## 五、项目结构

```
vx版agent集合体/
├── frontend/                          # 前端 (Electron + React + TypeScript)
│   ├── src/
│   │   ├── components/                # 17 个 UI 组件
│   │   │   ├── AgentCreatePanel.tsx   # Agent 创建/编辑面板
│   │   │   ├── AgentList.tsx          # 对话列表（含群聊分区）
│   │   │   ├── ChatArea.tsx           # 聊天主区域
│   │   │   ├── ChatHeader.tsx         # 聊天顶栏（私聊/群聊自适应）
│   │   │   ├── ChatInput.tsx          # 输入框 + @提及
│   │   │   ├── ContactsView.tsx       # 通讯录（Agent 列表管理）
│   │   │   ├── CreateConversationDialog.tsx  # 新建对话/群聊弹窗
│   │   │   ├── Layout.tsx             # 主布局
│   │   │   ├── MessageBubble.tsx      # 消息气泡
│   │   │   ├── MessageList.tsx        # 消息列表
│   │   │   ├── SettingsView.tsx       # 设置面板
│   │   │   ├── Sidebar.tsx            # 左侧导航栏
│   │   │   └── ...
│   │   ├── store/useStore.ts          # Zustand 全局状态
│   │   ├── hooks/useWebSocket.ts      # WebSocket 连接 + 消息分发
│   │   ├── types/index.ts             # TypeScript 类型定义
│   │   └── i18n/                      # 国际化（zh-CN / en-US）
│   └── electron/                      # Electron 主进程
│
├── backend/                           # 后端 (Python + Flask)
│   ├── app/
│   │   ├── main.py                    # Flask 应用入口（端口 7890）
│   │   ├── config.py                  # 配置管理
│   │   ├── database.py                # SQLAlchemy 初始化
│   │   ├── models.py                  # 19+ 个 ORM 数据模型
│   │   ├── ws_handler.py              # WebSocket 消息路由（全部业务逻辑）
│   │   ├── llm_client.py              # LLM 客户端（OpenAI/Anthropic 流式）
│   │   ├── context_manager.py         # 对话上下文构建
│   │   ├── planner.py / worker.py / critic.py  # PWC 编排
│   │   ├── orchestrator.py            # 任务编排器
│   │   ├── concurrency.py             # 并发控制 + 任务队列
│   │   ├── memory_manager.py          # L1/L2 记忆管理
│   │   ├── vector_memory.py           # L3 向量记忆（ChromaDB）
│   │   ├── skill_manager.py           # 技能热加载
│   │   ├── collaboration_engine.py    # 协作引擎
│   │   ├── group_chat_bus.py          # 群聊消息总线
│   │   ├── deadlock_detector.py       # 死循环检测
│   │   ├── security.py                # 安全审查 + 审计日志
│   │   ├── import_export.py           # 数据导入导出
│   │   ├── cli_tool.py                # CLI 安全执行
│   │   ├── web_tool.py                # Web 自动化
│   │   ├── ui_tool.py                 # UI 自动化
│   │   ├── vision_tool.py             # 视觉识别
│   │   └── skills/                    # 内置技能
│   ├── tests/                         # 20 个测试文件，277 个用例
│   ├── scripts/migrate.py             # 数据库迁移脚本
│   └── requirements.txt               # Python 依赖
│
├── docs/                              # 文档
├── scripts/                           # 辅助脚本
└── .gitignore
```

---

## 六、快速启动

### 环境要求

- **Python** 3.10+
- **Node.js** 18+
- **Windows** 10/11（开发模式可在任意系统运行）

### 1. 启动后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # 可选：配置全局 API Key
python -m app.main
# → 运行在 http://localhost:7890
```

### 2. 启动前端（新终端）

```bash
cd frontend
npm install
npm run dev
# → 运行在 http://localhost:3000（端口被占用会自动切换）
```

### 3. 配置 Agent

1. 打开浏览器访问前端地址
2. 点击左侧 **通讯录** 图标
3. 点击 **+** 创建 Agent
4. 填写名称、选择提供商、输入模型名
5. 如需接入第三方 API：选择"自定义 (OpenAI 兼容)"，填入 Base URL 和 API Key
6. 回到 **消息** 页签，点击 + 创建对话，选择 Agent
7. 发送消息开始对话

---

## 七、测试

### 后端测试（277 个用例）

```bash
cd backend
venv\Scripts\activate
python -m pytest tests/ -v
python -m pytest tests/ --cov=app --cov-report=html   # 覆盖率报告
```

### 前端测试（71 个用例）

```bash
cd frontend
npx vitest run
```

### 覆盖率概况

| 等级 | 后端模块（≥90%） |
|:---:|------|
| 90%+ | models (99%), config (100%), context_manager (97%), deadlock_detector (95%), concurrency (93%), security (91%) |
| 70-90% | cli_tool (87%), critic (82%), group_chat_bus (75%), import_export (74%), memory_manager (72%), skill_manager (72%), planner (65%) |

---

## 八、v0.1.1 版本功能清单

### 本版本新增（相对 v0.5.0）

| 功能 | 说明 |
|------|------|
| **自定义 LLM 接入** | Agent 创建面板支持 Base URL / API Key / 自定义模型名 |
| **第三方 Provider** | "自定义 (OpenAI 兼容)" 选项，支持 DeepSeek/Ollama/Qwen 等 |
| **Base URL 自动补全** | 自动追加 `/v1` 后缀 |
| **群聊系统** | 创建 → 进入 → 发消息 → 各 Agent 用各自 LLM 独立回复 |
| **@提及** | 输入 @ 或点 @ 按钮选择 Agent，精准点名回复 |
| **对话删除** | 对话列表 hover 显示垃圾桶，二次确认删除 |
| **群聊持久化** | 刷新页自动加载群聊列表 |
| **创建群聊自动进入** | 创建后直接进入群聊界面 |
| **发送者标识** | 群聊中每条消息标注 Agent 名称 |

### 继承功能（来自 v0.5.0）

- Agent CRUD（创建/编辑/删除/列表）
- LLM 流式对话（OpenAI + Anthropic）
- Markdown 渲染 + 代码高亮
- CLI / Web / Vision 工具
- PWC 任务编排（Plan-Work-Critic）
- 三级记忆系统（L1 缓存 + L2 摘要 + L3 向量）
- 技能插件（代码审查 / 内容总结）
- 消息编辑 / 撤回 / 引用
- 安全审计 + 权限控制
- 数据导入导出
- 多语言框架（zh-CN / en-US）
- WebSocket 自动重连
- Electron 桌面打包

---

## 九、后续规划

| 优先级 | 任务 |
|:---:|------|
| P0 | 修复 Electron 打包、后端集成测试、前后端联调、依赖锁定 |
| P1 | 数据迁移脚本、应用图标、NSIS 安装程序、LLM 集成测试 |
| P2 | 自动更新机制、E2E 测试、CI/CD 流水线、安全审计 |

---

## 十、技术架构图

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│  React 18 + TypeScript + Zustand + Tailwind     │
│              ↕ WebSocket (ws://)                 │
├─────────────────────────────────────────────────┤
│                   Backend                        │
│              Flask + Flask-Sock                  │
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Agent    │ │ PWC      │ │ Tool Layer     │  │
│  │ CRUD     │ │ Planner  │ │ CLI/Web/Vision │  │
│  │ ──────── │ │ Worker   │ │ UI Automation  │  │
│  │ Group    │ │ Critic   │ │                │  │
│  │ Chat     │ │          │ │                │  │
│  └──────────┘ └──────────┘ └────────────────┘  │
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Memory   │ │ Skills   │ │ Security       │  │
│  │ L1/L2/L3 │ │ Plugin   │ │ Audit + ACL    │  │
│  └──────────┘ └──────────┘ └────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │          LLM Client (Unified)             │   │
│  │   OpenAI  │  Anthropic  │  Custom (兼容)  │   │
│  │   gpt-4o  │  claude     │  deepseek/ollama│   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│              ↕ SQLAlchemy ORM                    │
│              ┌──────────┐                       │
│              │  SQLite   │  ChromaDB            │
│              └──────────┘                       │
└─────────────────────────────────────────────────┘
```
