# vx版Agent集合体

> Windows 桌面应用，微信式 UI，以 AI Agent 为核心的操作系统级平台。

## 项目概述

- **前端**: Electron + React + TypeScript
- **后端**: Python + Flask
- **AI**: OpenAI / Anthropic / 讯飞 / Ollama

## 目录结构

```
vx版agent集合体/
├── frontend/          # 前端 (Electron + React)
├── backend/         # 后端 (Python + Flask)
├── docs/            # 文档
├── scripts/         # 脚本
└── README.md
```

## 文档

完整规格文档见: [docs/AI_Agent_Messenger_OS_SPEC_完整版_v0.5.md](./docs/AI_Agent_Messenger_OS_SPEC_完整版_v0.5.md)

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 开发

```bash
# 后端
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
npm run dev
```

## 版本

v0.5.0
