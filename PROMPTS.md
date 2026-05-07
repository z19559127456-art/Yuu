# 并行开发提示词 — 8 个对话框

---

## 通用开头（所有对话框 A-H 共用）

在 Claude Code 中先发送这段建立上下文：

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

## 对话框 A — 数据模型 & 配置

**操作文件**：`backend/app/models.py`、`backend/app/config.py`

```
- [x] Agent 模型增强（19+ 字段：personality/tools/skills/memory/concurrency 等，含 to_dict()）
- [x] WebRecord — Web 工具执行结果
- [x] UIRecord — UI 工具执行结果
- [x] VisionRecord — Vision 工具执行结果
- [x] Plan — 任务计划，含 status 字段和 subtasks_json
- [x] SubTask — 子任务，关联 Plan
- [x] TaskExecution — 任务执行记录，含 start_time/end_time/status
- [x] SkillRecord — 技能调用记录
- [x] VectorMemoryEntry — 向量记忆索引记录
- [x] GroupConversation — 群聊会话，支持多 Agent 参与
- [x] GroupParticipant — 群聊参与者
- [x] DiscussionRound — 讨论轮次记录
- [x] AuditLog — 安全审计日志

config.py：
- [x] 已有的 DATA_DIR、API Keys 配置
- [x] SECURITY_POLICY_DIR
- [x] CHROMADB_PATH
- [x] MAX_CONCURRENT_TASKS (默认 5)
- [x] TOOL_TIMEOUT_DEFAULT (默认 60 秒)
```

---

## 对话框 B — Web/UI/Vision 工具 + 导入导出

**新建文件**：`backend/app/web_tool.py`、`ui_tool.py`、`vision_tool.py`、`import_export.py`

```
- [x] ~~cli_tool.py~~（已在其他轮次完成 — 命令白名单/黑名单/沙箱执行/流式输出）
- [x] web_tool.py — Playwright Web自动化工具
- [x] ui_tool.py — PyAutoGUI 桌面自动化工具
- [x] vision_tool.py — Vision API 工具
- [x] import_export.py — 导入导出工具
```

---

## 对话框 C — Planner/Worker/Critic + 并发控制

**新建文件**：`backend/app/planner.py`、`worker.py`、`critic.py`、`orchestrator.py`、`concurrency.py`

```
- [x] planner.py — 任务拆解为有依赖关系的子任务
- [x] worker.py — LLM 执行子任务
- [x] critic.py — 输出质量验证
- [x] orchestrator.py — 三步协调状态机
- [x] concurrency.py — TaskQueue + RetryHandler
```

---

## 对话框 D — Skill 插件 + 记忆管理

**新建文件**：`backend/app/skill_manager.py`、`skills/`、`memory_manager.py`、`vector_memory.py`

```
- [x] skill_manager.py — Skill 基类 + SkillRegistry + 热重载
- [x] skills/__init__.py
- [x] skills/code_review.py — 内置技能
- [x] skills/summarize.py — 内置技能
- [x] memory_manager.py — L1 缓存 + L2 摘要
- [x] vector_memory.py — L3 Chromadb 向量记忆
```

---

## 对话框 E — 群聊/讨论/安全

**新建文件**：`backend/app/collaboration_engine.py`、`group_chat_bus.py`、`deadlock_detector.py`、`security.py`

```
- [x] collaboration_engine.py — 任务模式 + 讨论模式
- [x] group_chat_bus.py — 消息路由总线
- [x] deadlock_detector.py — 三层防死循环
- [x] security.py — 权限检查 + 审计日志 + 脱敏
```

---

## 对话框 F — 前端新组件 + i18n

**新建文件**：`frontend/src/components/ToolOutput.tsx`、`PlanView.tsx`、`TaskProgress.tsx`、`TaskHistoryPanel.tsx`、`GroupChatView.tsx`、`frontend/src/i18n/`

```
- [x] ToolOutput.tsx — 工具执行结果展示面板
- [x] PlanView.tsx — 任务分解树
- [x] TaskProgress.tsx — 进度条组件
- [x] TaskHistoryPanel.tsx — 任务历史记录列表
- [x] GroupChatView.tsx — 群聊消息流视图
- [x] frontend/src/i18n/index.ts — i18n 初始化
- [x] frontend/src/i18n/zh-CN.ts — 中文语言包
- [x] frontend/src/i18n/en-US.ts — 英文语言包
```

---

## 对话框 G — Phase 1 Week 4 CLI 前端

**修改文件**：`frontend/src/components/MessageBubble.tsx`、`ChatInput.tsx`、`SettingsView.tsx`、`Sidebar.tsx`、`frontend/src/index.css`

```
- [x] MessageBubble.tsx — Markdown 渲染 + 流式消息显示 + 打字指示器动画
- [x] ChatInput.tsx — 工具执行状态栏 + 等待提示 + 错误提示
- [x] SettingsView.tsx — CLI 安全配置区域（启用/禁用、命令白名单/黑名单、超时设置）
- [x] Sidebar.tsx — 三栏导航（消息/通讯录/设置）
- [x] index.css — Markdown 样式 + 滚动条 + 打字点动画
```

---

## 对话框 H — 最终集成（最后执行！）

> ⚠️ 等待对话框 A~G 全部完成后，再打开这个对话框执行。

**修改文件**：`frontend/src/types/index.ts`、`frontend/src/store/useStore.ts`、`backend/app/llm_client.py`、`backend/app/context_manager.py`、`backend/app/ws_handler.py`、`frontend/src/hooks/useWebSocket.ts`、`frontend/src/components/Layout.tsx`、`frontend/src/components/AgentList.tsx`

```
- [x] types/index.ts — 全面更新：Agent 完整类型、Message 增强、WS 消息类型（含 message_update/message_final）
- [x] useStore.ts — 新增 Agent CRUD actions、updateMessageContent/finalizeMessage、UI state（showAgentForm/editingAgent）
- [x] llm_client.py — 新建，支持 OpenAI + Anthropic 流式输出
- [x] context_manager.py — 新建，含系统提示构建 + 历史摘要 + L2 记忆注入
- [x] ws_handler.py — 完全重写：Agent CRUD + LLM 流式 + 对话管理
- [x] useWebSocket.ts — 新增 message_update/message_final/agent_crud 等消息处理器
- [x] Layout.tsx — 支持 contacts/settings/chats 三栏切换
- [x] AgentList.tsx — 显示当前 Agent 名称 + 新建对话按钮

集成完成（B~G 模块已全部接入）：
- [x] tool_call → 路由到 CLI/Web/UI/Vision 各 Tool.execute()
- [x] plan_create → Planner + Orchestrator PWC 周期
- [x] group_send → GroupChatBus 广播
- [x] memory_query → VectorMemory 向量搜索 + L2 回退
- [x] 消息编辑/撤回/引用
- [x] function calling 循环（LLM 输出中解析 TOOL_CALL: 模式并执行）
```
