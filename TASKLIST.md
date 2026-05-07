# vx版Agent集合体 — 开发任务清单

---

## Phase 1 — MVP（单 Agent 对话）

### Week 1-3 ✅ 已完成基础骨架

- ✅ 项目骨架：Flask + Electron/React
- ✅ 基础 UI：微信风格三栏布局
- ✅ WebSocket 通信 + 自动重连
- ✅ Agent 数据模型（完整 ORM）
- ✅ Agent CRUD（创建/编辑/删除/列表）
- ✅ Agent 管理 UI（通讯录视图 + 创建表单）
- ✅ LLM 集成（OpenAI + Anthropic 流式输出）
- ✅ 对话上下文管理（系统提示 + 历史摘要）
- ✅ Markdown 渲染 + 代码高亮
- ✅ 流式消息显示 + 思考中动画
- ✅ CLI 工具后端（白名单/黑名单安全控制）

### Week 4 — CLI 工具前端联调（已完成 ✅）

- [x] 前端：工具执行状态显示 + 进度条
- [x] 前端：工具输出展示
- [x] 联调：Agent 调用 CLI 工具完整流程
- [x] 联调：错误处理和重试

---

## Phase 2 — 核心功能（全部完成 ✅）

- [x] Planner/Worker/Critic 三角架构
- [x] Web 自动化工具 (Playwright)
- [x] Skill 插件系统 (加载器/热重载/内置技能)
- [x] 记忆管理 L1/L2 + 任务历史面板
- [x] 并发控制 + 重试策略 + 配置管理

---

## Phase 3 — 多 Agent 协作（全部完成 ✅）

- [x] 群聊 UI + 多 Agent 协作引擎
- [x] 讨论模式 (GroupChatBus + 防死循环)
- [x] UI 自动化工具 (PyAutoGUI) + 安全保护

---

## Phase 4 — 完善与发布

- [x] Vision 工具 + L3 向量记忆 (ChromaDB)
- [x] 安全系统 (权限/审计/隐私) + 增强功能
- [x] 消息编辑/撤回/引用 + 导入导出 + i18n
- [ ] 测试覆盖 + 打包发布 (Electron)
