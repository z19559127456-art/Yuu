# 快速启动指南

## 当前进度

已完成 Phase 1 Week 1-3（项目骨架 + Agent 管理 + LLM 集成）

- [x] 项目骨架：Electron + React + Python Flask
- [x] 基础 UI：微信风格三栏布局
- [x] WebSocket 通信 + 自动重连
- [x] Agent 数据模型（完整版含19+字段）
- [x] Agent CRUD（创建/编辑/删除/列表）
- [x] Agent 管理 UI（通讯录视图 + 创建表单）
- [x] LLM 集成（OpenAI + Anthropic 流式输出）
- [x] 对话上下文管理（系统提示 + 历史摘要）
- [x] Markdown 渲染 + 代码高亮
- [x] 流式消息显示 + 思考中动画
- [x] CLI 工具（白名单/黑名单安全控制）

## 启动步骤

### 1. 启动后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env 填入你的 API Key
python -m app.main
```

后端运行在: http://localhost:7890

### 2. 启动前端 (新终端)

```bash
cd frontend
npm install
npm run dev
```

前端运行在: http://localhost:3000

## 项目结构

```
vx版agent集合体/
├── frontend/          # Electron + React + TypeScript
│   ├── src/
│   │   ├── components/   # UI 组件
│   │   ├── store/        # Zustand 状态管理
│   │   ├── hooks/        # WebSocket Hook
│   │   └── types/        # TypeScript 类型定义
│   └── electron/         # Electron 主进程
├── backend/           # Python + Flask
│   └── app/
│       ├── models.py        # ORM 模型
│       ├── ws_handler.py    # WebSocket 路由
│       ├── llm_client.py    # LLM 客户端
│       ├── context_manager.py # 对话上下文
│       ├── cli_tool.py      # CLI 安全执行
│       └── database.py      # 数据库初始化
└── docs/              # 文档
```
