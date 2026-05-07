# 多对话框并行执行方案

> **目标**：8个 Claude Code 对话框同时工作，零文件覆盖冲突。
> **核心原则**：每个文件**只属于一个对话框**，互不交叉。

---

## 📋 执行总览

```
┌──────────────────────────────────────────────────────────────────┐
│  第1轮: 以下 7 个对话框可以同时打开、同时执行 (零冲突)          │
│                                                                  │
│  A ── Data Models & Config    (models.py + config.py)           │
│  B ── Web/UI/Vision/Export     (5个新Python模块)                 │
│  C ── Planner/Worker/Critic     (5个新Python模块)                │
│  D ── Skill/Memory/Vector      (4个新模块 + skills目录)          │
│  E ── GroupChat/Deadlock/Security (4个新Python模块)              │
│  F ── Frontend 新组件           (5个新TSX组件 + i18n框架)        │
│  G ── Phase 1 Week 4 CLI前端   (修改5个现有前端文件)             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  第2轮: 必须在第1轮所有对话框结束后执行 (集成)                  │
│                                                                  │
│  H ── 最终集成                (ws_handler + types + hook +      │
│                                 store + context + llm_client)    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 第1轮（7个对话框同时执行）

---

### 对话框 A — 数据模型 & 配置

**修改文件**：
- `backend/app/models.py` — 追加新 ORM 模型
- `backend/app/config.py` — 追加新配置项

**执行内容**：

1. 在 `models.py` 末尾追加：
   - `WebRecord` — Web 自动化执行记录
   - `UIRecord` — UI 自动化执行记录
   - `VisionRecord` — Vision 调用记录
   - `Plan` — 任务计划（含 status/subtasks JSON）
   - `SubTask` — 子任务
   - `TaskExecution` — 任务执行记录
   - `SkillRecord` — 技能调用记录
   - `VectorMemoryEntry` — 向量记忆条目元数据
   - `GroupConversation` — 群聊会话
   - `GroupParticipant` — 群聊参与者
   - `DiscussionRound` — 讨论轮次
   - `AuditLog` — 安全审计日志

2. 在 `config.py` 追加：安全策略路径、ChromaDB 路径、并发上限等配置项

**不碰文件**：`ws_handler.py`、`context_manager.py`、`types/index.ts`、任何前端文件

---

### 对话框 B — Web/UI/Vision 自动化工具 + 导入导出

**新建文件**（仅新文件，不修改任何现有文件）：

| 文件 | 内容 |
|------|------|
| `backend/app/web_tool.py` | Playwright 浏览器自动化。类 `WebTool`，`execute(url, actions, ...)` 返回 `ToolResult` |
| `backend/app/ui_tool.py` | PyAutoGUI 桌面自动化。类 `UITool`，`execute(action, params, ...)` 返回 `ToolResult` |
| `backend/app/vision_tool.py` | Vision API 封装。类 `VisionTool`，`analyze(image_path, prompt, ...)` 返回 `ToolResult` |
| `backend/app/import_export.py` | JSON/Markdown 导入导出。类 `DataExporter` / `DataImporter` |

**接口规范**：
```python
# 所有工具类遵循统一接口:
async def execute(params: dict, cancel_token=None, on_progress=None) -> ToolResult:
    ...
```

**不碰文件**：任何 `.tsx`、`.ts`、`ws_handler.py`、`context_manager.py`

---

### 对话框 C — Planner/Worker/Critic + 并发控制

**新建文件**：

| 文件 | 内容 |
|------|------|
| `backend/app/planner.py` | Planner 角色：将大任务拆解为子任务 DAG |
| `backend/app/worker.py` | Worker 角色：执行单个子任务，调用 LLM/工具 |
| `backend/app/critic.py` | Critic 角色：验证 Worker 输出，质量打分 |
| `backend/app/orchestrator.py` | 调度器：协调 P/W/C 三人组，管理状态机 |
| `backend/app/concurrency.py` | 任务队列 + 并发调度 + 重试策略（指数退避） |

**核心接口**：
```python
# Planner
async def create_plan(task_description: str, agent_context: dict) -> Plan

# Worker  
async def execute_subtask(subtask: SubTask, context: dict) -> SubtaskResult

# Critic
async def evaluate(result: SubtaskResult, criteria: dict) -> Critique

# Orchestrator
async def run_pwc_cycle(task: str, agent: Agent) -> TaskResult

