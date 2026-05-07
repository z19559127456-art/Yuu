# vx版Agent集合体 — 剩余工作清单

> 更新时间：2026-05-07
> 当前版本：v0.5.0
> 测试状态：277 个测试全部通过，整体行覆盖率 52%

---

## 一、当前完成情况

### 已全部完成

- ✅ Phase 1 MVP（单Agent对话 + CLI工具）
- ✅ Phase 2 核心功能（PWC架构 + 工具层 + 技能/记忆 + 并发控制）
- ✅ Phase 3 多Agent协作（群聊 + 讨论模式 + 防死循环 + UI自动化）
- ✅ Phase 4 中的 Vision/L3记忆/安全/消息增强/i18n/导入导出
- ✅ 单元测试：277 个测试（后端236 + 前端41）
- ✅ 生产构建：Vite 前端 dist/ 输出 (329KB)
- ✅ 4个生产代码Bug已修复

### 部分完成

- 🔶 测试覆盖：单元测试完备（52%），缺少集成测试和E2E测试
- 🔶 Electron打包：配置文件就绪，构建环境待修复

---

## 二、剩余工作详情

### P0 — 必须完成才能发布

| # | 任务 | 说明 | 预计时间 |
|---|------|------|:---:|
| 1 | **修复 Electron 打包** | app-builder.exe 执行失败，需排查 Windows 权限/二进制兼容问题；考虑换用 electron-forge 或手动打包 | 2-4h |
| 2 | **后端 ws_handler 集成测试** | 当前覆盖率仅 13%（457行）。需 mock WebSocket 对象，测试 handle_message 各消息类型分发逻辑 | 3-4h |
| 3 | **前端 useWebSocket Hook 测试** | 需 mock WebSocket 连接，测试消息收发、重连逻辑、状态更新。当前未覆盖 | 2-3h |
| 4 | **前后端联调测试** | 启动后端 Flask 服务 + 前端 Vite 开发服务器，手动验证完整流程 | 2h |
| 5 | **依赖锁定** | 生成 `requirements.txt` freeze 版本 + `package-lock.json` 检查，确保可复现构建 | 0.5h |

### P1 — 发布前建议完成

| # | 任务 | 说明 | 预计时间 |
|---|------|------|:---:|
| 6 | **数据迁移脚本** | 创建 `backend/scripts/migrate.py`，支持数据库版本升级。DEVELOPMENT.md 中已规划但未实现 | 2h |
| 7 | **应用图标** | 设计/生成 icon.ico（Windows）和 icon.icns（macOS），放入 `frontend/public/` | 1-2h |
| 8 | **NSIS 安装程序** | 配置 electron-builder NSIS 参数（中文安装界面、桌面快捷方式、卸载程序） | 1h |
| 9 | **LLM 集成测试** | 使用 mock API 测试 llm_client.py（当前26%覆盖率），验证流式输出和 tool calling 循环 | 3h |
| 10 | **工具层集成测试** | web_tool (16%) / vision_tool (31%) / ui_tool (0%) 需要真实环境或 mock 测试 | 3-4h |
| 11 | **技能模块测试** | skills/code_review.py 和 skills/summarize.py 当前0%覆盖，需 mock LLM 测试 | 2h |
| 12 | **编排器集成测试** | orchestrator.py (29%) — mock P/W/C 组件，验证完整的 Plan→Work→Critic 状态机 | 3h |

### P2 — 后续版本

| # | 任务 | 说明 | 预计时间 |
|---|------|------|:---:|
| 13 | **自动更新机制** | 集成 electron-updater，实现应用内版本检查和自动更新 | 3-4h |
| 14 | **E2E 测试** | 使用 Playwright 编写端到端测试，测试完整用户流程 | 4-6h |
| 15 | **CI/CD 流水线** | 配置 GitHub Actions：lint → test → build → release | 3-4h |
| 16 | **性能基准测试** | 测试 WebSocket 并发连接、LLM 流式延迟、大消息列表渲染性能 | 2h |
| 17 | **macOS/Linux 构建** | 验证并配置跨平台 electron-builder 构建 | 1-2h |
| 18 | **安全审计** | 完整的代码安全审查（依赖漏洞、SQL注入、XSS等） | 3-4h |

