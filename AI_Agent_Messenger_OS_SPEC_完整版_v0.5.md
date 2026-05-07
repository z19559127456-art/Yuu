# 📱 AI Agent Messenger OS — 完整技术规格说明书

> **版本**：v0.5（完善版）
> **定位**：Windows 桌面应用，微信式 UI，以 AI Agent 为核心对象的操作系统级平台

---

## 目录

1. [项目定位与愿景](#一项目定位与愿景)
2. [核心设计理念](#二核心设计理念)
3. [UI 设计规范](#三ui-设计规范微信风格)
4. [Agent 数据模型](#四agent-数据模型)
5. [Agent 运行机制](#五agent-运行机制)
6. [群聊多 Agent 协作协议](#六群聊多-agent-协作协议)
7. [工具层（Tools Layer）](#七工具层tools-layer)
8. [Skill 插件系统](#八skill-插件系统)
9. [记忆与上下文管理](#九记忆与上下文管理)
10. [安全系统](#十安全系统)
11. [错误处理与重试策略](#十一错误处理与重试策略)
12. [并发控制与资源管理](#十二并发控制与资源管理)
13. [配置管理](#十三配置管理)
14. [消息编辑与引用](#十四消息编辑与引用)
15. [中断与取消机制](#十五中断与取消机制)
16. [导入导出系统](#十六导入导出系统)
17. [UI/UX 增强](#十七uiux-增强)
18. [多语言支持](#十八多语言支持)
19. [测试与运维](#十九测试与运维)
20. [系统架构](#二十系统架构)
21. [技术栈与依赖](#二十一技术栈与依赖)
22. [数据存储设计](#二十二数据存储设计)
23. [开发路线图](#二十三开发路线图)

---

## 一、项目定位与愿景

### 1.1 一句话定义

> **AI Agent Messenger OS = 微信交互范式 × AI 操作系统 × 多 Agent 协作平台**

### 1.2 核心目标

| 维度 | 目标描述 |
|------|----------|
| 交互体验 | 像用微信一样使用 AI，零学习成本 |
| Agent 管理 | 像加好友一样创建、配置、删除 Agent |
| 任务执行 | 自然语言 → 自动拆解 → 工具执行 → 结果返回 |
| 多 Agent 协作 | 像群聊一样让多个 Agent 并行协作完成复杂任务 |
| 自动化能力 | 可操作电脑 CLI / UI / Web / 视觉识别 |
| 可扩展性 | Skill 插件热加载，Agent 行为完全可定制 |
| 可靠性 | 完善的错误处理、重试、降级机制 |
| 安全性 | 细粒度权限控制、审计日志、隐私保护 |

### 1.3 目标用户

- 开发者（自动化编码、测试、部署流水线）
- 产品/运营（数据收集、内容生成、报告撰写）
- 研究者（文献检索、信息整合、分析报告）
- 普通用户（电脑自动化、日程管理、文件处理）

---

## 二、核心设计理念

### 2.1 Agent = 微信"好友"的替代物

每个 Agent 是一个有独立身份、角色、工具集和记忆的 AI 实体，对用户而言行为上等价于一个"智能联系人"。

**设计原则：**
- 每个 Agent 独立存在，不互相共享上下文（除非在群聊中）
- Agent 可以有个性、语气风格、专属工具
- Agent 的对话历史持久化，具备跨会话记忆

### 2.2 Chat = 任务执行接口

```
用户自然语言输入
    ↓
意图理解 (Intent Parser)
    ↓
任务规划 (Planner)
    ↓
工具调用 (Tool Executor)
    ↓
结果处理 + 格式化输出
    ↓
用户看到结构化回复
```

### 2.3 Group Chat = 多 Agent 并行协作系统

群聊不是多个 Agent 轮流回答，而是任务拆解后的**并行执行框架**：

- 任务自动分配给最合适的 Agent
- Agent 间结果可互相引用
- 有 Critic 角色负责汇总和质量把关

### 2.4 Agent 完全可设计

用户可以在 UI 中：
- 创建新 Agent（填表单，类似新建联系人）
- 修改现有 Agent 的角色描述、人格、工具集、LLM 模型
- 导入/导出 Agent 配置（JSON 格式）
- 从模板库快速创建 Agent

---

## 三、UI 设计规范（微信风格）

### 3.1 整体布局

```
┌────────────────────────────────────────────────────────────┐
│  标题栏：AI Agent Messenger OS          [─] [□] [×]       │
├──────┬──────────────────┬───────────────────────────────────┤
│      │                  │                                   │
│  导  │   Agent 列表      │         聊天主区域                │
│  航  │                  │                                   │
│  栏  │  🔍 搜索框        │  ┌──────────────────────────┐    │
│      │  ──────────────  │  │  Agent 头像 + 名称 + 状态 │    │
│  💬  │  [头像] CodeAgent │  └──────────────────────────┘    │
│  👥  │  [头像] 群组-01   │                                   │
│  🔧  │  [头像] DataAgent │  消息气泡区（可滚动）             │
│  📊  │  [头像] WebAgent  │                                   │
│  ⚙️  │                  │  ┌──────────────────────────┐    │
│      │  + 新建 Agent     │  │ 📎 🌐 ⚡  输入框  [发送] │    │
│      │                  │  └──────────────────────────┘    │
└──────┴──────────────────┴───────────────────────────────────┘
```

### 3.2 导航栏图标（左侧竖栏）

| 图标 | 功能 | 快捷键 |
|------|------|--------|
| 💬 | 聊天列表（默认视图） | Ctrl+1 |
| 👥 | Agent 通讯录 | Ctrl+2 |
| 🔧 | Skill 管理中心 | Ctrl+3 |
| 📊 | 任务执行历史 | Ctrl+4 |
| ⚙️ | 系统设置 | Ctrl+, |

### 3.3 消息气泡规范

| 消息类型 | 样式说明 | 操作 |
|----------|----------|------|
| 用户消息 | 右对齐，绿色气泡 | 编辑、撤回、复制、引用、"记住这条" |
| Agent 文本回复 | 左对齐，白色气泡 | 复制、引用、重新生成 |
| 工具执行状态 | 灰色卡片，带进度条 | 取消（执行中）、重试（失败后） |
| 代码块 | 深色背景，语法高亮，一键复制按钮 | 复制、保存到文件 |
| 错误信息 | 红色边框卡片，含重试按钮 | 重试、查看详情 |
| 任务完成通知 | 绿色 ✅ 标识 + 摘要 | 查看详情 |
| 文件/截图结果 | 内嵌预览缩略图，点击放大 | 打开、另存为、复制 |
| 系统通知 | 灰色居中横幅 | 关闭 |

### 3.4 Agent 创建面板（类"添加好友"）

```
┌──────────────────────────────────┐
│  新建 Agent                  ×   │
├──────────────────────────────────┤
│  头像：[自动生成] [上传]         │
│  名称：___________________________│
│  角色描述：______________________│
│  人格风格：[严谨] [活泼] [简洁]  │
│  LLM 模型：[下拉选择]            │
│  工具授权：☑CLI ☑Web ☐UI ☐Vision│
│    CLI 目录白名单：[+ 添加]      │
│    Web 域名白名单：[+ 添加]      │
│  记忆模式：● 持久化  ○ 会话级    │
│  Skills：[+ 添加技能]            │
│                 [取消] [创建]    │
└──────────────────────────────────┘
```

### 3.5 加载状态设计

```
Agent 思考中动画：
  [Agent 头像] ◌ 正在思考...
  （三个点循环跳动动画）

工具执行分步指示：
  ┌─────────────────────────┐
  │ ⏳ 正在执行：读取文件    │ 1/5
  │    [████████░░░░]  60%  │
  │ 📎 main.py               │
  └─────────────────────────┘
  （点击可展开查看详细日志）
  [取消]
```

### 3.6 通知系统

| 通知类型 | 触发场景 | 展示方式 |
|----------|----------|----------|
| 任务完成 | 后台长时间任务执行完毕 | 系统托盘通知 + 应用内横幅 |
| 错误警报 | 关键错误发生 | 弹窗 + 日志记录 |
| 安全提醒 | 敏感操作需要确认 | 模态对话框 |
| 更新提示 | 新版本可用 | 应用内横幅 |

---

## 四、Agent 数据模型

### 4.1 Agent Schema（完整版）

```json
{
  "agent_id": "uuid-v4",
  "name": "CodeAgent",
  "avatar": "base64_or_url",
  "role": "程序开发助手",
  "system_prompt": "你是一名经验丰富的全栈开发工程师，擅长 Python、JavaScript 和系统架构设计...",
  "personality": {
    "style": "严谨",
    "tone": "专业",
    "verbosity": "concise"
  },
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.3,
    "max_tokens": 4096,
    "api_key_ref": "env:OPENAI_API_KEY",
    "retry_config": {
      "max_retries": 3,
      "initial_delay_ms": 1000,
      "max_delay_ms": 10000,
      "exponential_backoff": true,
      "retry_on": ["rate_limit", "network", "timeout"]
    }
  },
  "tools": {
    "cli": {
      "enabled": true,
      "allowed_commands": ["python", "git", "pip"],
      "blocked_commands": ["rm -rf", "format"],
      "allowed_directories": ["C:\\Users\\%USERNAME%\\Documents", "D:\\Projects"],
      "blocked_directories": ["C:\\Windows", "C:\\Program Files"]
    },
    "web": {
      "enabled": true,
      "max_pages": 10,
      "allowed_domains": ["github.com", "stackoverflow.com"],
      "blocked_domains": ["malicious.com"]
    },
    "ui_automation": { "enabled": false },
    "vision": { "enabled": true }
  },
  "memory": {
    "mode": "persistent",
    "backend": "sqlite",
    "max_history_turns": 100,
    "summary_threshold": 50
  },
  "skills": ["code_review", "debug", "refactor", "test_generation"],
  "concurrency": {
    "max_parallel_tasks": 3,
    "queue_strategy": "fifo"
  },
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "tags": ["dev", "python"],
  "is_active": true
}
```

### 4.2 Agent 状态机

```
[空闲 Idle]
    ↓ 收到消息
[规划中 Planning]
    ↓ 拆解完成
[执行中 Running]
    ↓ 工具调用中
[等待工具 Waiting]
    ↓ 工具返回
[生成回复 Generating]
    ↓ 输出完成
[空闲 Idle]

异常分支：
    执行中 → [错误 Error] → 重试 or 放弃
    执行中 → [已取消 Cancelled] → 清理 → 空闲
```

### 4.3 消息 Schema

```json
{
  "msg_id": "uuid-v4",
  "conversation_id": "uuid-v4",
  "agent_id": "uuid-v4|null",
  "role": "user|assistant|system|tool",
  "type": "text|tool_call|tool_result|error|system_notice",
  "content": "string",
  "content_html": "string|null",
  "attachments": [
    {
      "type": "file|image|code",
      "name": "string",
      "data": "string|bytes|null",
      "path": "string|null"
    }
  ],
  "tool_calls": [
    {
      "id": "string",
      "name": "string",
      "arguments": "object"
    }
  ],
  "tool_results": [
    {
      "tool_call_id": "string",
      "result": "any",
      "status": "success|error"
    }
  ],
  "reply_to": "uuid-v4|null",
  "is_edited": false,
  "edited_from": "uuid-v4|null",
  "is_pinned": false,
  "is_remembered": false,
  "status": "sending|sent|failed|cancelled",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

---

## 五、Agent 运行机制

### 5.1 三角架构：Planner / Worker / Critic

每个 Agent 内部运行时由三个逻辑角色构成（可由同一 LLM 实例扮演不同 prompt 角色）：

#### Planner（规划者）
**职责：** 理解用户意图，将复杂任务拆解为子任务列表

```python
# Planner Prompt 模板
PLANNER_PROMPT = """
你是任务规划专家。
用户请求：{user_input}
可用工具：{available_tools}
可用技能：{available_skills}

请将任务拆解为有序的子任务列表，每个子任务包含：
- task_id
- description（任务描述）
- tool（所需工具，可为 null）
- depends_on（依赖的前置 task_id 列表）
- estimated_output（预期输出类型）
- can_be_cancelled（是否可取消）

输出格式：JSON
"""
```

#### Worker（执行者）
**职责：** 按照 Planner 的计划，顺序/并行执行任务

```python
# Worker 执行循环伪代码
async def worker_loop(task_plan: List[Task], cancel_token: CancelToken) -> TaskResults:
    results = {}
    for task in topological_sort(task_plan):
        if cancel_token.is_cancelled:
            raise TaskCancelledError()

        context = {dep: results[dep] for dep in task.depends_on}
        try:
            result = await execute_task_with_retry(
                task,
                context,
                cancel_token=cancel_token
            )
            results[task.task_id] = result
        except Exception as e:
            if task.can_retry:
                await retry_task(task)
            else:
                raise
    return results

async def execute_task_with_retry(task, context, cancel_token, max_retries=3):
    retry_count = 0
    while retry_count < max_retries:
        try:
            return await execute_task(task, context, cancel_token)
        except RetryableError as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise
            wait_time = calculate_backoff(retry_count)
            await asyncio.sleep(wait_time)
```

#### Critic（批评者）
**职责：** 检查 Worker 的输出质量，决定是否需要修正或重试

```python
# Critic 判断逻辑
CRITIC_PROMPT = """
原始任务：{original_request}
执行结果：{worker_output}

请判断：
1. 任务是否完成？(yes/no/partial)
2. 输出质量是否满足要求？
3. 如果不满足，给出具体的修正建议

输出格式：JSON {{"status": "...", "score": 0-10, "feedback": "..."}}
"""
```

### 5.2 单次对话完整流程

```
用户输入 "帮我重构这段 Python 代码，并运行测试"
    │
    ▼
[Intent Parser] 识别意图：代码重构 + 测试执行
    │
    ▼
[Planner] 拆解子任务：
    task_1: 读取代码内容（无工具依赖）
    task_2: 分析代码结构（depends_on: task_1）
    task_3: 生成重构版本（depends_on: task_2）
    task_4: 执行 pytest（tool: CLI, depends_on: task_3）
    task_5: 汇总测试结果（depends_on: task_4）
    │
    ▼
[Worker] 顺序/并行执行各子任务
    │
    ▼
[Critic] 检查测试是否全部通过
    ├── 通过 → 格式化输出返回用户
    ├── 失败 → 将错误信息反馈给 Worker，触发修复循环（最多3次）
    │
    ▼
用户看到：重构后代码 + 测试结果摘要
```

---

## 六、群聊多 Agent 协作协议

### 6.1 群聊对象模型

群聊支持两种模式，通过 `chat_mode` 字段切换：

| 模式 | 值 | 说明 |
|------|----|------|
| 任务模式 | `task` | Coordinator 中心化分发任务，Agent 各自执行后汇总（原有模式） |
| 讨论模式 | `discussion` | Agent 之间自由发言、互相回应，适合需要协商的场景 |

```json
{
  "group_id": "uuid-v4",
  "name": "全栈开发小组",
  "chat_mode": "task",
  "members": [
    { "agent_id": "...", "role": "coordinator" },
    { "agent_id": "...", "role": "worker" },
    { "agent_id": "...", "role": "worker" },
    { "agent_id": "...", "role": "critic" }
  ],
  "task_routing_strategy": "auto",
  "speaking_order": "round_robin|priority|free",
  "discussion_config": {
    "max_rounds": 10,
    "pass_threshold": 0.6,
    "termination_condition": "consensus"
  },
  "created_at": "..."
}
```

`discussion_config` 字段仅在 `chat_mode: discussion` 时生效：
- `max_rounds`：最大发言轮次上限，触发后强制结束
- `pass_threshold`：Agent 选择 `<pass>` 的比例达到该阈值时，判定讨论收敛
- `termination_condition`：终止条件，见 6.5 节

### 6.2 群聊任务执行流程

```
用户 → 群聊输入："做一个爬虫，抓取豆瓣 Top250 电影，保存到 Excel"
    │
    ▼
[Coordinator Agent] 接收任务，分配给各 Worker：
    - WebAgent：负责爬取豆瓣页面
    - DataAgent：负责数据清洗 + Excel 生成
    - CodeAgent：负责编写/调试爬虫脚本
    │
    ▼
[并行执行阶段]
    WebAgent ──→ 获取页面 HTML
    CodeAgent ──→ 生成 BeautifulSoup 解析脚本
    │
    ▼（WebAgent 和 CodeAgent 结果汇合）
    DataAgent ──→ 执行脚本 + 清洗数据 + 写入 Excel
    │
    ▼
[Critic Agent] 检查 Excel 文件完整性（250 条记录？字段是否完整？）
    │
    ▼
[Coordinator] 汇总结果，发送给用户
```

### 6.3 Agent 间通信消息格式

```json
{
  "msg_id": "uuid",
  "from_agent": "coordinator-001",
  "to_agent": "web-agent-001|all",
  "type": "task_assign|task_result|task_error|request_help|status_update|context_share|pass|consensus|role_switch_request",
  "payload": {
    "task_id": "task_1",
    "description": "抓取豆瓣电影 Top250 全部页面 HTML",
    "priority": "high",
    "deadline_ms": 30000
  },
  "timestamp": "2025-01-01T00:00:00Z"
}
```

消息类型枚举：
- `task_assign` — 分配任务
- `task_result` — 返回结果
- `task_error` — 报告失败
- `request_help` — 请求其他 Agent 协助
- `status_update` — 中间进度汇报
- `context_share` — 共享上下文片段
- `pass` — 本轮无新内容，跳过发言（讨论模式专用）
- `consensus` — 声明已达成共识（讨论模式专用）
- `role_switch_request` — 请求切换角色（如 Coordinator 移交）

### 6.4 任务依赖图可视化

```
任务 DAG 可视化展示：

  ┌──────────┐
  │ Task 1   │ 读取文件
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │ Task 2   │ 分析代码
  └────┬─────┘
       │
  ┌────┴─────┐
  ▼          ▼
┌──────┐  ┌──────┐
│Task 3│  │Task 4│ 并行执行
└──┬───┘  └──┬───┘
   │         │
   └────┬────┘
        ▼
   ┌────────┐
   │ Task 5 │ 汇总
   └────────┘

（鼠标悬停显示任务详情，点击跳转对应消息）
```

### 6.5 角色动态切换机制

```python
# 角色切换请求处理
async def handle_role_switch(request: RoleSwitchRequest):
    """
    允许 Agent 中途移交 Coordinator 角色
    """
    # 1. 验证请求合法性
    if request.from_role != "coordinator":
        return {"success": False, "reason": "只有 Coordinator 可以移交角色"}

    # 2. 征得用户确认（如果是敏感操作）
    if not await user_confirm(f"{request.from_agent} 请求将 Coordinator 移交給 {request.to_agent}"):
        return {"success": False, "reason": "用户拒绝"}

    # 3. 执行切换
    group = get_group(request.group_id)
    group.members = [
        {**m, "role": "coordinator" if m.agent_id == request.to_agent else m.role}
        for m in group.members
    ]

    # 4. 广播通知
    await broadcast(group.group_id, {
        "type": "role_switched",
        "from": request.from_agent,
        "to": request.to_agent
    })

    return {"success": True}
```

---

### 6.6 讨论模式：Agent 互相对话

讨论模式下，群聊引入**共享消息总线（GroupChatBus）**，所有 Agent 订阅同一消息流，可自由发言和回应彼此。

#### 消息总线实现

```python
# group/discussion_bus.py
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class GroupMessage:
    msg_id: str
    from_agent: str          # agent_id，"user" 表示用户发言
    content: str
    timestamp: str
    msg_type: str = "speak"  # "speak" | "pass" | "consensus"

class GroupChatBus:
    def __init__(self, group_config: dict):
        self.group_id = group_config["group_id"]
        self.cfg = group_config["discussion_config"]
        self.messages: List[GroupMessage] = []
        self.agents: Dict[str, AgentInstance] = {}
        self.round_count = 0
        self.speaking_order = group_config.get("speaking_order", "free")
        self._lock = asyncio.Lock()

    async def broadcast(self, from_agent: str, content: str, msg_type: str = "speak"):
        """发布一条消息到总线，所有其他 Agent 都会收到"""
        async with self._lock:
            msg = GroupMessage(
                msg_id=new_uuid(),
                from_agent=from_agent,
                content=content,
                timestamp=now_iso(),
                msg_type=msg_type
            )
            self.messages.append(msg)
            # 推送给前端实时显示
            await push_to_ui(self.group_id, msg)

    async def run_discussion(self, user_input: str) -> str:
        """讨论模式主循环"""
        # 1. 用户输入作为第一条消息
        await self.broadcast("user", user_input)

        while self.round_count < self.cfg["max_rounds"]:
            self.round_count += 1
            round_responses = []

            # 2. 按发言顺序让 Agent 决策
            if self.speaking_order == "round_robin":
                for agent_id in self.agents.keys():
                    response = await self._agent_turn(agent_id, self.agents[agent_id])
                    round_responses.append((agent_id, response))
            elif self.speaking_order == "priority":
                sorted_agents = sorted(self.agents.items(), key=lambda a: a[1].priority)
                for agent_id, agent in sorted_agents:
                    response = await self._agent_turn(agent_id, agent)
                    round_responses.append((agent_id, response))
            else:  # free
                tasks = [
                    self._agent_turn(agent_id, agent)
                    for agent_id, agent in self.agents.items()
                ]
                round_responses = await asyncio.gather(*tasks)

            # 3. 按顺序广播本轮发言（非 pass）
            spoke_count = 0
            for agent_id, response in round_responses:
                if response.msg_type != "pass":
                    await self.broadcast(agent_id, response.content, response.msg_type)
                    spoke_count += 1

            # 4. 检查终止条件
            if await self._should_terminate(round_responses, spoke_count):
                break

        # 5. 触发 Critic 汇总
        return await self._summarize()

    async def _agent_turn(self, agent_id: str, agent) -> tuple:
        """单个 Agent 的一轮决策"""
        history_text = self._format_history_for_agent(agent_id)
        response = await agent.llm.complete([
            {"role": "system", "content": self._build_discussion_prompt(agent)},
            {"role": "user",   "content": history_text}
        ])
        return (agent_id, response)

    def _build_discussion_prompt(self, agent) -> str:
        return f"""
{agent.system_prompt}

你现在参与一场多 Agent 群聊讨论。
规则：
1. 仔细阅读群聊历史，只有当你有实质性新内容时才发言
2. 如果你认为自己无新内容补充，回复 <pass>
3. 如果你认为讨论已经充分、可以得出结论，回复 <consensus>：结论内容
4. 发言要简洁，避免重复别人已说过的内容

输出格式（严格遵守）：
- 正常发言：直接输出内容
- 跳过：<pass>
- 宣布共识：<consensus>：[结论]
"""

    def _format_history_for_agent(self, agent_id: str) -> str:
        lines = ["=== 群聊历史 ==="]
        for msg in self.messages:
            speaker = "用户" if msg.from_agent == "user" else f"[{msg.from_agent}]"
            lines.append(f"{speaker}: {msg.content}")
        lines.append(f"""
现在轮到你（{agent_id}）发言：""")
        return "\n".join(lines)
```

#### 发言轮次示意

```
用户："我们要选 React 还是 Vue 来做这个项目的前端？"
    │
    ▼
Round 1：
  FrontendAgent："推荐 React，生态更成熟，适合复杂项目"
  BackendAgent："<pass>"
  ArchAgent："同意考虑 React，但要看团队熟悉度"
    │
    ▼
Round 2：
  FrontendAgent："<pass>"
  BackendAgent："从后端 API 角度两者没区别，看前端同学决定"
  ArchAgent："<consensus>：选 React，理由是生态成熟 + 团队熟悉度高"
    │
    ▼
[终止：consensus 检测到] → Critic 汇总 → 返回用户
```

---

### 6.7 防死循环机制

讨论模式内置三层防护，任意一层触发即终止当前轮次：

#### 机制一：发言轮次硬限制

```python
# 在 run_discussion 主循环中
while self.round_count < self.cfg["max_rounds"]:   # 默认 max_rounds=10
    self.round_count += 1
    ...

# 超出轮次后强制进入汇总
if self.round_count >= self.cfg["max_rounds"]:
    await self.broadcast("system", f"⚠️ 已达最大讨论轮次（{self.cfg['max_rounds']}），自动汇总结论")
```

触发条件：连续讨论超过 `max_rounds` 轮（默认 10 轮）无论是否收敛，强制结束。适合防止低效的无限来回。

#### 机制二：Agent 自主 Pass

每个 Agent 在 Prompt 中被明确要求自我判断：无新内容时回复 `<pass>` 而非强行发言。总线统计每轮 pass 比例：

```python
async def _should_terminate(self, round_responses: list, spoke_count: int) -> bool:
    total = len(round_responses)
    pass_count = sum(1 for _, r in round_responses if r.msg_type == "pass")
    pass_ratio = pass_count / total

    # 机制二：pass 比例超过阈值（默认 60%），说明大多数 Agent 认为没新内容了
    if pass_ratio >= self.cfg["pass_threshold"]:   # 默认 0.6
        await self.broadcast("system", f"💬 {pass_count}/{total} 个 Agent 无新内容，讨论自然收敛")
        return True

    # 机制一：轮次硬限制（在主循环 while 条件中检查）
    return False
```

#### 机制三：Critic 收敛检测

Critic Agent 在每轮结束后自动评估讨论质量，若检测到收敛信号则主动介入终止：

```python
# 收敛检测触发条件（满足任一即触发）：
CONSENSUS_SIGNALS = [
    "any agent sent <consensus>",          # 有 Agent 主动宣布共识
    "pass_ratio >= pass_threshold",        # 大多数 Agent pass（机制二）
    "round_count >= max_rounds",           # 达到轮次上限（机制一）
    "no_new_info_detected_by_critic",      # Critic 判断信息不再增长
]

CRITIC_CONVERGENCE_PROMPT = """
请分析以下群聊历史，判断讨论是否已经收敛：
{history}

判断标准：
- 新轮次的发言是否在重复上一轮的内容？
- 是否出现了明确的结论或共识？
- 是否已经充分覆盖了原始问题？

输出 JSON：{{"converged": true/false, "reason": "...", "conclusion": "..."}}
"""

async def _critic_check(self) -> bool:
    if len(self.messages) < 4:   # 消息太少，不检测
        return False
    result = await self.critic_agent.llm.complete([
        {"role": "user", "content": CRITIC_CONVERGENCE_PROMPT.format(
            history=self._format_history_for_agent("critic")
        )}
    ])
    return result.converged
```

#### 三层机制触发优先级

```
Round N 结束
    ↓
检查：有 Agent 发出 <consensus>？          → 是 → 立即终止
    ↓ 否
检查：pass_ratio >= pass_threshold？       → 是 → 收敛终止
    ↓ 否
检查：round_count >= max_rounds？          → 是 → 强制终止
    ↓ 否
检查：Critic 判断收敛？                    → 是 → 智能终止
    ↓ 否
继续下一轮
```

---

### 6.8 讨论模式 vs 任务模式 选择建议

| 场景 | 推荐模式 | 原因 |
|------|----------|------|
| 明确可拆解的执行任务（爬虫、写代码） | `task` | 中心化调度效率高，token 消耗少 |
| 方案选型、技术评审 | `discussion` | 需要多角度碰撞 |
| 头脑风暴、创意生成 | `discussion` | 发散性讨论更有价值 |
| 文档撰写、数据处理 | `task` | 结构清晰，无需协商 |
| 有争议的决策 | `discussion` | 让不同立场 Agent 充分博弈 |

---

## 七、工具层（Tools Layer）

### 7.1 CLI 工具

**功能：** 在本机终端执行命令，支持流式输出

```python
class CLITool:
    allowed_commands: List[str]       # 白名单
    blocked_patterns: List[str]       # 黑名单正则
    allowed_directories: List[str]    # 目录白名单
    blocked_directories: List[str]    # 目录黑名单
    working_directory: str
    timeout_seconds: int = 30
    sandbox_mode: bool = True         # 沙盒模式下使用受限 shell

    async def execute(
        self,
        command: str,
        cancel_token: CancelToken = None
    ) -> ToolResult:
        # 1. 安全检查
        safety_result = self._check_safety(command)
        if not safety_result.allowed:
            return ToolResult(
                success=False,
                output=None,
                output_type="error",
                stderr=f"命令被禁止：{safety_result.reason}"
            )

        # 2. 沙盒包装（Windows: 受限用户令牌）
        wrapped_cmd = self._wrap_in_sandbox(command)

        # 3. subprocess 异步执行
        process = await asyncio.create_subprocess_shell(
            wrapped_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_directory
        )

        # 4. 实时流式回传 stdout/stderr
        stdout_chunks = []
        stderr_chunks = []

        async def read_stream(stream, chunks, callback):
            while True:
                chunk = await stream.read(1024)
                if not chunk:
                    break
                chunks.append(chunk)
                if callback:
                    callback(chunk.decode('utf-8', errors='replace'))

        async def cancel_monitor():
            if cancel_token:
                await cancel_token.wait()
                try:
                    process.terminate()
                    await asyncio.sleep(1)
                    if process.returncode is None:
                        process.kill()
                except:
                    pass

        tasks = [
            read_stream(process.stdout, stdout_chunks, self._on_stdout),
            read_stream(process.stderr, stderr_chunks, self._on_stderr),
        ]
        if cancel_token:
            tasks.append(cancel_monitor())

        await asyncio.gather(*tasks, return_exceptions=True)
        await process.wait()

        return ToolResult(
            success=process.returncode == 0,
            output=b''.join(stdout_chunks).decode('utf-8', errors='replace'),
            output_type="text",
            stderr=b''.join(stderr_chunks).decode('utf-8', errors='replace'),
            execution_time_ms=0
        )

    def _check_safety(self, command: str) -> SafetyResult:
        # 检查命令黑名单
        for pattern in self.blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return SafetyResult(allowed=False, reason=f"匹配危险模式: {pattern}")

        # 检查命令白名单
        cmd_parts = shlex.split(command)
        if cmd_parts and cmd_parts[0] not in self.allowed_commands:
            return SafetyResult(allowed=False, reason=f"命令不在白名单: {cmd_parts[0]}")

        # 检查目录访问
        if self.working_directory:
            in_allowed = any(
                self.working_directory.lower().startswith(d.lower())
                for d in self.allowed_directories
            ) if self.allowed_directories else True

            in_blocked = any(
                self.working_directory.lower().startswith(d.lower())
                for d in self.blocked_directories
            )

            if in_blocked or not in_allowed:
                return SafetyResult(allowed=False, reason=f"目录访问受限: {self.working_directory}")

        return SafetyResult(allowed=True)
```

**安全白名单示例：**
- ✅ `python`, `pip`, `git`, `node`, `npm`, `pytest`, `ls`, `dir`, `cat`, `type`
- ❌ `rm -rf`, `del /f /s`, `format`, `shutdown`, `regedit`, `net user`

### 7.2 Web 自动化工具（Playwright）

```python
class WebTool:
    def __init__(self, allowed_domains=None, blocked_domains=None):
        self.allowed_domains = allowed_domains or []
        self.blocked_domains = blocked_domains or []
        self.browser = None
        self.context = None

    async def _check_domain(self, url: str) -> bool:
        domain = urlparse(url).netloc
        if self.blocked_domains and any(b in domain for b in self.blocked_domains):
            return False
        if self.allowed_domains and not any(a in domain for a in self.allowed_domains):
            return False
        return True

    async def search(self, query: str) -> List[SearchResult]: ...
    async def fetch_page(self, url: str, cancel_token: CancelToken = None) -> PageContent:
        if not await self._check_domain(url):
            raise DomainNotAllowedError(url)
        ...
    async def click(self, selector: str, cancel_token: CancelToken = None): ...
    async def fill_form(self, selector: str, value: str, cancel_token: CancelToken = None): ...
    async def screenshot(self, cancel_token: CancelToken = None) -> bytes: ...
    async def extract_text(self, selector: str = "body") -> str: ...
    async def run_script(self, js: str, cancel_token: CancelToken = None) -> Any: ...

    async def cleanup(self):
        """确保浏览器资源被释放"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
```

**注意：** 默认在无头（headless）模式运行；需要时可切换有头模式并呈现给用户预览。

### 7.3 UI 自动化工具（PyAutoGUI）

```python
class UITool:
    def __init__(self, require_confirmation=True):
        self.require_confirmation = require_confirmation
        self.protected_windows = ["设置", "任务管理器", "注册表编辑器", "PowerShell"]

    async def _check_protected(self) -> bool:
        """检查当前活动窗口是否受保护"""
        active_window = get_active_window_title()
        return any(p in active_window for p in self.protected_windows)

    async def _show_confirmation(self, description: str) -> bool:
        """显示操作预告，等待用户确认"""
        if not self.require_confirmation:
            return True

        # 显示悬浮提示条
        confirmation = await show_confirmation_dialog(
            title="UI 自动化操作确认",
            message=f"即将执行：{description}",
            timeout_seconds=3
        )
        return confirmation

    async def take_screenshot(self, cancel_token: CancelToken = None) -> bytes: ...
    async def find_element_by_image(self, template: bytes) -> Coordinate: ...
    async def click_at(self, x: int, y: int, cancel_token: CancelToken = None):
        if await self._check_protected():
            if not await self._show_confirmation(f"点击 ({x}, {y}) [受保护窗口]"):
                raise UserCancelledError()

        if not await self._show_confirmation(f"点击 ({x}, {y})"):
            raise UserCancelledError()

        # 记录操作日志
        await log_ui_action("click", {"x": x, "y": y})
        ...
    async def type_text(self, text: str, cancel_token: CancelToken = None): ...
    async def hotkey(self, *keys: str, cancel_token: CancelToken = None): ...
    async def drag(self, start: Coordinate, end: Coordinate, cancel_token: CancelToken = None): ...
```

**使用限制：** UI 自动化默认需要用户在设置中显式授权。每次操作前会在界面显示"即将操作：[描述]"，3秒倒计时，用户可点击取消。

### 7.4 视觉识别工具（Vision）

```python
class VisionTool:
    async def analyze_image(self, image: bytes) -> str: ...          # 图像描述
    async def extract_text_from_image(self, image: bytes) -> str: ... # OCR
    async def find_ui_element(self, screenshot: bytes, description: str) -> BoundingBox: ...
    async def read_screen(self) -> str: ...                           # 截屏 + OCR
```

### 7.5 工具返回值统一格式

```python
@dataclass
class ToolResult:
    success: bool
    output: Any                  # 主要输出内容
    output_type: str             # "text" | "bytes" | "json" | "error"
    stderr: Optional[str]        # 错误信息
    execution_time_ms: int
    metadata: Dict[str, Any]     # 工具特定元数据
```

### 7.6 工具实例池

```python
class ToolInstancePool:
    """管理工具实例的复用，避免频繁创建销毁"""

    def __init__(self, max_instances: int = 3):
        self.max_instances = max_instances
        self.pools = {
            "cli": asyncio.Queue(),
            "web": asyncio.Queue(),
        }
        self._locks = {
            "cli": asyncio.Lock(),
            "web": asyncio.Lock(),
        }
        self._counts = {
            "cli": 0,
            "web": 0,
        }

    async def acquire(self, tool_type: str):
        async with self._locks[tool_type]:
            if not self.pools[tool_type].empty():
                return await self.pools[tool_type].get()

            if self._counts[tool_type] < self.max_instances:
                instance = self._create_instance(tool_type)
                self._counts[tool_type] += 1
                return instance

            # 等待释放
            return await self.pools[tool_type].get()

    async def release(self, tool_type: str, instance):
        await self.pools[tool_type].put(instance)

    def _create_instance(self, tool_type: str):
        if tool_type == "cli":
            return CLITool()
        elif tool_type == "web":
            return WebTool()
        raise ValueError(f"Unknown tool type: {tool_type}")
```

---

## 八、Skill 插件系统

### 8.1 Skill 定义规范

每个 Skill 是一个独立 Python 文件，放置于 `skills/` 目录，自动被系统发现和加载：

```python
# skills/web_summary.py

SKILL_META = {
    "name": "web_summary",
    "display_name": "网页摘要",
    "description": "获取指定 URL 的网页内容并生成摘要",
    "version": "1.0.0",
    "author": "system",
    "required_tools": ["web"],
    "input_schema": {
        "url": {"type": "string", "description": "目标网页 URL"},
        "max_length": {"type": "integer", "default": 500}
    },
    "output_schema": {
        "summary": {"type": "string"},
        "title": {"type": "string"},
        "key_points": {"type": "array"}
    }
}

async def run(
    input: dict,
    tools: ToolRegistry,
    llm: LLMClient,
    cancel_token: CancelToken = None
) -> dict:
    url = input["url"]
    max_length = input.get("max_length", 500)

    # 1. 用 WebTool 抓取页面
    page = await tools.web.fetch_page(url, cancel_token=cancel_token)

    # 2. 用 LLM 生成摘要
    summary = await llm.complete(
        f"请对以下内容生成不超过 {max_length} 字的摘要：\n{page.text}"
    )

    return {
        "summary": summary,
        "title": page.title,
        "key_points": []  # 可进一步实现
    }
```

### 8.2 Skill 加载器

```python
class SkillLoader:
    skills_dir: str = "./skills"
    loaded_skills: Dict[str, SkillModule] = {}
    _watchdog_observer = None

    def discover(self):
        """扫描 skills/ 目录，热加载所有合法 Skill"""
        for file in Path(self.skills_dir).glob("*.py"):
            self.load(file)

        # 启动文件监控，自动热加载
        self._start_watchdog()

    def load(self, path: Path):
        """动态 import，验证 SKILL_META 和 run() 签名"""
        ...

    def reload(self, skill_name: str):
        """热重载单个 Skill（无需重启应用）"""
        ...

    def unload(self, skill_name: str):
        """卸载 Skill"""
        if skill_name in self.loaded_skills:
            del self.loaded_skills[skill_name]

    def _start_watchdog(self):
        """启动文件监控"""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class SkillFileHandler(FileSystemEventHandler):
            def __init__(self, loader):
                self.loader = loader

            def on_modified(self, event):
                if event.src_path.endswith('.py'):
                    skill_name = Path(event.src_path).stem
                    self.loader.reload(skill_name)

            def on_created(self, event):
                if event.src_path.endswith('.py'):
                    self.loader.load(Path(event.src_path))

            def on_deleted(self, event):
                if event.src_path.endswith('.py'):
                    skill_name = Path(event.src_path).stem
                    self.loader.unload(skill_name)

        self._watchdog_observer = Observer()
        self._watchdog_observer.schedule(
            SkillFileHandler(self),
            self.skills_dir,
            recursive=False
        )
        self._watchdog_observer.start()
```

### 8.3 Skill 调用方式

Agent 可通过两种方式使用 Skill：

1. **LLM 自主调用**：Skill 列表以 Function Calling 格式注入 LLM，由模型自主决定何时调用
2. **用户显式调用**：在输入框输入 `/skill web_summary url=https://...`

### 8.4 内置 Skill 列表（计划）

| Skill 名称 | 功能描述 |
|------------|----------|
| `code_review` | 代码审查，输出建议列表 |
| `web_summary` | 网页摘要提取 |
| `file_reader` | 读取并理解本地文件（txt/pdf/docx/xlsx） |
| `excel_writer` | 生成 Excel 文件 |
| `image_analyzer` | 分析图片内容 |
| `git_helper` | 封装常用 git 操作 |
| `scheduler` | 定时任务注册 |
| `email_draft` | 生成邮件草稿 |

---

## 九、记忆与上下文管理

### 9.1 记忆分层架构

```
┌─────────────────────────────────────────────────────────┐
│  L1：会话缓存（In-Memory）                                │
│  当前对话的完整历史，直接注入 Prompt                       │
├─────────────────────────────────────────────────────────┤
│  L2：摘要记忆（SQLite）                                   │
│  超过阈值的历史自动压缩为摘要                              │
├─────────────────────────────────────────────────────────┤
│  L3：长期知识库（向量数据库）                              │
│  Agent 从过往对话中提炼的知识片段                          │
└─────────────────────────────────────────────────────────┘
```

### 9.2 记忆写入策略

- **会话结束时**：自动将本次对话压缩为摘要，写入 L2
- **重要信息提取**：LLM 自动识别对话中的重要事实（用户偏好、项目信息），写入 L3
- **手动标记**：用户可右键消息 → "记住这条"，强制写入 L3

### 9.3 Prompt 构建顺序

```
[系统 Prompt：角色 + 人格 + 工具描述]
[L3 长期记忆：相关知识片段 Top-K]
[L2 摘要记忆：历史摘要]
[L1 会话缓存：近 N 轮对话]
[当前用户输入]
```

### 9.4 记忆管理器实现

```python
class MemoryManager:
    def __init__(self, agent_id: str, db_path: str, vector_store_path: str):
        self.agent_id = agent_id
        self.db = SQLiteDB(db_path)
        self.vector_store = ChromaDB(vector_store_path)
        self.l1_cache = []  # 会话缓存
        self.summary_threshold = 50

    async def add_message(self, role: str, content: str, metadata: dict = None):
        """添加消息到记忆"""
        # 1. 添加到 L1 缓存
        self.l1_cache.append({"role": role, "content": content})

        # 2. 持久化到数据库
        await self.db.insert_message(
            agent_id=self.agent_id,
            role=role,
            content=content,
            metadata=metadata or {}
        )

        # 3. 检查是否需要摘要压缩
        if len(self.l1_cache) > self.summary_threshold:
            await self._compress_to_l2()

        # 4. 自动提取重要信息到 L3
        if role == "assistant" or metadata.get("is_remembered"):
            await self._extract_to_l3(role, content)

    async def _compress_to_l2(self):
        """将 L1 缓存压缩为摘要，存入 L2"""
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in self.l1_cache])

        # 使用 LLM 生成摘要
        summary = await self._llm_complete(f"请为以下对话生成简洁摘要：\n{history_text}")

        # 存入 L2
        await self.db.insert_summary(
            agent_id=self.agent_id,
            summary=summary,
            message_count=len(self.l1_cache)
        )

        # 清空 L1，保留最后几条
        self.l1_cache = self.l1_cache[-10:]

    async def _extract_to_l3(self, role: str, content: str):
        """提取重要信息到 L3 向量库"""
        extraction_prompt = """
        请从以下内容中提取可能对未来有帮助的重要事实、偏好、知识点。
        每行一条事实，用简洁的语言。如果没有重要信息，返回空列表。

        内容：
        {content}
        """

        result = await self._llm_complete(extraction_prompt.format(content=content))
        facts = [line.strip() for line in result.split('\n') if line.strip()]

        for fact in facts:
            await self.vector_store.add(
                agent_id=self.agent_id,
                text=fact,
                metadata={"source": "auto_extract", "role": role}
            )

    async def retrieve_relevant(self, query: str, top_k: int = 5) -> List[str]:
        """从 L3 检索相关记忆"""
        return await self.vector_store.search(
            agent_id=self.agent_id,
            query=query,
            top_k=top_k
        )

    def build_prompt_context(self, current_query: str) -> List[dict]:
        """构建完整的 Prompt 上下文"""
        context = []

        # L3: 相关长期记忆
        relevant_memories = self.vector_store.search_sync(
            self.agent_id, current_query, top_k=3
        )
        if relevant_memories:
            context.append({
                "role": "system",
                "content": "相关记忆：\n" + "\n".join(relevant_memories)
            })

        # L2: 历史摘要
        summaries = self.db.get_summaries(self.agent_id, limit=3)
        if summaries:
            context.append({
                "role": "system",
                "content": "历史对话摘要：\n" + "\n".join(summaries)
            })

        # L1: 近期对话
        context.extend(self.l1_cache)

        return context
```

---

## 十、安全系统

### 10.1 命令安全拦截

```python
class CommandSafetyChecker:
    BLOCKED_PATTERNS = [
        r"rm\s+-rf",
        r"del\s+/[fFsS]",
        r"format\s+[A-Za-z]:",
        r"shutdown",
        r":\(\)\s*{\s*:\s*\|\s*:\s*&\s*};\s*:",  # fork bomb
        r"base64.*\|.*bash",
        r"curl.*\|.*sh",
        r"wget.*\|.*sh",
        r"powershell.*-nop.*-c",
        r"Invoke-Expression",
        r"iex\s*\(",
        r"reg\s+add",
        r"reg\s+delete",
        r"net\s+user",
        r"netsh\s+firewall",
        r"sc\s+config",
        r"schtasks",
    ]

    def check(self, command: str, working_dir: str = None) -> SafetyResult:
        # 1. 检查危险模式
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return SafetyResult(
                    blocked=True,
                    reason=f"匹配危险模式: {pattern}",
                    severity="high"
                )

        # 2. 检查工作目录
        if working_dir:
            if self._is_sensitive_directory(working_dir):
                return SafetyResult(
                    blocked=True,
                    reason=f"敏感目录禁止操作: {working_dir}",
                    severity="high"
                )

        return SafetyResult(blocked=False)

    def _is_sensitive_directory(self, path: str) -> bool:
        sensitive_paths = [
            r"C:\\Windows",
            r"C:\\Program Files",
            r"C:\\Program Files (x86)",
            r"%APPDATA%",
            r"%LOCALAPPDATA%",
        ]
        path_lower = path.lower()
        return any(sp.lower() in path_lower for sp in sensitive_paths)
```

### 10.2 UI 操作保护

- **操作预告**：每次 UI 自动化操作前，弹出悬浮提示条（如："即将点击：[开始] 按钮"），3秒倒计时，用户可点击取消
- **敏感区域保护**：系统设置、任务管理器、注册表编辑器等窗口默认受保护，需要二次确认
- **操作日志**：所有 UI 操作记录在本地日志文件

### 10.3 沙盒执行

```python
# Windows 沙盒策略
class SandboxExecutor:
    def execute_sandboxed(self, command: str):
        # 方式1：使用受限用户账户（Windows Restricted Token）
        # 方式2：Windows Job Object 限制资源
        # 方式3：未来支持 Windows Sandbox / WSL2 隔离
        pass

    def create_restricted_token(self):
        """创建受限令牌"""
        import win32security
        import win32api
        import win32con

        # 获取当前进程令牌
        current_token = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(),
            win32security.TOKEN_DUPLICATE | win32security.TOKEN_QUERY
        )

        # 创建受限令牌
        restricted_token = win32security.CreateRestrictedToken(
            current_token,
            win32security.DISABLE_MAX_PRIVILEGE,
            [],
            [],
            []
        )

        return restricted_token
```

### 10.4 数据隐私

- 所有 Agent 配置、对话历史默认存储在本地 `%APPDATA%\AgentMessengerOS\`
- API Key 使用系统密钥链（Windows Credential Manager）加密存储
- 用户可选择禁止任何数据离开本机（本地 LLM 模式）

### 10.5 细粒度权限控制

```python
class PermissionManager:
    def __init__(self):
        self.permissions = {}

    def grant_cli_directory(self, agent_id: str, directory: str):
        """授予 Agent 访问特定目录的权限"""
        if agent_id not in self.permissions:
            self.permissions[agent_id] = {}
        if "cli_directories" not in self.permissions[agent_id]:
            self.permissions[agent_id]["cli_directories"] = []
        self.permissions[agent_id]["cli_directories"].append(directory)

    def grant_web_domain(self, agent_id: str, domain: str):
        """授予 Agent 访问特定域名的权限"""
        if agent_id not in self.permissions:
            self.permissions[agent_id] = {}
        if "web_domains" not in self.permissions[agent_id]:
            self.permissions[agent_id]["web_domains"] = []
        self.permissions[agent_id]["web_domains"].append(domain)

    def can_access_cli_directory(self, agent_id: str, directory: str) -> bool:
        if agent_id not in self.permissions:
            return False
        allowed = self.permissions[agent_id].get("cli_directories", [])
        return any(directory.lower().startswith(a.lower()) for a in allowed)

    def can_access_web_domain(self, agent_id: str, domain: str) -> bool:
        if agent_id not in self.permissions:
            return False
        allowed = self.permissions[agent_id].get("web_domains", [])
        return any(d in domain for d in allowed)
```

### 10.6 审计日志

```python
class AuditLogger:
    def __init__(self, log_path: str):
        self.log_path = log_path
        self._lock = asyncio.Lock()

    async def log(self, event: AuditEvent):
        """记录审计事件"""
        event.timestamp = datetime.utcnow().isoformat()
        event.event_id = new_uuid()

        # 写入日志文件
        async with self._lock:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(dataclasses.asdict(event), ensure_ascii=False) + '\n')

        # 可选：写入系统事件日志
        self._write_to_system_event_log(event)

    def _write_to_system_event_log(self, event: AuditEvent):
        """写入 Windows 事件日志"""
        try:
            import win32evtlog
            # 实现略
        except ImportError:
            pass

@dataclass
class AuditEvent:
    event_id: str = None
    timestamp: str = None
    event_type: str  # "tool_execution" | "permission_request" | "config_change" | "error"
    agent_id: str = None
    user_id: str = None
    action: str
    resource: str = None
    status: str  # "success" | "failed" | "denied"
    details: dict = None
    ip_address: str = None
```

### 10.7 隐私模式

```python
class PrivacyMode:
    def __init__(self):
        self.temp_mode = False
        self.sensitive_patterns = [
            r"(?i)api[_-]?key\s*[=:]\s*['\"]?([a-zA-Z0-9_\-]{16,})",
            r"(?i)password\s*[=:]\s*['\"]?([a-zA-Z0-9_\-]{4,})",
            r"(?i)token\s*[=:]\s*['\"]?([a-zA-Z0-9_\-]{16,})",
            r"(?i)secret\s*[=:]\s*['\"]?([a-zA-Z0-9_\-]{16,})",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # email
            r"\b\d{3}[-.]?\d{4}[-.]?\d{4}\b",  # phone
        ]

    def enter_temp_mode(self):
        """进入临时模式，不保存历史"""
        self.temp_mode = True

    def exit_temp_mode(self):
        """退出临时模式，清理临时数据"""
        self.temp_mode = False
        self._clear_temp_data()

    def redact_sensitive_info(self, text: str) -> str:
        """自动脱敏敏感信息"""
        result = text
        for pattern in self.sensitive_patterns:
            result = re.sub(pattern, "[REDACTED]", result)
        return result

    def _clear_temp_data(self):
        """清理临时会话数据"""
        # 清理内存中的临时会话
        # 清理临时文件
        pass
```

---

## 十一、错误处理与重试策略

### 11.1 错误分类

```python
class ErrorType(Enum):
    # LLM API 错误
    RATE_LIMIT = "rate_limit"          # 限流
    TIMEOUT = "timeout"                # 超时
    NETWORK_ERROR = "network_error"    # 网络错误
    API_ERROR = "api_error"            # API 返回错误
    INVALID_RESPONSE = "invalid_response"  # 响应格式错误

    # 工具错误
    TOOL_FAILED = "tool_failed"        # 工具执行失败
    TOOL_TIMEOUT = "tool_timeout"      # 工具超时
    PERMISSION_DENIED = "permission_denied"  # 权限不足

    # 应用错误
    AGENT_ERROR = "agent_error"        # Agent 内部错误
    STATE_ERROR = "state_error"        # 状态错误

    # 用户操作
    USER_CANCELLED = "user_cancelled"  # 用户取消
```

### 11.2 重试策略配置

```python
@dataclass
class RetryPolicy:
    max_retries: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retry_on: List[ErrorType] = None

    def __post_init__(self):
        if self.retry_on is None:
            self.retry_on = [
                ErrorType.RATE_LIMIT,
                ErrorType.TIMEOUT,
                ErrorType.NETWORK_ERROR,
            ]

# 默认重试策略
DEFAULT_RETRY_POLICY = RetryPolicy()

# 工具执行重试策略
TOOL_RETRY_POLICY = RetryPolicy(
    max_retries=2,
    initial_delay_ms=500,
    retry_on=[ErrorType.TOOL_TIMEOUT, ErrorType.NETWORK_ERROR]
)
```

### 11.3 重试装饰器

```python
def with_retry(policy: RetryPolicy = DEFAULT_RETRY_POLICY):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            cancel_token = kwargs.get('cancel_token')

            for attempt in range(policy.max_retries + 1):
                if cancel_token and cancel_token.is_cancelled:
                    raise UserCancelledError()

                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_type = _classify_error(e)
                    last_exception = e

                    if error_type not in policy.retry_on:
                        raise

                    if attempt >= policy.max_retries:
                        raise RetryFailedError(
                            f"重试 {policy.max_retries} 次后仍然失败"
                        ) from e

                    # 计算等待时间
                    delay = policy.initial_delay_ms * (policy.backoff_multiplier ** attempt)
                    delay = min(delay, policy.max_delay_ms)

                    if policy.jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(f"第 {attempt + 1} 次尝试失败，{delay/1000:.1f}s 后重试: {e}")
                    await asyncio.sleep(delay / 1000)

            raise last_exception
        return wrapper
    return decorator

def _classify_error(e: Exception) -> ErrorType:
    """根据异常类型分类"""
    if isinstance(e, (asyncio.TimeoutError, TimeoutError)):
        return ErrorType.TIMEOUT
    elif isinstance(e, (aiohttp.ClientError, ConnectionError)):
        return ErrorType.NETWORK_ERROR
    elif isinstance(e, PermissionError):
        return ErrorType.PERMISSION_DENIED
    elif isinstance(e, UserCancelledError):
        return ErrorType.USER_CANCELLED
    else:
        return ErrorType.API_ERROR
```

### 11.4 降级策略

```python
class FallbackStrategy:
    def __init__(self):
        self.fallbacks = {}

    def register_fallback(self, error_type: ErrorType, fallback_func):
        """注册降级方案"""
        self.fallbacks[error_type] = fallback_func

    async def execute_with_fallback(self, func, *args, **kwargs):
        """执行并在失败时尝试降级"""
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_type = _classify_error(e)
            if error_type in self.fallbacks:
                logger.warning(f"执行降级策略: {error_type}")
                return await self.fallbacks[error_type](*args, **kwargs)
            raise

# 示例降级策略
async def llm_fallback_simple(*args, **kwargs):
    """LLM 失败时的降级：使用简单规则回复"""
    return {"content": "抱歉，服务暂时不可用，请稍后再试。"}

async def web_fallback_cache(*args, **kwargs):
    """Web 抓取失败时使用缓存"""
    url = kwargs.get('url')
    cache = get_cache()
    if url in cache:
        return cache[url]
    raise
```

### 11.5 Agent 崩溃恢复

```python
class AgentRecoveryManager:
    def __init__(self):
        self.checkpoints = {}
        self.recovery_log = []

    async def save_checkpoint(self, agent_id: str, state: dict):
        """保存检查点"""
        checkpoint_id = new_uuid()
        self.checkpoints[agent_id] = {
            'checkpoint_id': checkpoint_id,
            'state': state,
            'timestamp': datetime.utcnow().isoformat()
        }
        # 持久化到磁盘
        await self._persist_checkpoint(agent_id, self.checkpoints[agent_id])

    async def try_recover(self, agent_id: str) -> dict | None:
        """尝试恢复 Agent 状态"""
        if agent_id not in self.checkpoints:
            return None

        checkpoint = self.checkpoints[agent_id]
        logger.info(f"从检查点恢复 Agent: {agent_id}, 时间: {checkpoint['timestamp']}")

        self.recovery_log.append({
            'agent_id': agent_id,
            'checkpoint_id': checkpoint['checkpoint_id'],
            'recovered_at': datetime.utcnow().isoformat()
        })

        return checkpoint['state']

    async def _persist_checkpoint(self, agent_id: str, checkpoint: dict):
        """持久化检查点"""
        checkpoint_dir = Path(self.data_dir) / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        checkpoint_path = checkpoint_dir / f"{agent_id}.json"
        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f)
```

---

## 十二、并发控制与资源管理

### 12.1 Agent 消息队列

```python
class AgentMessageQueue:
    """单个 Agent 的消息队列"""

    def __init__(self, agent_id: str, strategy: str = "fifo"):
        self.agent_id = agent_id
        self.strategy = strategy  # "fifo" | "priority" | "parallel"
        self.queue = asyncio.Queue()
        self.active_tasks = set()
        self.max_parallel = 3
        self._lock = asyncio.Lock()

    async def enqueue(self, message: Message, priority: int = 0):
        """消息入队"""
        if self.strategy == "priority":
            await self.queue.put((-priority, message))  # 负号使高优先级先出
        else:
            await self.queue.put(message)

    async def process_queue(self, cancel_token: CancelToken = None):
        """处理队列中的消息"""
        while not cancel_token or not cancel_token.is_cancelled:
            # 获取消息
            if self.strategy == "priority":
                priority, message = await self.queue.get()
            else:
                message = await self.queue.get()

            # 根据策略决定如何执行
            if self.strategy == "parallel" and len(self.active_tasks) < self.max_parallel:
                # 并行执行
                task = asyncio.create_task(self._process_single(message))
                self.active_tasks.add(task)
                task.add_done_callback(lambda t: self.active_tasks.discard(t))
            else:
                # 顺序执行
                await self._process_single(message)

    async def _process_single(self, message: Message):
        """处理单条消息"""
        try:
            agent = get_agent(self.agent_id)
            await agent.process_message(message)
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
```

### 12.2 全局并发管理器

```python
class GlobalConcurrencyManager:
    """全局并发控制"""

    def __init__(self):
        self.agent_queues = {}
        self.tool_pool = ToolInstancePool()
        self.semaphores = {
            "llm": asyncio.Semaphore(5),      # 最多 5 个并发 LLM 请求
            "cli": asyncio.Semaphore(3),      # 最多 3 个并发 CLI 执行
            "web": asyncio.Semaphore(2),      # 最多 2 个并发 Web 操作
        }
        self._metrics = {
            "active_llm_requests": 0,
            "active_cli_tasks": 0,
            "active_web_tasks": 0,
        }

    def get_or_create_queue(self, agent_id: str) -> AgentMessageQueue:
        """获取或创建 Agent 的消息队列"""
        if agent_id not in self.agent_queues:
            self.agent_queues[agent_id] = AgentMessageQueue(agent_id)
        return self.agent_queues[agent_id]

    async def acquire_llm_slot(self):
        """获取 LLM 并发槽位"""
        await self.semaphores["llm"].acquire()
        self._metrics["active_llm_requests"] += 1

    def release_llm_slot(self):
        """释放 LLM 并发槽位"""
        self.semaphores["llm"].release()
        self._metrics["active_llm_requests"] -= 1

    async def execute_with_concurrency_control(self, resource_type: str, func, *args, **kwargs):
        """带并发控制的执行"""
        sem = self.semaphores[resource_type]
        async with sem:
            return await func(*args, **kwargs)

    def get_metrics(self) -> dict:
        """获取并发指标"""
        return {
            **self._metrics,
            "queued_messages": sum(q.queue.qsize() for q in self.agent_queues.values())
        }
```

---

## 十三、配置管理

### 13.1 配置层级

```
配置优先级（从高到低）：
1. 命令行参数
2. 环境变量
3. 用户配置文件（config.user.json）
4. 全局配置文件（config.json）
5. 默认值（代码中）
```

### 13.2 配置管理器实现

```python
class ConfigManager:
    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        self.global_config_path = self.config_dir / "config.json"
        self.user_config_path = self.config_dir / "config.user.json"
        self.env_prefix = "AGENT_OS_"

        self._config = {}
        self._watchers = []
        self._load_config()

    def _load_config(self):
        """加载配置"""
        # 默认配置
        self._config = self._get_default_config()

        # 全局配置文件
        if self.global_config_path.exists():
            with open(self.global_config_path, 'r', encoding='utf-8') as f:
                self._merge_config(json.load(f))

        # 用户配置文件
        if self.user_config_path.exists():
            with open(self.user_config_path, 'r', encoding='utf-8') as f:
                self._merge_config(json.load(f))

        # 环境变量
        self._load_from_env()

    def _merge_config(self, config: dict):
        """合并配置"""
        def _merge(a, b):
            for k, v in b.items():
                if k in a and isinstance(a[k], dict) and isinstance(v, dict):
                    _merge(a[k], v)
                else:
                    a[k] = v
        _merge(self._config, config)

    def _load_from_env(self):
        """从环境变量加载"""
        import os
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                config_key = key[len(self.env_prefix):].lower().replace('__', '.')
                self._set_nested(config_key, value)

    def _set_nested(self, key: str, value):
        """设置嵌套配置值"""
        parts = key.split('.')
        current = self._config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        # 尝试类型转换
        current[parts[-1]] = self._parse_value(value)

    def _parse_value(self, value: str):
        """尝试解析值类型"""
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        if value.lower() == 'null':
            return None
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def get(self, key: str, default=None):
        """获取配置值"""
        parts = key.split('.')
        current = self._config
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set(self, key: str, value, save: bool = True):
        """设置配置值"""
        self._set_nested(key, value)
        if save:
            self.save_user_config()
        self._notify_watchers(key, value)

    def save_user_config(self):
        """保存用户配置"""
        with open(self.user_config_path, 'w', encoding='utf-8') as f:
            json.dump(self._get_user_modified_config(), f, indent=2, ensure_ascii=False)

    def watch(self, key: str, callback):
        """监听配置变化"""
        self._watchers.append((key, callback))

    def _notify_watchers(self, key: str, value):
        """通知监听器"""
        for watch_key, callback in self._watchers:
            if key.startswith(watch_key):
                callback(value)

    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "app": {
                "name": "AI Agent Messenger OS",
                "version": "0.5.0",
                "language": "zh-CN",
                "theme": "light",
            },
            "llm": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "model": "gpt-4o",
                        "temperature": 0.7,
                        "max_tokens": 4096,
                    },
                    "anthropic": {
                        "model": "claude-3-5-sonnet-20241022",
                        "temperature": 0.7,
                        "max_tokens": 4096,
                    }
                }
            },
            "tools": {
                "cli": {
                    "enabled": True,
                    "timeout_seconds": 30,
                },
                "web": {
                    "enabled": True,
                    "timeout_seconds": 60,
                },
                "ui": {
                    "enabled": False,
                    "require_confirmation": True,
                }
            },
            "memory": {
                "summary_threshold": 50,
                "max_history_turns": 100,
            },
            "concurrency": {
                "max_llm_parallel": 5,
                "max_cli_parallel": 3,
                "max_web_parallel": 2,
            },
            "paths": {
                "data_dir": "%APPDATA%/AgentMessengerOS",
                "agents_dir": "%APPDATA%/AgentMessengerOS/agents",
                "skills_dir": "%APPDATA%/AgentMessengerOS/skills",
                "logs_dir": "%APPDATA%/AgentMessengerOS/logs",
            }
        }

    def _get_user_modified_config(self) -> dict:
        """获取用户修改过的配置（对比默认值）"""
        # 实现略，只保存与默认值不同的配置
        return self._config
```

### 13.3 配置热更新

```python
# 配置监听示例
config = ConfigManager(config_dir)

# 监听主题变化
config.watch("app.theme", lambda new_theme: apply_theme(new_theme))

# 监听 LLM 配置变化
config.watch("llm", lambda new_config: reload_llm_clients(new_config))
```

---

## 十四、消息编辑与引用

### 14.1 消息编辑

```python
class MessageEditManager:
    def __init__(self, db):
        self.db = db

    async def edit_message(self, msg_id: str, new_content: str) -> Message:
        """编辑消息"""
        original_msg = await self.db.get_message(msg_id)
        if not original_msg:
            raise MessageNotFoundError()

        # 只有用户消息可以编辑
        if original_msg.role != "user":
            raise PermissionDeniedError()

        # 创建编辑版本
        new_msg = Message(
            msg_id=new_uuid(),
            conversation_id=original_msg.conversation_id,
            role=original_msg.role,
            content=new_content,
            type=original_msg.type,
            is_edited=True,
            edited_from=msg_id,
            reply_to=original_msg.reply_to,
            created_at=datetime.utcnow().isoformat()
        )

        # 保存新消息
        await self.db.insert_message(new_msg)

        # 标记原消息为已编辑
        await self.db.mark_edited(msg_id)

        # 触发重新生成回复
        await self._regenerate_responses(original_msg.conversation_id, new_msg)

        return new_msg

    async def _regenerate_responses(self, conversation_id: str, new_user_msg: Message):
        """重新生成 Agent 回复"""
        # 1. 获取对话中的 Agent
        conversation = await self.db.get_conversation(conversation_id)
        agent = get_agent(conversation.agent_id)

        # 2. 取消原消息后的所有待执行任务
        await cancel_pending_tasks(conversation_id, after_msg_id=new_user_msg.edited_from)

        # 3. 让 Agent 重新处理
        await agent.process_message(new_user_msg, regenerate=True)
```

### 14.2 消息撤回

```python
async def delete_message(msg_id: str, for_me: bool = False):
    """删除/撤回消息"""
    msg = await db.get_message(msg_id)
    if not msg:
        raise MessageNotFoundError()

    # 检查权限：只能撤回自己的消息，且有时间限制
    if msg.role == "user":
        time_diff = datetime.utcnow() - datetime.fromisoformat(msg.created_at)
        if time_diff.total_seconds() > 120:  # 2分钟内可撤回
            raise TimeWindowExpiredError()

    if for_me:
        # 仅对自己删除（隐藏）
        await db.hide_message(msg_id, for_user="current")
    else:
        # 完全撤回
        await db.delete_message(msg_id)
        await broadcast_deletion(msg.conversation_id, msg_id)
```

### 14.3 消息引用与上下文锚点

```python
async def reply_to_message(
    conversation_id: str,
    target_msg_id: str,
    content: str
) -> Message:
    """回复/引用特定消息"""
    target_msg = await db.get_message(target_msg_id)
    if not target_msg:
        raise MessageNotFoundError()

    # 创建回复消息
    reply_msg = Message(
        msg_id=new_uuid(),
        conversation_id=conversation_id,
        role="user",
        content=content,
        type="text",
        reply_to=target_msg_id,
        created_at=datetime.utcnow().isoformat()
    )

    await db.insert_message(reply_msg)
    return reply_msg

def build_context_with_anchor(
    conversation_history: List[Message],
    anchor_msg_id: str
) -> List[dict]:
    """
    构建带锚点的上下文

    当用户引用特定消息时，重点展示锚点附近的对话历史
    """
    context = []
    anchor_found = False

    # 找到锚点消息，展示其前后几条
    for i, msg in enumerate(conversation_history):
        if msg.msg_id == anchor_msg_id:
            anchor_found = True
            # 锚点前 3 条
            context.extend([
                {"role": m.role, "content": m.content}
                for m in conversation_history[max(0, i-3):i]
            ])
            # 锚点消息（标记）
            context.append({
                "role": msg.role,
                "content": f"[引用消息]\n{msg.content}"
            })
            break

    # 如果没找到锚点，展示最近历史
    if not anchor_found:
        context = [
            {"role": m.role, "content": m.content}
            for m in conversation_history[-10:]
        ]

    return context
```

### 14.4 跳转到消息

```python
# 前端实现示例
function jumpToMessage(msg_id: string) {
    const element = document.querySelector(`[data-msg-id="${msg_id}"]`);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        element.classList.add('highlighted');
        setTimeout(() => element.classList.remove('highlighted'), 2000);
    }
}
```

---

## 十五、中断与取消机制

### 15.1 取消令牌

```python
class CancelToken:
    """取消令牌，用于信号传递"""

    def __init__(self):
        self._cancelled = False
        self._event = asyncio.Event()
        self._callbacks = []

    def cancel(self):
        """发出取消信号"""
        if not self._cancelled:
            self._cancelled = True
            self._event.set()
            for callback in self._callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"取消回调执行失败: {e}")

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    async def wait(self):
        """等待取消信号"""
        await self._event.wait()

    def add_callback(self, callback):
        """添加取消回调"""
        if self._cancelled:
            callback()
        else:
            self._callbacks.append(callback)

    def fork(self) -> 'CancelToken':
        """创建子令牌，父取消时子也取消"""
        child = CancelToken()
        self.add_callback(child.cancel)
        return child
```

### 15.2 任务取消管理器

```python
class TaskCancellationManager:
    """管理所有可取消的任务"""

    def __init__(self):
        self._tasks = {}  # task_id -> (task, cancel_token)
        self._lock = asyncio.Lock()

    async def register_task(self, task_id: str, task, cancel_token: CancelToken):
        """注册任务"""
        async with self._lock:
            self._tasks[task_id] = (task, cancel_token)

    async def cancel_task(self, task_id: str) -> bool:
        """取消指定任务"""
        async with self._lock:
            if task_id not in self._tasks:
                return False

            task, cancel_token = self._tasks[task_id]
            cancel_token.cancel()

            # 等待任务响应取消
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"任务 {task_id} 取消超时，强制终止")
            except Exception as e:
                logger.warning(f"任务取消过程出错: {e}")

            del self._tasks[task_id]
            return True

    async def cancel_all(self):
        """取消所有任务"""
        task_ids = list(self._tasks.keys())
        for task_id in task_ids:
            await self.cancel_task(task_id)

    def get_active_tasks(self) -> List[dict]:
        """获取所有活动任务"""
        return [
            {"task_id": task_id, "status": "active"}
            for task_id in self._tasks.keys()
        ]
```

### 15.3 可取消的工具执行示例

```python
async def execute_with_cancellation(
    tool_func,
    *args,
    cancel_token: CancelToken = None,
    **kwargs
):
    """带取消支持的工具执行"""
    if not cancel_token:
        return await tool_func(*args, **kwargs)

    # 创建任务
    task = asyncio.create_task(tool_func(*args, **kwargs))

    # 等待任务完成或取消信号
    done, pending = await asyncio.wait(
        [task, asyncio.shield(cancel_token.wait())],
        return_when=asyncio.FIRST_COMPLETED
    )

    if cancel_token.is_cancelled:
        # 取消任务
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        raise TaskCancelledError()

    return await task
```

### 15.4 清理逻辑

```python
class CleanupManager:
    """负责任务取消后的资源清理"""

    def __init__(self):
        self._cleanup_hooks = []

    def register_cleanup_hook(self, hook):
        """注册清理钩子"""
        self._cleanup_hooks.append(hook)

    async def execute_cleanup(self, task_id: str, context: dict):
        """执行清理"""
        logger.info(f"执行任务清理: {task_id}")

        for hook in self._cleanup_hooks:
            try:
                await hook(task_id, context)
            except Exception as e:
                logger.error(f"清理钩子执行失败: {e}")

        # 清理临时文件
        await self._cleanup_temp_files(task_id)

        # 终止子进程
        await self._terminate_subprocesses(task_id)

    async def _cleanup_temp_files(self, task_id: str):
        """清理该任务创建的临时文件"""
        temp_dir = Path(tempfile.gettempdir()) / f"agent_os_{task_id}"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _terminate_subprocesses(self, task_id: str):
        """终止该任务启动的子进程"""
        # 平台相关实现
        pass
```

---

## 十六、导入导出系统

### 16.1 对话导出

```python
class ExportManager:
    def __init__(self, db):
        self.db = db

    async def export_conversation(
        self,
        conversation_id: str,
        format: str = "markdown",
        include_attachments: bool = True
    ) -> ExportResult:
        """导出对话"""
        messages = await self.db.get_conversation_messages(conversation_id)

        if format == "markdown":
            content = self._export_markdown(messages)
            extension = "md"
        elif format == "json":
            content = self._export_json(messages)
            extension = "json"
        elif format == "pdf":
            content = await self._export_pdf(messages)
            extension = "pdf"
        else:
            raise ValueError(f"不支持的格式: {format}")

        # 处理附件
        attachments = []
        if include_attachments:
            attachments = await self._collect_attachments(messages)

        return ExportResult(
            content=content,
            extension=extension,
            attachments=attachments,
            filename=f"conversation_{conversation_id}.{extension}"
        )

    def _export_markdown(self, messages: List[Message]) -> str:
        """导出为 Markdown"""
        lines = ["# 对话记录\n"]

        for msg in messages:
            timestamp = datetime.fromisoformat(msg.created_at).strftime("%Y-%m-%d %H:%M:%S")
            role = "用户" if msg.role == "user" else "Agent"

            lines.append(f"## {role} ({timestamp})\n")

            if msg.is_edited:
                lines.append("*[已编辑]*\n")

            if msg.reply_to:
                lines.append(f"*[回复消息 {msg.reply_to}]*\n")

            lines.append(msg.content)
            lines.append("\n---\n")

        return "\n".join(lines)

    def _export_json(self, messages: List[Message]) -> str:
        """导出为 JSON"""
        data = [
            {
                "msg_id": msg.msg_id,
                "role": msg.role,
                "content": msg.content,
                "type": msg.type,
                "created_at": msg.created_at,
                "is_edited": msg.is_edited,
                "reply_to": msg.reply_to,
            }
            for msg in messages
        ]
        return json.dumps(data, indent=2, ensure_ascii=False)

    async def _export_pdf(self, messages: List[Message]) -> bytes:
        """导出为 PDF"""
        markdown = self._export_markdown(messages)
        # 使用 markdown2pdf 或类似库
        # 实现略
        return b""
```

### 16.2 Agent 配置导出/导入

```python
async def export_agent(agent_id: str) -> bytes:
    """导出 Agent 配置"""
    agent = await db.get_agent(agent_id)

    export_data = {
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "personality": agent.personality,
        "tools": agent.tools,
        "skills": agent.skills,
        "export_version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
    }

    # 不导出敏感信息（如 API Key）
    if "llm" in export_data and "api_key" in export_data["llm"]:
        del export_data["llm"]["api_key"]

    return json.dumps(export_data, indent=2, ensure_ascii=False).encode('utf-8')

async def import_agent(data: bytes) -> str:
    """导入 Agent 配置"""
    import_data = json.loads(data.decode('utf-8'))

    # 验证格式
    if "export_version" not in import_data:
        raise InvalidImportFormatError()

    # 创建新 Agent
    agent_id = new_uuid()
    agent = Agent(
        agent_id=agent_id,
        name=import_data["name"],
        description=import_data.get("description", ""),
        system_prompt=import_data["system_prompt"],
        personality=import_data.get("personality", {}),
        tools=import_data.get("tools", {}),
        skills=import_data.get("skills", []),
        created_at=datetime.utcnow().isoformat(),
        is_active=True
    )

    await db.insert_agent(agent)
    return agent_id
```

### 16.3 Agent 分享

```python
async def share_agent(agent_id: str) -> str:
    """生成 Agent 分享链接"""
    agent_data = await export_agent(agent_id)

    # 上传到分享服务（可选）
    # share_url = await upload_to_share_service(agent_data)

    # 或生成可复制的分享码（Base64）
    import base64
    share_code = base64.urlsafe_b64encode(agent_data).decode('utf-8')

    return f"agent://share/{share_code}"

async def import_from_share(share_url_or_code: str) -> str:
    """从分享链接/码导入"""
    if share_url_or_code.startswith("agent://share/"):
        share_code = share_url_or_code[len("agent://share/"):]
    else:
        share_code = share_url_or_code

    import base64
    agent_data = base64.urlsafe_b64decode(share_code.encode('utf-8'))
    return await import_agent(agent_data)
```

---

## 十七、UI/UX 增强

### 17.1 加载状态组件

```typescript
// React 组件示例
function AgentTypingIndicator({ agentName }: { agentName: string }) {
    return (
        <div className="agent-typing">
            <Avatar name={agentName} />
            <div className="typing-content">
                <span className="typing-dots">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                </span>
                <span className="typing-text">正在思考...</span>
            </div>
        </div>
    );
}

function ToolExecutionProgress({ task, onCancel }: { task: Task, onCancel: () => void }) {
    return (
        <div className="tool-execution-card">
            <div className="task-header">
                <Icon name={task.icon} />
                <span className="task-description">{task.description}</span>
                <span className="task-step">{task.currentStep}/{task.totalSteps}</span>
            </div>
            <ProgressBar value={task.progress} />
            <div className="task-details">
                {task.logs.map((log, i) => (
                    <div key={i} className="log-entry">{log}</div>
                ))}
            </div>
            <Button variant="secondary" size="small" onClick={onCancel}>
                取消
            </Button>
        </div>
    );
}
```

### 17.2 通知系统

```typescript
// 系统托盘通知
function showSystemNotification(title: string, body: string, options?: NotificationOptions) {
    if (Notification.permission === 'granted') {
        new Notification(title, {
            body,
            icon: '/icon.png',
            ...options
        });
    }
}

// 应用内通知
const toastStore = createStore((set) => ({
    toasts: [],
    addToast: (toast) => set((state) => ({
        toasts: [...state.toasts, { id: uuid(), ...toast }]
    })),
    removeToast: (id) => set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id)
    })),
}));

function Toast({ toast, onClose }: { toast: Toast; onClose: () => void }) {
    useEffect(() => {
        const timer = setTimeout(onClose, toast.duration || 5000);
        return () => clearTimeout(timer);
    }, []);

    return (
        <div className={`toast toast-${toast.type}`}>
            <Icon name={toast.icon} />
            <span>{toast.message}</span>
            <button onClick={onClose}>&times;</button>
        </div>
    );
}
```

### 17.3 右键菜单

```typescript
function MessageContextMenu({ msg, position }: { msg: Message; position: { x: number; y: number } }) {
    return (
        <div
            className="context-menu"
            style={{ left: position.x, top: position.y }}
        >
            <MenuItem icon="copy" onClick={() => copyToClipboard(msg.content)}>
                复制
            </MenuItem>
            {msg.role === 'user' && (
                <MenuItem icon="edit" onClick={() => editMessage(msg)}>
                    编辑
                </MenuItem>
            )}
            <MenuItem icon="quote" onClick={() => quoteMessage(msg)}>
                引用
            </MenuItem>
            <MenuItem icon="bookmark" onClick={() => rememberMessage(msg)}>
                记住这条
            </MenuItem>
            <Divider />
            <MenuItem icon="link" onClick={() => jumpToMessage(msg.msg_id)}>
                定位消息
            </MenuItem>
            {msg.role === 'user' && (
                <MenuItem icon="delete" variant="danger" onClick={() => deleteMessage(msg)}>
                    撤回
                </MenuItem>
            )}
        </div>
    );
}
```

---

## 十八、多语言支持

### 18.1 i18n 框架设计

```typescript
// locales/zh-CN.ts
export default {
    common: {
        save: '保存',
        cancel: '取消',
        confirm: '确认',
        delete: '删除',
        edit: '编辑',
        loading: '加载中...',
        error: '错误',
        success: '成功',
    },
    chat: {
        inputPlaceholder: '输入消息...',
        send: '发送',
        typing: '正在思考...',
        editMessage: '编辑消息',
        deleteMessage: '撤回消息',
        quoteMessage: '引用消息',
    },
    agent: {
        create: '创建 Agent',
        edit: '编辑 Agent',
        delete: '删除 Agent',
        name: '名称',
        description: '描述',
        systemPrompt: '系统提示',
        personality: '性格',
        tools: '工具',
        skills: '技能',
    },
    settings: {
        title: '设置',
        language: '语言',
        theme: '主题',
        llm: 'LLM 配置',
        tools: '工具设置',
        privacy: '隐私设置',
    },
    errors: {
        network: '网络错误，请检查网络连接',
        timeout: '请求超时，请重试',
        permissionDenied: '权限不足',
        rateLimit: '请求过于频繁，请稍后再试',
    }
};

// locales/en-US.ts
export default {
    common: {
        save: 'Save',
        cancel: 'Cancel',
        // ...
    },
    // ...
};
```

### 18.2 语言切换

```typescript
// i18n/store.ts
import { createStore } from 'zustand';
import zhCN from './locales/zh-CN';
import enUS from './locales/en-US';

const translations = {
    'zh-CN': zhCN,
    'en-US': enUS,
};

type Locale = keyof typeof translations;

interface I18nState {
    locale: Locale;
    t: (key: string, params?: Record<string, any>) => string;
    setLocale: (locale: Locale) => void;
}

function translate(obj: any, key: string, params?: Record<string, any>): string {
    const parts = key.split('.');
    let value = obj;
    for (const part of parts) {
        if (value && typeof value === 'object' && part in value) {
            value = value[part];
        } else {
            return key; // 返回 key 作为 fallback
        }
    }

    if (typeof value !== 'string') {
        return key;
    }

    // 插值替换
    if (params) {
        return value.replace(/\{(\w+)\}/g, (_, k) => params[k] ?? `{${k}}`);
    }

    return value;
}

export const useI18n = createStore<I18nState>((set, get) => ({
    locale: 'zh-CN',
    t: (key, params) => translate(translations[get().locale], key, params),
    setLocale: (locale) => {
        set({ locale });
        localStorage.setItem('locale', locale);
    },
}));

// 使用示例
function MyComponent() {
    const { t } = useI18n();
    return <button>{t('common.save')}</button>;
}
```

---

## 十九、测试与运维

### 19.1 测试策略

```python
# tests/unit/test_memory.py
import pytest
from app.memory import MemoryManager

@pytest.mark.asyncio
async def test_memory_add_and_retrieve():
    """测试记忆添加和检索"""
    manager = MemoryManager("test_agent", ":memory:", ":memory:")

    await manager.add_message("user", "我喜欢蓝色")
    await manager.add_message("assistant", "好的，我记住了")
    await manager.add_message("user", "我不喜欢红色")

    relevant = await manager.retrieve_relevant("我喜欢什么颜色？")
    assert any("蓝色" in r for r in relevant)

# tests/integration/test_agent.py
@pytest.mark.asyncio
async def test_agent_full_flow():
    """测试 Agent 完整对话流程"""
    agent = create_test_agent()

    response = await agent.process_message("你好")
    assert response.content is not None

# tests/e2e/test_ui.py
# 使用 Playwright 进行端到端测试
@pytest.mark.playwright
async def test_create_agent(page):
    """测试创建 Agent 的 UI 流程"""
    await page.goto("http://localhost:3000")

    # 点击新建 Agent
    await page.click("#new-agent-btn")

    # 填写表单
    await page.fill("#agent-name", "测试助手")
    await page.fill("#agent-description", "一个测试助手")

    # 提交
    await page.click("#create-agent-btn")

    # 验证
    await page.wait_for_selector(".agent-item", timeout=5000)
    assert "测试助手" in await page.content()
```

### 19.2 监控与日志

```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 指标定义
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status']
)

llm_request_duration = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration',
    ['provider', 'model']
)

active_tasks = Gauge(
    'active_tasks',
    'Number of active tasks',
    ['agent_id']
)

token_usage = Counter(
    'token_usage_total',
    'Total token usage',
    ['provider', 'model', 'type']
)

# 使用示例
def record_llm_request(provider: str, model: str, duration: float, status: str):
    llm_requests_total.labels(provider=provider, model=model, status=status).inc()
    llm_request_duration.labels(provider=provider, model=model).observe(duration)
```

### 19.3 日志系统

```python
# app/logging/setup.py
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)

def setup_logging(log_dir: str):
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    root_logger.addHandler(console_handler)

    # 文件输出 - JSON 格式
    file_handler = RotatingFileHandler(
        log_dir / "app.jsonl",
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(file_handler)

    # 错误日志单独文件
    error_handler = RotatingFileHandler(
        log_dir / "error.jsonl",
        maxBytes=100 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(error_handler)
```

### 19.4 健康检查

```python
# app/health/check.py
from dataclasses import dataclass
from typing import List

@dataclass
class HealthStatus:
    status: str  # "healthy" | "degraded" | "unhealthy"
    checks: List[dict]

async def perform_health_check() -> HealthStatus:
    """执行健康检查"""
    checks = []

    # 数据库检查
    try:
        await db.ping()
        checks.append({"name": "database", "status": "healthy"})
    except Exception as e:
        checks.append({"name": "database", "status": "unhealthy", "error": str(e)})

    # LLM API 检查
    try:
        await llm_client.ping()
        checks.append({"name": "llm_api", "status": "healthy"})
    except Exception as e:
        checks.append({"name": "llm_api", "status": "degraded", "error": str(e)})

    # 磁盘空间检查
    import shutil
    disk_usage = shutil.disk_usage('/')
    if disk_usage.free < 1024 * 1024 * 1024:  # < 1GB
        checks.append({"name": "disk_space", "status": "unhealthy", "free": disk_usage.free})
    else:
        checks.append({"name": "disk_space", "status": "healthy"})

    # 整体状态
    if any(c["status"] == "unhealthy" for c in checks):
        overall = "unhealthy"
    elif any(c["status"] == "degraded" for c in checks):
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthStatus(status=overall, checks=checks)
```

### 19.5 升级与数据迁移

```python
# app/migration/manager.py
from packaging import version

class MigrationManager:
    def __init__(self, db):
        self.db = db
        self.migrations = []

    def register_migration(self, from_version: str, to_version: str, migration_func):
        """注册迁移脚本"""
        self.migrations.append({
            "from": from_version,
            "to": to_version,
            "func": migration_func
        })

    async def migrate(self, current_version: str, target_version: str):
        """执行迁移"""
        if version.parse(current_version) >= version.parse(target_version):
            return

        # 找到需要执行的迁移
        migrations_to_run = []
        v = current_version
        while v != target_version:
            migration = next(
                (m for m in self.migrations if m["from"] == v),
                None
            )
            if not migration:
                break
            migrations_to_run.append(migration)
            v = migration["to"]

        # 按顺序执行
        for migration in migrations_to_run:
            logger.info(f"Migrating from {migration['from']} to {migration['to']}")
            await migration["func"](self.db)

        # 更新版本号
        await self.db.set_schema_version(target_version)

# 示例迁移
async def migrate_0_4_to_0_5(db):
    """从 0.4 升级到 0.5"""
    # 添加新表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            agent_id TEXT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT
        )
    """)

    # 修改现有表
    await db.execute("""
        ALTER TABLE agents ADD COLUMN concurrency_config TEXT
    """)

# 注册
migration_manager = MigrationManager(db)
migration_manager.register_migration("0.4.0", "0.5.0", migrate_0_4_to_0_5)
```

### 19.6 自动更新

```typescript
// 前端自动更新检查
async function checkForUpdates() {
    const response = await fetch('https://api.example.com/releases/latest');
    const release = await response.json();

    if (versionCompare(release.version, appVersion) > 0) {
        // 有新版本
        showUpdateNotification(release);
    }
}

// Electron 自动更新
import { autoUpdater } from 'electron-updater';

autoUpdater.setFeedURL({
    provider: 'github',
    owner: 'example',
    repo: 'agent-messenger',
});

autoUpdater.on('update-available', (info) => {
    mainWindow.webContents.send('update-available', info);
});

autoUpdater.on('update-downloaded', (info) => {
    mainWindow.webContents.send('update-downloaded', info);
});

autoUpdater.checkForUpdatesAndNotify();
```

---

## 二十、系统架构

### 20.1 完整分层架构

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          UI Layer (Electron + React)                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │  聊天界面     │ │ Agent 管理    │ │  任务历史    │ │   设置面板        │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘  │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │ IPC / WebSocket
┌────────────────────────────────▼──────────────────────────────────────────┐
│                         Backend Layer (Python + Flask)                      │
│                                                                             │
│  ┌──────────────────┐    ┌─────────────────────────────────────────────┐  │
│  │  Agent Manager   │    │    Multi-Agent Engine                       │  │
│  │  - CRUD          │    │    - Planner / Worker / Critic              │  │
│  │  - State         │    │    - Group Chat Bus                        │  │
│  └──────────────────┘    └─────────────────────────────────────────────┘  │
│  ┌──────────────────┐    ┌─────────────────────────────────────────────┐  │
│  │  Skill Loader    │    │    Memory Manager                          │  │
│  │  - 热加载        │    │    - L1/L2/L3                              │  │
│  │  - 调用          │    │    - Vector Store                          │  │
│  └──────────────────┘    └─────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                       Tools Layer                                   │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                   │  │
│  │  │CLI Tool │ │Web Tool │ │UI Tool  │ │Vision   │                   │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────┐    ┌─────────────────────────────────────────────┐  │
│  │  Config Manager  │    │    Error & Retry                           │  │
│  │  - 配置管理      │    │    - Fallback                             │  │
│  │  - 热更新        │    │    - Recovery                             │  │
│  └──────────────────┘    └─────────────────────────────────────────────┘  │
│  ┌──────────────────┐    ┌─────────────────────────────────────────────┐  │
│  │  Security        │    │    Concurrency Control                     │  │
│  │  - 权限控制      │    │    - Queues                               │  │
│  │  - 审计日志      │    │    - Pooling                              │  │
│  └──────────────────┘    └─────────────────────────────────────────────┘  │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼──────────────────────────────────────────┐
│                      LLM Provider Layer                                    │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐                      │
│  │ OpenAI  │ │Anthropic │ │ 讯飞    │ │ Ollama   │                      │
│  └─────────┘ └──────────┘ └─────────┘ └──────────┘                      │
└────────────────────────────────┬──────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼──────────────────────────────────────────┐
│                        Storage Layer                                       │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────┐                          │
│  │  SQLite  │ │  ChromaDB    │ │  File System │                          │
│  └──────────┘ └──────────────┘ └──────────────┘                          │
└───────────────────────────────────────────────────────────────────────────┘
```

### 20.2 Electron ↔ Python 通信

```typescript
// Electron Main Process (TypeScript)
import { PythonShell } from 'python-shell';
import { WebSocketServer } from 'ws';

// 启动 Python 后端
function startPythonBackend() {
    const pythonShell = new PythonShell('backend/main.py', {
        pythonPath: 'venv/bin/python',
    });

    pythonShell.on('message', (message) => {
        console.log('Python:', message);
    });

    return pythonShell;
}

// WebSocket 服务器
const wss = new WebSocketServer({ port: 7890 });

wss.on('connection', (ws) => {
    ws.on('message', async (data) => {
        const request = JSON.parse(data.toString());
        const response = await routeToBackend(request);
        ws.send(JSON.stringify(response));
    });
});

// 路由到后端
async function routeToBackend(request: any) {
    switch (request.type) {
        case 'send_message':
            return await agentManager.send_message(request);
        case 'create_agent':
            return await agentManager.create_agent(request);
        case 'get_conversation':
            return await agentManager.get_conversation(request);
        default:
            return { error: 'Unknown request type' };
    }
}
```

```python
# Python WebSocket Handler
from flask_sock import Sock

sock = Sock(app)

@sock.route('/ws')
def websocket_handler(ws):
    while True:
        data = ws.receive()
        request = json.loads(data)

        # 路由到对应处理函数
        response = handle_request(request)

        ws.send(json.dumps(response))

def handle_request(request: dict):
    handler = request_handlers.get(request['type'])
    if handler:
        return handler(request)
    return {'error': 'Unknown request type'}
```

---

## 二十一、技术栈与依赖

### 21.1 前端（Electron + React）

| 包 | 版本 | 用途 |
|----|------|------|
| `electron` | ^28.0 | 桌面应用框架 |
| `react` | ^18.2 | UI 渲染 |
| `react-dom` | ^18.2 | DOM 渲染 |
| `react-router-dom` | ^6.20 | 路由 |
| `zustand` | ^4.4 | 状态管理 |
| `react-markdown` | ^9.0 | Markdown 渲染 |
| `highlight.js` | ^11.9 | 代码高亮 |
| `tailwindcss` | ^3.3 | CSS 框架 |
| `ws` | ^8.14 | WebSocket 客户端 |
| `dayjs` | ^1.11 | 日期处理 |
| `lucide-react` | ^0.29 | 图标库 |

### 21.2 后端（Python）

| 包 | 版本 | 用途 |
|----|------|------|
| `flask` | ^3.0 | Web 框架 |
| `flask-sock` | ^0.7 | WebSocket 支持 |
| `openai` | ^1.3 | OpenAI SDK |
| `anthropic` | ^0.16 | Anthropic SDK |
| `playwright` | ^1.40 | Web 自动化 |
| `pyautogui` | ^0.9 | UI 自动化 |
| `sqlalchemy` | ^2.0 | ORM |
| `chromadb` | ^0.4 | 向量数据库 |
| `pillow` | ^10.1 | 图像处理 |
| `keyring` | ^24.2 | 系统密钥链 |
| `watchdog` | ^4.0 | 文件监控 |
| `prometheus-client` | ^0.19 | 指标监控 |
| `python-dotenv` | ^1.0 | 环境变量 |
| `pydantic` | ^2.5 | 数据验证 |

### 21.3 测试

| 包 | 版本 | 用途 |
|----|------|------|
| `pytest` | ^7.4 | 测试框架 |
| `pytest-asyncio` | ^0.21 | 异步测试 |
| `pytest-playwright` | ^0.4 | E2E 测试 |
| `pytest-cov` | ^4.1 | 覆盖率 |

### 21.4 支持的 LLM 提供商

| 提供商 | 接入方式 | 模型示例 |
|--------|----------|----------|
| OpenAI | `openai` SDK | GPT-4o, GPT-4 Turbo, GPT-3.5 |
| Anthropic | `anthropic` SDK | Claude 3.5 Sonnet, Claude 3 Opus |
| 讯飞星火 | HTTP API | Spark Lite, Spark Pro |
| 火山引擎 | HTTP API | Doubao, Doubao Pro |
| Ollama | 本地 HTTP | Llama 2, Mistral, CodeLlama |

---

## 二十二、数据存储设计

### 22.1 目录结构

```
%APPDATA%\AgentMessengerOS\
├── config.json              # 全局配置
├── config.user.json         # 用户配置
├── agents\                  # Agent 配置
│   ├── {agent_id}.json
│   └── ...
├── conversations\           # 对话历史
│   ├── {conversation_id}.db
│   └── ...
├── memory\
│   ├── agent_memory.db      # SQLite：会话摘要 + 元数据
│   └── vector_store\        # ChromaDB：长期向量记忆
├── skills\                  # 用户自定义技能
│   ├── my_skill.py
│   └── ...
├── checkpoints\             # 检查点
│   ├── {agent_id}.json
│   └── ...
├── logs\
│   ├── app.jsonl            # 应用日志
│   ├── error.jsonl          # 错误日志
│   ├── audit.jsonl          # 审计日志
│   └── task_history.jsonl   # 任务执行历史
├── temp\                    # 临时文件
│   └── ...
└── exports\                 # 导出文件
    └── ...
```

### 22.2 SQLite 主要表结构

```sql
-- Agent 表
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    avatar TEXT,
    system_prompt TEXT,
    personality_json TEXT,
    llm_config_json TEXT,
    tools_config_json TEXT,
    skills_json TEXT,
    concurrency_config_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    tags_json TEXT
);

-- 对话表
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    agent_id TEXT,
    group_id TEXT,
    title TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

-- 消息表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    agent_id TEXT,
    role TEXT NOT NULL,  -- 'user' | 'assistant' | 'system' | 'tool'
    type TEXT NOT NULL,  -- 'text' | 'tool_call' | 'tool_result' | 'error'
    content TEXT,
    content_html TEXT,
    attachments_json TEXT,
    tool_calls_json TEXT,
    tool_results_json TEXT,
    reply_to TEXT,
    is_edited INTEGER DEFAULT 0,
    edited_from TEXT,
    is_pinned INTEGER DEFAULT 0,
    is_remembered INTEGER DEFAULT 0,
    status TEXT DEFAULT 'sent',  -- 'sending' | 'sent' | 'failed' | 'cancelled'
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- 任务执行记录表
CREATE TABLE task_records (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    agent_id TEXT,
    task_type TEXT NOT NULL,
    input_json TEXT,
    output_json TEXT,
    status TEXT NOT NULL,  -- 'success' | 'failed' | 'partial' | 'cancelled'
    error_message TEXT,
    duration_ms INTEGER,
    token_usage_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- 记忆摘要表
CREATE TABLE memory_summaries (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    message_count INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

-- 审计日志表
CREATE TABLE audit_log (
    event_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    agent_id TEXT,
    user_id TEXT,
    action TEXT NOT NULL,
    resource TEXT,
    status TEXT NOT NULL,
    details_json TEXT,
    ip_address TEXT
);

-- 配置版本表
CREATE TABLE schema_version (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- 索引
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_agent ON messages(agent_id);
CREATE INDEX idx_task_records_agent ON task_records(agent_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
```

---

## 二十三、开发路线图

### Phase 1（MVP）- 预计 4 周

目标：核心单 Agent 对话功能

- [x] 规格文档 v0.5（补充所有完善项）
- [ ] 项目初始化
  - [ ] 前端项目搭建（Electron + React + TypeScript）
  - [ ] 后端项目搭建（Python + Flask）
  - [ ] 开发环境配置
- [ ] 基础 UI
  - [ ] 微信风格布局
  - [ ] 导航栏
  - [ ] 消息列表
  - [ ] 输入框
- [ ] Agent 管理
  - [ ] Agent 创建/编辑/删除 UI
  - [ ] Agent 数据模型
  - [ ] Agent 持久化
- [ ] 单 Agent 对话
  - [ ] 消息发送/接收
  - [ ] WebSocket 通信
  - [ ] LLM 集成（OpenAI/Anthropic）
  - [ ] 对话历史持久化
- [ ] CLI 工具（安全版）
  - [ ] 命令白名单
  - [ ] 沙箱执行
  - [ ] 流式输出
- [ ] 基础错误处理

### Phase 2（核心功能）- 预计 4 周

目标：完整的 Agent 能力 + 工具 + 技能

- [ ] Planner / Worker / Critic 三角架构
- [ ] Web 自动化工具（Playwright）
- [ ] Skill 插件系统
  - [ ] Skill 加载器
  - [ ] 热重载
  - [ ] 3个内置 Skill
- [ ] 记忆管理（L1/L2）
- [ ] 任务执行历史面板
- [ ] 并发控制
- [ ] 重试策略
- [ ] 配置管理

### Phase 3（多 Agent 协作）- 预计 3 周

目标：群聊 + 多 Agent 协作

- [ ] 群聊 UI
- [ ] 多 Agent 协作引擎
  - [ ] 任务模式
  - [ ] 讨论模式
- [ ] Agent 间消息协议
- [ ] GroupChatBus
- [ ] Coordinator 角色
- [ ] 讨论模式防死循环
- [ ] 任务依赖图可视化
- [ ] 角色动态切换
- [ ] UI 自动化工具 + 安全保护

### Phase 4（完善与发布）- 预计 3 周

目标：完善、安全、可发布

- [ ] Vision 工具
- [ ] L3 向量记忆（ChromaDB）
- [ ] 多 LLM 提供商支持
- [ ] Agent 模板库
- [ ] 安全系统
  - [ ] 细粒度权限
  - [ ] 审计日志
  - [ ] 隐私模式
- [ ] 消息编辑/撤回/引用
- [ ] 导入导出
- [ ] 多语言支持
- [ ] 测试
  - [ ] 单元测试
  - [ ] 集成测试
  - [ ] E2E 测试
- [ ] 监控与日志
- [ ] 数据迁移
- [ ] 自动更新
- [ ] 打包发布
  - [ ] electron-builder
  - [ ] Windows 安装包
  - [ ] 数字签名

---

**文档版本**: v0.5
**最后更新**: 2025-05-05
**变更记录**:
- v0.1 - 初始版本
- v0.2 - 细化内容
- v0.3 - 补充多 Agent 协作协议
- v0.4 - 基础完整版
- v0.5 - 完善版，新增：
  - 错误处理与重试策略
  - 并发控制
  - 配置管理
  - 消息编辑/引用/撤回
  - 中断与取消
  - 导入导出
  - UI/UX 增强
  - 多语言支持
  - 测试与运维
  - 安全系统增强
  - 升级与迁移
  - 自动更新
```

现在我将把更新后的规格文档写入到用户指定的位置：

<seed:tool_call><function name="Write"><parameter name="file_path" string="true">C:\Users\Z1004\Desktop\AI_Agent_Messenger_OS_SPEC_完整版_v0.5.md