# Concurrency
class TaskQueue: async def enqueue(task); async def dequeue(); def get_status()
```

---

### 对话框 D — Skill 插件系统 + 记忆管理 L1/L2/L3

**新建文件**：

| 文件 | 内容 |
|------|------|
| `backend/app/skill_manager.py` | 技能加载器/热重载/注册表 |
| `backend/app/skills/__init__.py` | 内置技能包标记 |
| `backend/app/skills/code_review.py` | 内置技能：代码审查 |
| `backend/app/skills/summarize.py` | 内置技能：文本摘要 |
| `backend/app/memory_manager.py` | L1（会话缓存）+ L2（摘要）统一调度 |
| `backend/app/vector_memory.py` | L3 ChromaDB 向量记忆（增删查） |

**核心接口**：
```python
# Skill
class BaseSkill: name, description, async def execute(params) -> SkillResult

# MemoryManager
async def store(agent_id, messages); async def recall(agent_id, query) -> list[str]
async def summarize(agent_id) -> str

# VectorMemory
async def add_entry(agent_id, text, metadata); async def search(agent_id, query, top_k=5)
```

---

### 对话框 E — 群聊/讨论模式 + 安全系统

**新建文件**：

| 文件 | 内容 |
|------|------|
| `backend/app/collaboration_engine.py` | 多 Agent 编排引擎（任务模式 + 讨论模式） |
| `backend/app/group_chat_bus.py` | 群聊消息总线（广播/路由/持久化） |
| `backend/app/deadlock_detector.py` | 防死循环三层机制（话题漂移检测/重复检测/轮次上限） |
| `backend/app/security.py` | 权限/审计/隐私统一管理 |

**核心接口**：
```python
# GroupChatBus
async def publish(sender_id, group_id, message)
async def subscribe(group_id, handler)
async def get_history(group_id) -> list

# DeadlockDetector
def check(message_history) -> bool  # True = 检测到死循环

# Security
class SecurityManager: check_permission(user, action), log_audit(event), sanitize_output(text)
```

---

### 对话框 F — 前端新组件 + i18n 框架

**新建文件**（不修改任何现有文件）：

| 文件 | 内容 |
|------|------|
| `frontend/src/components/ToolOutput.tsx` | 工具执行结果展示面板（支持 text/image/json） |
| `frontend/src/components/PlanView.tsx` | Planner 任务树形展示 + 进度 |
| `frontend/src/components/TaskProgress.tsx` | 子任务执行进度条 + 状态徽标 |
| `frontend/src/components/TaskHistoryPanel.tsx` | 任务历史记录列表 |
| `frontend/src/components/GroupChatView.tsx` | 群聊视图（多角色消息流） |
| `frontend/src/i18n/index.ts` | i18n 框架初始化 |
| `frontend/src/i18n/zh-CN.ts` | 中文语言包 |
| `frontend/src/i18n/en-US.ts` | 英文语言包 |

**关键约定**：
- 组件 props 用内联 `interface` 定义（不要引入 `@/types`，因为 types/index.ts 在对话框 H 才会更新）
- 组件导出用 `export default function Xxx`
- i18n 框架只搭结构，不要修改现有组件的文本引用（那在对话框 G 和 H 做）
- 所有样式用 Tailwind 类 + `index.css`（已有）的自定义类

---

### 对话框 G — Phase 1 Week 4 CLI 前端 UI

**修改文件**（仅以下 5 个文件）：

| 文件 | 改动内容 |
|------|---------|
| `frontend/src/components/MessageBubble.tsx` | 新增 `role === 'tool'` 消息渲染分支；显示工具执行状态（进度/成功/失败）；工具输出折叠/展开 |
| `frontend/src/components/ChatInput.tsx` | 发送按钮旁加"执行工具"模式切换；工具执行中禁用输入显示"等待工具执行..." |
| `frontend/src/components/SettingsView.tsx` | 新增 CLI 工具安全配置面板（白名单/黑名单/超时设置） |
| `frontend/src/components/Sidebar.tsx` | 新增"任务历史"导航按钮 |
| `frontend/src/index.css` | 新增进度条、工具输出框、状态徽标的 Tailwind 自定义类 |

**不碰文件**：`ws_handler.py`、`types/index.ts`、`useWebSocket.ts`、`useStore.ts`、`context_manager.py`、`Layout.tsx`
（集成工作统一由对话框 H 完成）

**前端组件内联类型**：不要修改 `types/index.ts`，在组件文件内部定义需要的局部类型，例如：
```typescript
// 在 ToolOutput.tsx 内部，不要加到 types/index.ts
interface ToolExecutionState {
  status: 'running' | 'success' | 'failed';
  progress: number;
  output: string;
}
```

---

## 第2轮（最终集成，必须最后执行）

### 对话框 H — 最终集成

**等待条件**：对话框 A~G 全部执行完毕

**修改文件**：

| 文件 | 改动内容 |
|------|---------|
| `backend/app/ws_handler.py` | 🔥 添加所有新消息类型的路由 handler（tool_call, plan_create, memory_query, group_send, message_edit 等） |
| `backend/app/context_manager.py` | 🔥 集成工具定义注入、技能注入、记忆检索、多角色 system prompt |
| `backend/app/llm_client.py` | 添加 tool calling / function calling 支持（LLM 选择工具的循环） |
| `frontend/src/types/index.ts` | 🔥 添加所有新消息类型、新数据接口（ToolResult, Plan, SubTask, GroupMessage 等） |
| `frontend/src/hooks/useWebSocket.ts` | 🔥 添加所有新 WS 消息的处理分支（tool_result, plan_update, memory_result, group_message 等） |
| `frontend/src/store/useStore.ts` | 添加所有新 state（plan, taskHistory, groupChats, toolExecutions 等） |
| `frontend/src/components/Layout.tsx` | 集成新视图（群聊视图、任务历史面板等） |
| `frontend/src/components/AgentList.tsx` | 添加群聊列表项支持 |

**执行顺序**（在此对话框内按序完成）：
```
① types/index.ts → ② useStore.ts → ③ llm_client.py → ④ context_manager.py
→ ⑤ ws_handler.py → ⑥ useWebSocket.ts → ⑦ Layout.tsx → ⑧ AgentList.tsx
```

---

## 🚦 执行流程

### 步骤 1：通用的对话开头（所有对话框共用）

打开 Claude Code 后，先发这条消息建立上下文：

> 我们正在开发一个 AI Agent Messenger 项目，在 `C:\Users\Z1004\Desktop\cc\ds\vx版agent集合体` 目录下。
> 你不用管文件冲突，我安排了多个对话框并行工作，每个对话框只拥有自己那部分文件。
> 
> **你不应该修改任何不属于本对话框的文件。如果遇到需要修改其他文件的地方，在代码里加 `// TODO(H): ...` 或 `# TODO(H): ...` 标记，留给集成对话框处理。**
> 
> 项目技术栈：
> - 后端：Python + Flask + SQLAlchemy + SQLite
> - 前端：React + TypeScript + Vite + Tailwind CSS + Zustand
> - 通信：WebSocket (Flask-Sock)