---

## 三、当前测试覆盖率明细

### 后端（236 tests, 52% 行覆盖率）

| 覆盖率等级 | 模块 |
|:---:|------|
| **90%+** | models (99%), config (100%), __init__ (100%), context_manager (97%), deadlock_detector (95%), concurrency (93%), security (91%) |
| **70-90%** | cli_tool (87%), critic (82%), group_chat_bus (75%), import_export (74%), memory_manager (72%), skill_manager (72%) |
| **50-70%** | planner (65%), vector_memory (65%) |
| **<50%** | **ws_handler (13%)**, **web_tool (16%)**, **worker (27%)**, **orchestrator (29%)**, **collaboration_engine (39%)**, **vision_tool (31%)** |
| **0%** | main.py, skills/code_review.py, skills/summarize.py, ui_tool.py |

### 前端（41 tests, 5个测试文件）

| 测试文件 | 测试数 |
|---------|:-----:|
| useStore.test.ts | 17 |
| MessageBubble.test.tsx | 7 |
| i18n.test.ts | 6 |
| ToolOutput.test.tsx | 6 |
| PlanView.test.tsx | 5 |

待补充：
- `useWebSocket.test.ts` — WebSocket 连接/Mock/重连测试
- `ChatInput.test.tsx` — 输入组件测试
- `Layout.test.tsx` — 布局组件测试
- `ContactsView.test.tsx` — 通讯录视图测试

---

## 四、Electron 打包问题分析

### 当前错误

```
app-builder.exe process failed ERR_ELECTRON_BUILDER_CANNOT_EXECUTE
```

### 已尝试的方案

| 方案 | 结果 |
|------|------|
| `electron-builder --win` | ❌ signing 阶段失败 |
| `electron-builder --dir --win` | ❌ 同样错误 |
| `electron-builder --win --ia32` | ❌ packaging 阶段失败 |

### 推荐解决顺序

1. **确认 node_modules 完整性** — 重新安装依赖
   ```bash
   cd frontend
   rm -rf node_modules
   npm install
   ```

2. **换用 electron-forge** — 更稳定的打包工具
   ```bash
   npx create-electron-app --template=vite-typescript
   ```

3. **手动打包** — 最底层方案
   - 手动下载 Electron 二进制
   - 将 dist/ 和 electron/ 复制到 resources/app/
   - 打包为 zip/portable

4. **开发模式运行** — 如果只是本地使用
   ```bash
   cd frontend
   npm run electron:dev
   ```

---

## 五、快速启动命令参考

### 后端测试

```bash
cd backend
venv\Scripts\activate

# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_models.py -v

# 覆盖率报告
python -m pytest tests/ --cov=app --cov-report=html

# 启动后端服务
python -m app.main
```

### 前端测试

```bash
cd frontend

# 运行所有测试
npx vitest run

# 开发模式运行
npm run dev

# 生产构建
npx vite build

# Electron 开发模式
npm run electron:dev
```

---

## 六、工作量估算

| 优先级 | 任务数 | 预计总时间 |
|:---:|:-----:|:---------:|
| P0（必须） | 5 | 10-14 小时 |
| P1（建议） | 7 | 15-20 小时 |
| P2（后续） | 6 | 18-24 小时 |
| **合计** | **18** | **43-58 小时** |

---

## 七、完成度评估

```
████████████████████░░░░░░░░░░    ~80%

功能开发:  ████████████████████  100%
单元测试:  ████████████████░░░░   80%
集成测试:  ██████░░░░░░░░░░░░░░   30%
E2E测试:   ░░░░░░░░░░░░░░░░░░░░    0%
打包发布:  ██████░░░░░░░░░░░░░░   30%
运维设施:  ██░░░░░░░░░░░░░░░░░░   10%

整体:      ████████████████░░░░  ~75-80%
```
