# vx版Agent集合体 - 开发流程

## 目录

- [环境准备](#环境准备)
- [项目初始化](#项目初始化)
- [Phase 1: MVP 开发](#phase-1-mvp-开发)
- [Phase 2: 核心功能开发](#phase-2-核心功能开发)
- [Phase 3: 多Agent协作](#phase-3-多agent协作)
- [Phase 4: 完善与发布](#phase-4-完善与发布)
- [开发规范](#开发规范)
- [测试流程](#测试流程)
- [发布流程](#发布流程)

---

## 环境准备

### 系统要求

- Windows 10/11
- Python 3.10+
- Node.js 18+

### 安装步骤

#### 1. 安装 Python

从 [python.org](https://www.python.org/downloads/) 下载并安装 Python 3.10+

```bash
# 验证
python --version
pip --version
```

#### 2. 安装 Node.js

从 [nodejs.org](https://nodejs.org/) 下载并安装 Node.js 18+

```bash
# 验证
node --version
npm --version
```

#### 3. 克隆/进入项目

```bash
cd "C:\Users\Z1004\Desktop\cc\ds\vx版agent集合体"
```

---

## 项目初始化

### 1. 后端初始化

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
# (待实现)
```

### 2. 前端初始化

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 3. 配置文件

创建 `.env` 文件：

```bash
# 复制环境变量模板
copy .env.example .env

# 编辑 .env，填入你的配置
```

`.env` 示例：

```env
# LLM 配置
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# 应用配置
DATA_DIR=%APPDATA%/AgentMessengerOS
LOG_LEVEL=INFO
```

---

## Phase 1: MVP 开发

**目标**: 核心单 Agent 对话功能  
**预计时间**: 4 周

### Week 1: 项目骨架 + UI

- [ ] 后端
  - [ ] Flask 应用初始化
  - [ ] WebSocket 服务器
  - [ ] 基础目录结构
  - [ ] 数据库模型 (Agent, Conversation, Message)

- [ ] 前端
  - [ ] Electron + React + TypeScript 配置
  - [ ] 微信风格布局 (三栏: 导航 + Agent列表 + 聊天区)
  - [ ] 消息列表组件
  - [ ] 输入框组件

- [ ] 联调
  - [ ] 前后端 WebSocket 通信
  - [ ] 基础消息收发

### Week 2: Agent 管理

- [ ] 后端
  - [ ] Agent CRUD API
  - [ ] Agent 数据模型完整实现
  - [ ] Agent 持久化 (SQLite)

- [ ] 前端
  - [ ] Agent 列表 UI
  - [ ] 创建/编辑 Agent 面板
  - [ ] Agent 配置表单

- [ ] 联调
  - [ ] Agent 创建流程
  - [ ] Agent 切换

### Week 3: LLM 集成

- [ ] 后端
  - [ ] LLM Client 封装 (支持 OpenAI/Anthropic)
  - [ ] 对话上下文管理
  - [ ] 流式响应支持

- [ ] 前端
  - [ ] 思考中加载动画
  - [ ] 流式消息显示
  - [ ] Markdown 渲染

- [ ] 联调
  - [ ] 完整对话流程
  - [ ] 对话历史持久化

### Week 4: CLI 工具

- [ ] 后端
  - [ ] CLI Tool 实现
  - [ ] 命令白名单/黑名单
  - [ ] 沙箱执行
  - [ ] 流式输出

- [ ] 前端
  - [ ] 工具执行状态显示
  - [ ] 进度条
  - [ ] 输出展示

- [ ] 联调
  - [ ] Agent 调用 CLI 工具
  - [ ] 错误处理和重试

---

## Phase 2: 核心功能开发

**目标**: 完整的 Agent 能力 + 工具 + 技能  
**预计时间**: 4 周

### Week 5: Planner / Worker / Critic

- [ ] 后端
  - [ ] Planner 实现 (任务拆解)
  - [ ] Worker 实现 (任务执行)
  - [ ] Critic 实现 (质量检查)
  - [ ] 三角架构集成

- [ ] 联调
  - [ ] 复杂任务拆解执行
  - [ ] 自动重试/修正

### Week 6: Web 自动化工具

- [ ] 后端
  - [ ] Web Tool (Playwright)
  - [ ] 域名白名单
  - [ ] 截图功能

- [ ] 前端
  - [ ] Web 操作预览
  - [ ] 截图显示

### Week 7: Skill 插件系统

- [ ] 后端
  - [ ] Skill Loader
  - [ ] 热重载机制
  - [ ] Skill 注册/调用
  - [ ] 内置 Skill 3个

- [ ] 前端
  - [ ] Skill 管理面板
  - [ ] Skill 配置 UI

### Week 8: 记忆管理

- [ ] 后端
  - [ ] L1 会话缓存
  - [ ] L2 摘要记忆 (自动压缩)
  - [ ] 任务执行历史

- [ ] 前端
  - [ ] 历史对话面板
  - [ ] 任务记录查看

---

## Phase 3: 多 Agent 协作

**目标**: 群聊 + 多 Agent 协作  
**预计时间**: 3 周

### Week 9: 群聊基础

- [ ] 后端
  - [ ] Group 数据模型
  - [ ] 群聊成员管理
  - [ ] GroupChatBus

- [ ] 前端
  - [ ] 群聊 UI
  - [ ] 多 Agent 消息显示

### Week 10: 任务模式

- [ ] 后端
  - [ ] Coordinator 角色
  - [ ] 任务分发
  - [ ] 结果汇总
  - [ ] DAG 可视化数据

- [ ] 前端
  - [ ] 任务依赖图展示
  - [ ] 执行进度监控

### Week 11: 讨论模式 + UI 自动化

- [ ] 后端
  - [ ] 讨论模式实现
  - [ ] 防死循环机制
  - [ ] UI Tool (PyAutoGUI)
  - [ ] 安全确认机制

- [ ] 前端
  - [ ] 操作预告弹窗
  - [ ] 确认/取消按钮

---

## Phase 4: 完善与发布

**目标**: 完善、安全、可发布  
**预计时间**: 3 周

### Week 12: 视觉 + 向量记忆

- [ ] 后端
  - [ ] Vision Tool
  - [ ] ChromaDB 集成 (L3)
  - [ ] 多 LLM 提供商统一接口

- [ ] 前端
  - [ ] 图片上传/预览
  - [ ] Agent 模板库

### Week 13: 安全 + 增强功能

- [ ] 后端
  - [ ] 细粒度权限控制
  - [ ] 审计日志
  - [ ] 隐私模式
  - [ ] 消息编辑/撤回/引用
  - [ ] 导入导出

- [ ] 前端
  - [ ] 右键菜单
  - [ ] 通知系统
  - [ ] i18n 中/英文切换

### Week 14: 测试 + 发布

- [ ] 测试
  - [ ] 单元测试覆盖
  - [ ] 集成测试
  - [ ] E2E 测试

- [ ] 发布准备
  - [ ] 数据迁移脚本
  - [ ] 自动更新
  - [ ] Electron 打包
  - [ ] 安装程序

---

## 开发规范

### Git 分支策略

```
main                # 稳定发布分支
  └── develop       # 开发分支
       ├── feature/xxx   # 功能分支
       ├── fix/xxx       # 修复分支
       └── refactor/xxx  # 重构分支
```

### 提交信息规范

```
<type>(<scope>): <subject>

类型:
  feat: 新功能
  fix: 修复
  docs: 文档
  style: 格式
  refactor: 重构
  test: 测试
  chore: 构建/工具
```

### 代码规范

#### Python

- 遵循 PEP 8
- 使用类型提示 (Type Hints)
- 使用 Black 格式化
- 使用 Ruff 检查

#### TypeScript

- 遵循 ESLint 规则
- 使用 Prettier 格式化
- 严格模式

---

## 测试流程

### 后端测试

```bash
cd backend
venv\Scripts\activate

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agent.py

# 覆盖率报告
pytest --cov=app
```

### 前端测试

```bash
cd frontend

# 运行测试
npm test

# E2E 测试
npm run test:e2e
```

---

## 发布流程

### 1. 版本准备

```bash
# 更新版本号
# 编辑 package.json 和 __init__.py

# 创建版本提交
git add .
git commit -m "chore: bump version to v0.5.0"
git tag v0.5.0
```

### 2. 构建

```bash
# 前端构建
cd frontend
npm run build

# Electron 打包
npm run electron:build
```

### 3. 发布检查清单

- [ ] 所有测试通过
- [ ] 文档更新
- [ ] 变更日志更新
- [ ] 安全审计通过
- [ ] 性能基准测试通过

---

## 常用命令速查

### 后端

```bash
cd backend
venv\Scripts\activate

# 启动开发服务器
python -m app.main

# 运行测试
pytest

# 格式化
black app/
```

### 前端

```bash
cd frontend

# 启动开发服务器
npm run dev

# 启动 Electron
npm run electron:dev

# 构建
npm run build
```

---

## 问题排查

### 后端常见问题

**虚拟环境激活失败**
- 确保使用 `venv\Scripts\activate` (Windows)

**依赖安装失败**
- 更新 pip: `python -m pip install --upgrade pip`
- 换源: `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 前端常见问题

**node_modules 安装慢**
- 换源: `npm config set registry https://registry.npmmirror.com`

**Electron 下载失败**
- 设置镜像: `npm config set electron_mirror https://npmmirror.com/mirrors/electron/`

---

## 资源链接

- [项目规格文档](./docs/AI_Agent_Messenger_OS_SPEC_完整版_v0.5.md)
- [README](./README.md)
- [Flask 文档](https://flask.palletsprojects.com/)
- [React 文档](https://react.dev/)
- [Electron 文档](https://www.electronjs.org/docs)