---

### 步骤 2：各对话框专用提示

#### 对话框 A — 数据模型

```
请修改 backend/app/models.py，追加以下 ORM 模型类（参考已有 Agent/Message 模型的写法）：
1. WebRecord — 记录 Web 工具执行结果
2. UIRecord — 记录 UI 工具执行结果  
3. VisionRecord — 记录 Vision 工具执行结果
4. Plan — 任务计划，含 status 字段和 subtasks_json
5. SubTask — 子任务，关联 Plan
6. TaskExecution — 任务执行记录，含 start_time/end_time/status
7. SkillRecord — 技能调用记录
8. VectorMemoryEntry — 向量记忆索引记录
9. GroupConversation — 群聊会话，支持多 Agent 参与
10. GroupParticipant — 群聊参与者
11. DiscussionRound — 讨论轮次记录
12. AuditLog — 安全审计日志

每个模型都要有 to_dict() 方法。
同时修改 backend/app/config.py，添加：
- SECURITY_POLICY_DIR
- CHROMADB_PATH
- MAX_CONCURRENT_TASKS (默认 5)
- TOOL_TIMEOUT_DEFAULT (默认 60 秒)
```

#### 对话框 B — 工具层

```
请在 backend/app/ 目录下新建以下文件：

1. web_tool.py — Playwright Web自动化工具
   - 类 WebTool，实现 execute(params, cancel_token, on_progress) 方法
   - params 包含 url, actions (点击/输入/截图/提取等)
   - 截图以 base64 返回
   - 支持超时控制

2. ui_tool.py — PyAutoGUI 桌面自动化工具
   - 要求：在 execute() 开头检查安全保护，鼠标移动超过 50px 必须经过中间点
   - 支持截图、点击、输入、按键

3. vision_tool.py — Vision API 工具
   - 封装 OpenAI Vision 和 Anthropic Vision
   - analyze(image_path_or_url, prompt) 返回分析结果
   - 支持多轮对话式分析

4. import_export.py — 导入导出工具
   - export_conversation(conv_id, format) → 'json' | 'markdown'
   - import_conversation(file_path) → conv_id
   - 支持导出为带 Markdown 渲染的可读格式

所有类使用 # TODO(H): wire into ws_handler 标记需要集成的位置。
```

#### 对话框 C — P/W/C 架构

```
请在 backend/app/ 目录下新建以下文件：

1. planner.py
   - create_plan(task_description, agent_config) → Plan (dataclass)
   - 将复杂任务拆解为有依赖关系的子任务列表
   - 每个子任务有：id, description, depends_on[], expected_output

2. worker.py
   - execute_subtask(subtask, context) → SubtaskResult
   - 调用 LLM 执行子任务，可调用工具
   - 返回 output, token_usage, tool_calls

3. critic.py
   - evaluate(subtask_result, quality_criteria) → Critique
   - 验证输出质量、完整性、一致性
   - 返回 pass/fail + 修改建议

4. orchestrator.py
   - run_pwc_cycle(task, agent) → 协调三步走
   - 管理状态机：PLANNING → WORKING → REVIEWING → REVISING → DONE

5. concurrency.py
   - TaskQueue 类：enqueue/dequeue/status/cancel
   - RetryHandler 类：指数退避重试，最大重试次数可配
```

#### 对话框 D — Skill + Memory

```
请在 backend/app/ 目录下新建：

1. skill_manager.py
   - Skill 基类 (BaseSkill): name, description, execute(params)
   - SkillRegistry: register(), unregister(), load_from_dir(), get_skill()
   - 支持热重载：watchdog 监控 skills/ 目录变化

2. skills/__init__.py (包标记)
3. skills/code_review.py
   - 内置技能：代码审查，分析 diff 或代码片段
4. skills/summarize.py
   - 内置技能：长文本摘要

5. memory_manager.py
   - MemoryManager 类
   - L1 缓存：当前会话最近 50 条消息
   - L2 摘要：当消息数超过阈值时自动生成摘要
   - store(agent_id, messages), recall(agent_id, query)
   - 使用 context_manager 的 build_messages 风格

6. vector_memory.py
   - VectorMemory 类 (L3)
   - 基于 Chromadb
   - add_entry(agent_id, text, metadata)
   - search(agent_id, query, top_k=5)
   - 所有操作失败时优雅降级（chromadb 可能不可用）
```

#### 对话框 E — 协作 + 安全

```
请在 backend/app/ 目录下新建：

1. collaboration_engine.py
   - 任务模式：调度多个 Agent 协作完成复杂任务
   - 讨论模式：多个 Agent 围绕话题讨论
   - assign_task(agent_id, task), collect_results() 

2. group_chat_bus.py
   - GroupChatBus 类：消息路由总线
   - publish(sender_id, group_id, message) 广播消息
   - subscribe(group_id, handler) 注册接收者
   - 消息持久化到数据库

3. deadlock_detector.py
   - 三层防死循环：
     ① 话题漂移检测（对比消息 embedding 相似度）
     ② 重复检测（最近 5 条去重）
     ③ 轮次上限（最多 N 轮讨论后终止）
   - check(messages) → (is_deadlocked, reason)

4. security.py
   - SecurityManager 类
   - check_permission(user, action, resource) → bool
   - log_audit(event_type, user, details)
   - sanitize_output(text) → 脱敏处理
   - access_control(resource, agent_id) → bool
```

#### 对话框 F — 前端新组件

```
请在 frontend/src/components/ 目录下新建以下组件（不要修改现有文件！）：

1. ToolOutput.tsx
   - 展示工具执行结果
   - 支持文本、JSON、图片 base64 三种输出格式
   - 带折叠/展开功能
   - Props 用内联 interface 定义

2. PlanView.tsx
   - 展示 Planner 的任务分解树
   - 每个子任务显示状态图标 (待办/进行中/完成/失败)
   - 依赖关系用连线或缩进表示
   - 使用 Tailwind

3. TaskProgress.tsx
   - 进度条 + 百分比 + 状态徽标
   - 支持多个子任务的并行进度
   - animated

4. TaskHistoryPanel.tsx
   - 任务历史记录列表
   - 按时间排序，显示任务类型/状态/耗时
   - 可点击查看详情

5. GroupChatView.tsx
   - 群聊消息流视图
   - 每条消息显示 Agent 头像+名称+内容
   - 与现有 ChatArea 风格一致

6. frontend/src/i18n/index.ts — i18n初始化
7. frontend/src/i18n/zh-CN.ts — 中文文本
8. frontend/src/i18n/en-US.ts — 英文文本

重要：所有组件内部定义自己的类型接口，不要 import @/types（因为 types/index.ts 后续会被集成窗口统一更新）。
样式统一用 Tailwind。
```

#### 对话框 G — CLI Week 4 前端

```
请修改以下前端文件，为 CLI 工具执行添加 UI 支持：

1. frontend/src/components/MessageBubble.tsx
   - 在 message.role === 'tool' 时显示工具输出框（灰底、等宽字体）
   - 工具正在执行时显示加载动画 + "执行中..." 文字
   - 工具输出支持折叠/展开

2. frontend/src/components/ChatInput.tsx
   - 输入框下方添加工具执行状态栏
   - 工具正在执行时禁用发送按钮，改为显示 "等待工具执行..."
   - 工具出错时显示红色错误提示

3. frontend/src/components/SettingsView.tsx
   - 添加 CLI 工具安全配置区域：
     - 白名单命令输入框
     - 黑名单命令输入框
     - 默认超时时间滑块 (5-120 秒)
   - 这些配置暂时只做 UI（# TODO(H): 集成到 Agent tools_config）

4. frontend/src/components/Sidebar.tsx
   - 在 chats 和 contacts 之间添加"任务历史" (History) 按钮
   - 使用 lucide-react 的 Clock 图标

5. frontend/src/index.css
   - 添加工具输出的自定义样式
   - 进度条动画关键帧

重要：
- 不要修改 types/index.ts — 在组件内写局部类型
- 不要修改 useWebSocket.ts、useStore.ts — 集成工作留给对话框 H
- 涉及 WS 消息通信的地方写注释 // TODO(H): wire with ws_handler
```

---

### 步骤 3：集成（对话框 H，最后执行）

> 注意：请在对话框 A~G 全部完成后，再打开这个对话框执行集成。

```
所有新模块已经创建完毕，请将它们集成到现有系统中：

1. 修改 frontend/src/types/index.ts：
   - 添加 ToolResult, ToolExecution, Plan, SubTask, Critique 等接口
   - 添加所有新的 WSClientMessage 和 WSServerMessage 联合类型成员
   - 导出类型

2. 修改 frontend/src/store/useStore.ts：
   - 添加 toolExecutions, plans, taskHistory, groupChats 等 state
   - 添加对应的 setter actions

3. 修改 backend/app/llm_client.py：
   - 在 stream() 中添加 tool calling 支持：
     - OpenAI: 检测 tool_calls，执行工具，继续流式生成
     - Anthropic: 检测 tool_use，执行工具，继续流式生成
   - 需要导入 web_tool.WebTool, ui_tool.UITool, vision_tool.VisionTool, cli_tool.CLITool

4. 修改 backend/app/context_manager.py：
   - _build_system_prompt() 中为每种工具生成详细的 JSON 格式定义
   - 集成记忆管理器：从 memory_manager 加载 L1/L2 记忆
   - 集成技能：列出可用技能及用法

5. 修改 backend/app/ws_handler.py：
   - 添加 tool_call 处理 → 路由到对应 Tool.execute()
   - 添加 plan_create → 调用 orchestrator.run_pwc_cycle()
   - 添加 memory_query → 调用 memory_manager
   - 添加 group_send → 调用 group_chat_bus
   - 添加 message_edit / message_recall → 修改 Message 表
   - send_message 的处理中加入 function calling 循环
   - 错误处理+重试

6. 修改 frontend/src/hooks/useWebSocket.ts：
   - 在 handleServerMessage 的 switch 中添加所有新消息类型分支
   - tool_result → 更新 store.toolExecutions
   - plan_update → 更新 store.plans  
   - memory_result → 更新搜索结果
   - group_message → 更新群聊消息列表

7. 修改 frontend/src/components/Layout.tsx：
   - 当 activeNav 切换到新视图时渲染对应的新组件

8. 修改 frontend/src/components/AgentList.tsx：
   - 如果有群聊，在对话列表上方显示"群聊"分类

所有修改请确保：
- import 路径正确
- 新模块的接口签名与实现一致
- 完整的错误处理
```

---

## 📊 文件冲突矩阵（验证零冲突）

| 文件 | 属于对话框 | 其他对话框是否触碰 |
|------|-----------|------------------|
| `models.py` | **A** | ❌ 无 |
| `config.py` | **A** | ❌ 无 |
| `web_tool.py` (新) | **B** | ❌ 无 |
| `ui_tool.py` (新) | **B** | ❌ 无 |
| `vision_tool.py` (新) | **B** | ❌ 无 |
| `import_export.py` (新) | **B** | ❌ 无 |
| `planner.py` (新) | **C** | ❌ 无 |
| `worker.py` (新) | **C** | ❌ 无 |
| `critic.py` (新) | **C** | ❌ 无 |
| `orchestrator.py` (新) | **C** | ❌ 无 |
| `concurrency.py` (新) | **C** | ❌ 无 |
| `skill_manager.py` (新) | **D** | ❌ 无 |
| `skills/` (新目录) | **D** | ❌ 无 |
| `memory_manager.py` (新) | **D** | ❌ 无 |
| `vector_memory.py` (新) | **D** | ❌ 无 |
| `collaboration_engine.py` (新) | **E** | ❌ 无 |
| `group_chat_bus.py` (新) | **E** | ❌ 无 |
| `deadlock_detector.py` (新) | **E** | ❌ 无 |
| `security.py` (新) | **E** | ❌ 无 |
| `ToolOutput.tsx` (新) | **F** | ❌ 无 |
| `PlanView.tsx` (新) | **F** | ❌ 无 |
| `TaskProgress.tsx` (新) | **F** | ❌ 无 |
| `TaskHistoryPanel.tsx` (新) | **F** | ❌ 无 |
| `GroupChatView.tsx` (新) | **F** | ❌ 无 |
| `i18n/*` (新目录) | **F** | ❌ 无 |
| `MessageBubble.tsx` | **G** | ❌ 无 |
| `ChatInput.tsx` | **G** | ❌ 无 |
| `SettingsView.tsx` | **G** | ❌ 无 |
| `Sidebar.tsx` | **G** | ❌ 无 |
| `index.css` | **G** | ❌ 无 |
| `ws_handler.py` | **H** | ❌ 无 |
| `context_manager.py` | **H** | ❌ 无 |
| `llm_client.py` | **H** | ❌ 无 |
| `types/index.ts` | **H** | ❌ 无 |
| `useWebSocket.ts` | **H** | ❌ 无 |
| `useStore.ts` | **H** | ❌ 无 |
| `Layout.tsx` | **H** | ❌ 无 |
| `AgentList.tsx` | **H** | ❌ 无 |

---

## ⚠️ 安全规则

1. **每次只开 7 个对话框**（A-G 同时，H 最后），开太多容易混淆
2. **启动每个对话框前**，确认编辑的文件没有被别的对话框修改
3. **对话框 G 修改现有前端文件**，如果遇上 git diff 冲突，手动合并
4. **对话框 H 最复杂**，建议预留足够上下文窗口
5. **接口契约**（本文件开头的接口规范页）是所有模块互相调用的约定，如果某个模块需要调整接口，在代码里加 `# TODO(H)` 注释，**不要跨对话框修改其他模块的文件**

---

## 📋 一键复制提示词

> 以下为每个对话框**可直接复制粘贴**到 Claude Code 的完整指令。

### 通用开头（所有对话框 A-G 共用）

```
我们正在开发一个 AI Agent Messenger 项目，在 C:\Users\Z1004\Desktop\cc\ds\vx版agent集合体 目录下。
你不用管文件冲突，我安排了多个对话框并行工作，每个对话框只拥有自己那部分文件。
你不应该修改任何不属于本对话框的文件。如果遇到需要修改其他文件的地方，在代码里加 # TODO(H): ... 标记，留给集成对话框处理。

项目技术栈：
- 后端：Python + Flask + SQLAlchemy + SQLite
- 前端：React + TypeScript + Vite + Tailwind CSS + Zustand
- 通信：WebSocket (Flask-Sock)
```

---

### 对话框 A — 数据模型 & 配置

```
（通用开头）

请修改 backend/app/models.py，追加以下 ORM 模型类（参考已有 Agent/Message 模型的写法）：
1. WebRecord — Web 工具执行结果
2. UIRecord — UI 工具执行结果
3. VisionRecord — Vision 工具执行结果
4. Plan — 任务计划，含 status 字段和 subtasks_json
5. SubTask — 子任务，关联 Plan
6. TaskExecution — 任务执行记录，含 start_time/end_time/status
7. SkillRecord — 技能调用记录
8. VectorMemoryEntry — 向量记忆索引记录
9. GroupConversation — 群聊会话，支持多 Agent 参与
10. GroupParticipant — 群聊参与者
11. DiscussionRound — 讨论轮次记录
12. AuditLog — 安全审计日志

每个模型都要有 to_dict() 方法。

同时修改 backend/app/config.py，添加：
- SECURITY_POLICY_DIR
- CHROMADB_PATH
- MAX_CONCURRENT_TASKS (默认 5)
- TOOL_TIMEOUT_DEFAULT (默认 60 秒)
```

---

### 对话框 B — Web/UI/Vision 工具 + 导入导出

```
（通用开头）

请在 backend/app/ 目录下新建以下文件：

1. web_tool.py — Playwright Web自动化工具
   - 类 WebTool，实现 execute(params, cancel_token, on_progress) 方法
   - params 包含 url, actions (点击/输入/截图/提取等)
   - 截图以 base64 返回，支持超时控制

2. ui_tool.py — PyAutoGUI 桌面自动化工具
   - execute() 开头检查安全保护，鼠标移动超 50px 必须经中间点
   - 支持截图、点击、输入、按键

3. vision_tool.py — Vision API 工具
   - 封装 OpenAI Vision 和 Anthropic Vision
   - analyze(image_path_or_url, prompt) 返回分析结果

4. import_export.py — 导入导出工具
   - export_conversation(conv_id, format) → 'json' | 'markdown'
   - import_conversation(file_path) → conv_id

所有类使用 # TODO(H): wire into ws_handler 标记需要集成的位置。
```

---

### 对话框 C — Planner/Worker/Critic + 并发控制

```
（通用开头）

请在 backend/app/ 目录下新建以下文件：

1. planner.py
   - create_plan(task_description, agent_config) → Plan (dataclass)
   - 将复杂任务拆解为有依赖关系的子任务列表
   - 每个子任务有：id, description, depends_on[], expected_output

2. worker.py
   - execute_subtask(subtask, context) → SubtaskResult
   - 调用 LLM 执行子任务，可调用工具
   - 返回 output, token_usage, tool_calls

3. critic.py
   - evaluate(subtask_result, quality_criteria) → Critique
   - 验证输出质量、完整性、一致性，返回 pass/fail + 修改建议

4. orchestrator.py
   - run_pwc_cycle(task, agent) → 协调三步走
   - 状态机：PLANNING → WORKING → REVIEWING → REVISING → DONE

5. concurrency.py
   - TaskQueue 类：enqueue/dequeue/status/cancel
   - RetryHandler 类：指数退避重试，最大重试次数可配
```

---

### 对话框 D — Skill 插件 + 记忆管理

```
（通用开头）

请在 backend/app/ 目录下新建：

1. skill_manager.py
   - Skill 基类 (BaseSkill): name, description, execute(params)
   - SkillRegistry: register(), unregister(), load_from_dir(), get_skill()
   - 支持热重载：watchdog 监控 skills/ 目录变化

2. skills/__init__.py (包标记)

3. skills/code_review.py — 内置技能：代码审查，分析 diff 或代码片段

4. skills/summarize.py — 内置技能：长文本摘要

5. memory_manager.py
   - MemoryManager 类
   - L1 缓存：当前会话最近 50 条消息
   - L2 摘要：消息数超阈值时自动生成摘要
   - store(agent_id, messages), recall(agent_id, query)

6. vector_memory.py
   - VectorMemory 类 (L3)，基于 Chromadb
   - add_entry(agent_id, text, metadata)
   - search(agent_id, query, top_k=5)
   - 操作失败时优雅降级（chromadb 可能不可用）
```

---

### 对话框 E — 群聊/讨论/安全

```
（通用开头）

请在 backend/app/ 目录下新建：

1. collaboration_engine.py
   - 任务模式：调度多个 Agent 协作完成复杂任务
   - 讨论模式：多个 Agent 围绕话题讨论
   - assign_task(agent_id, task), collect_results()

2. group_chat_bus.py
   - GroupChatBus 类：消息路由总线
   - publish(sender_id, group_id, message) 广播消息
   - subscribe(group_id, handler) 注册接收者
   - 消息持久化到数据库

3. deadlock_detector.py
   - 三层防死循环：
     ① 话题漂移检测（对比消息 embedding 相似度）
     ② 重复检测（最近 5 条去重）
     ③ 轮次上限（最多 N 轮后终止）
   - check(messages) → (is_deadlocked, reason)

4. security.py
   - SecurityManager 类
   - check_permission(user, action, resource) → bool
   - log_audit(event_type, user, details)
   - sanitize_output(text) → 脱敏处理
```

---

### 对话框 F — 前端新组件 + i18n

```
（通用开头）

请在 frontend/src/components/ 目录下新建以下组件（不要修改现有文件！）：

1. ToolOutput.tsx — 工具执行结果展示面板，支持 text/json/image base64，带折叠/展开功能。Props 用内联 interface 定义。

2. PlanView.tsx — Planner 任务分解树，子任务状态图标（待办/进行中/完成/失败），Tailwind 样式。

3. TaskProgress.tsx — 进度条 + 百分比 + 状态徽标，支持多子任务并行进度，带动画。

4. TaskHistoryPanel.tsx — 任务历史记录列表，按时间排序，显示类型/状态/耗时，点击查看详情。

5. GroupChatView.tsx — 群聊消息流视图，每条消息显示 Agent 头像+名称+内容，与现有 ChatArea 风格一致。

6. frontend/src/i18n/index.ts — i18n 初始化（只搭结构，不改现有组件）

7. frontend/src/i18n/zh-CN.ts — 中文语言包

8. frontend/src/i18n/en-US.ts — 英文语言包

重要规则：
- 组件内部定义自己的类型接口，不要 import @/types（types/index.ts 由集成窗口统一更新）
- 组件导出用 export default function Xxx
- i18n 只搭框架，不要修改现有组件文本
- 所有样式用 Tailwind 类
```

---

### 对话框 G — Phase 1 Week 4 CLI 前端

```
（通用开头）

请修改以下前端文件，为 CLI 工具执行添加 UI 支持：

1. frontend/src/components/MessageBubble.tsx
   - message.role === 'tool' 时显示工具输出框（灰底、等宽字体）
   - 工具执行中显示加载动画 + "执行中..." 文字
   - 工具输出支持折叠/展开

2. frontend/src/components/ChatInput.tsx
   - 输入框下方添加工具执行状态栏
   - 工具执行中禁用发送按钮，改为显示"等待工具执行..."
   - 工具出错时显示红色错误提示

3. frontend/src/components/SettingsView.tsx
   - 添加 CLI 工具安全配置区域：白名单命令、黑名单命令、超时滑块(5-120s)
   - 用 # TODO(H): 集成到 Agent tools_config 标记

4. frontend/src/components/Sidebar.tsx
   - chats 和 contacts 之间添加"任务历史"按钮，用 lucide-react 的 Clock 图标

5. frontend/src/index.css
   - 工具输出样式 + 进度条动画关键帧

重要：
- 不要修改 types/index.ts — 组件内写局部类型
- 不要修改 useWebSocket.ts、useStore.ts — 集成工作留给对话框 H
- 涉及 WS 通信的地方写注释 // TODO(H): wire with ws_handler
```

---

### 对话框 H — 最终集成（最后执行！）

> ⚠️ 等待对话框 A~G 全部完成后，再打开这个对话框执行。

```
所有新模块已经创建完毕，请将它们集成到现有系统中。

1. 修改 frontend/src/types/index.ts：
   - 添加 ToolResult, ToolExecution, Plan, SubTask, Critique 等接口
   - 添加所有新的 WSClientMessage 和 WSServerMessage 联合类型成员

2. 修改 frontend/src/store/useStore.ts：
   - 添加 toolExecutions, plans, taskHistory, groupChats 等 state
   - 添加对应的 setter actions

3. 修改 backend/app/llm_client.py：
   - stream() 中添加 tool calling：OpenAI 检测 tool_calls，Anthropic 检测 tool_use
   - 导入 web_tool.WebTool, ui_tool.UITool, vision_tool.VisionTool, cli_tool.CLITool

4. 修改 backend/app/context_manager.py：
   - _build_system_prompt() 为每种工具生成 JSON 格式定义
   - 集成 memory_manager 加载 L1/L2 记忆
   - 集成技能：列出可用技能及用法

5. 修改 backend/app/ws_handler.py：
   - tool_call → 路由到对应 Tool.execute()
   - plan_create → orchestrator.run_pwc_cycle()
   - memory_query → memory_manager
   - group_send → group_chat_bus
   - message_edit / message_recall
   - send_message 中加入 function calling 循环

6. 修改 frontend/src/hooks/useWebSocket.ts：
   - handleServerMessage 中添加 tool_result, plan_update, memory_result, group_message 等分支

7. 修改 frontend/src/components/Layout.tsx：
   - activeNav 切换到新视图时渲染对应的新组件

8. 修改 frontend/src/components/AgentList.tsx：
   - 有群聊时在对话列表上方显示"群聊"分类

所有修改请确保 import 路径正确，接口签名一致，有完整错误处理。
```
