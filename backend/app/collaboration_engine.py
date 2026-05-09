"""
协作引擎 — 任务模式 + 讨论模式

整合 GroupChatBus / DeadlockDetector / PermissionChecker / AuditLogger
提供多 Agent 协作的两种模式：
  - task:       基于 PWC 的多 Agent 任务执行
  - discussion: 基于 LLM 的多 Agent 自由讨论
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Agent, GroupConversation, GroupParticipant, DiscussionRound,
    TaskExecution, Message, Plan, SubTask,
)
from app.llm_client import LLMClient, llm_client_from_agent
from app.context_manager import ContextManager
from app.orchestrator import Orchestrator, PWCProgressCallback, PWCState
from app.group_chat_bus import GroupChatBus, BusMessage, BusEvent
from app.deadlock_detector import DeadlockDetector, DeadlockReport
from app.security import PermissionChecker, AuditLogger, PermissionResult
from app.free_dialogue_manager import FreeDialogueManager, FreeDialogueConfig

logger = logging.getLogger(__name__)

# Module-level engine registry for multi-group concurrency
_engines: dict[str, "CollaborationEngine"] = {}
# Track free dialogue active state separately for quick lookup
_free_dialogue_active: set[str] = set()


def get_or_create_engine(group_id: str, db: Session, api_keys: dict) -> "CollaborationEngine":
    """Get or create a CollaborationEngine for a group."""
    if group_id not in _engines:
        _engines[group_id] = CollaborationEngine(db, api_keys)
    return _engines[group_id]


def get_engine(group_id: str) -> "Optional[CollaborationEngine]":
    """Get an existing CollaborationEngine for a group, or None."""
    return _engines.get(group_id)


def remove_engine(group_id: str):
    """Remove and cleanup a CollaborationEngine for a group."""
    engine = _engines.pop(group_id, None)
    if engine:
        engine.cleanup()
    _free_dialogue_active.discard(group_id)


def is_free_dialogue_active(group_id: str) -> bool:
    """Check if a free dialogue session is active for the group."""
    return group_id in _free_dialogue_active


def set_free_dialogue_active(group_id: str, active: bool):
    """Mark a group's free dialogue as active/inactive."""
    if active:
        _free_dialogue_active.add(group_id)
    else:
        _free_dialogue_active.discard(group_id)


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class CollaborationMode(str, Enum):
    TASK = "task"
    DISCUSSION = "discussion"
    FREE_DIALOGUE = "free_dialogue"


class SessionState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class CollaborationSession:
    """协作会话"""
    id: str = ""
    group_id: str = ""
    mode: CollaborationMode = CollaborationMode.DISCUSSION
    state: SessionState = SessionState.IDLE
    topic: str = ""
    agents: list[Agent] = field(default_factory=list)
    current_round: Optional[DiscussionRound] = None
    orchestrator_result: Optional[dict] = None
    error: Optional[str] = None
    created_at: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "mode": self.mode.value,
            "state": self.state.value,
            "topic": self.topic,
            "agents": [{"id": a.id, "name": a.name} for a in self.agents],
            "current_round": self.current_round.to_dict() if self.current_round else None,
            "orchestrator_result": self.orchestrator_result or {},
            "error": self.error or "",
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class CollaborationConfig:
    """协作引擎配置"""
    max_discussion_rounds: int = 50
    max_discussion_tokens: int = 500_000
    max_task_duration: int = 3600
    stall_timeout: float = 120.0
    loop_window: int = 50
    repeat_threshold: int = 5
    max_concurrent_tasks: int = 5
    enable_audit: bool = True


# ---------------------------------------------------------------------------
# 协作引擎
# ---------------------------------------------------------------------------

class CollaborationEngine:
    """
    协作引擎 — 多 Agent 协作核心。

    支持两种模式：
    - task:       Plan → 分发子任务给不同 Agent → 汇总结果
    - discussion: 多 Agent 围绕主题自由讨论 / 辩论
    """

    def __init__(
        self,
        db: Session,
        api_keys: dict,
        config: Optional[CollaborationConfig] = None,
    ):
        self.db = db
        self.api_keys = api_keys
        self.config = config or CollaborationConfig()

        # 子系统
        self.bus = GroupChatBus(db)
        self.detector = DeadlockDetector(
            loop_window=self.config.loop_window,
            repeat_threshold=self.config.repeat_threshold,
            max_turns=self.config.max_discussion_rounds,
            max_tokens=self.config.max_discussion_tokens,
            max_duration=self.config.max_task_duration,
            stall_timeout=self.config.stall_timeout,
        )
        self.audit = AuditLogger(db) if self.config.enable_audit else None

        # 会话状态
        self._session: Optional[CollaborationSession] = None
        self._running = False
        self._callbacks: list[Callable] = []
        self._dialogue_mgr: Any = None

        # 注册总线回调
        self.bus.on_message(self._on_bus_message)

    # ------------------------------------------------------------------
    # 会话生命周期
    # ------------------------------------------------------------------

    async def start_session(
        self,
        group_id: str,
        mode: str = "discussion",
        topic: str = "",
    ) -> CollaborationSession:
        """开始新的协作会话。"""
        if self._running:
            raise RuntimeError("已有正在运行的协作会话")

        group = self.db.query(GroupConversation).filter(GroupConversation.id == group_id).first()
        if not group:
            raise ValueError(f"群聊不存在: {group_id}")

        agents = self.bus.get_active_agents(group_id)
        if not agents:
            raise ValueError("群聊中没有活跃 Agent")

        session_id = self._gen_id()

        self._session = CollaborationSession(
            id=session_id,
            group_id=group_id,
            mode=CollaborationMode(mode),
            topic=topic,
            agents=agents,
            created_at=datetime.now(timezone.utc).timestamp(),
        )

        # 更新群聊模式
        group.mode = mode
        self.db.commit()

        # 启动防死锁检测
        self.detector.budget.start_session(session_id)
        self.detector.stall.start_monitoring(session_id)

        # 审计
        if self.audit:
            self.audit.log(
                action="group_action",
                agent_id="system",
                resource_type="group",
                resource_id=group_id,
                details={"action": "start_session", "mode": mode, "topic": topic},
            )

        self._running = True

        # Mark free dialogue active immediately for quick WS check
        if mode == "free_dialogue":
            set_free_dialogue_active(group_id, True)

        # 广播开始消息
        await self.bus.broadcast(
            group_id=group_id,
            message=f"协作会话已开始 — 模式: {mode}，主题: {topic or '无'}",
        )

        # 根据模式执行
        if mode == "task":
            await self._run_task_mode(group_id, topic)
        elif mode == "free_dialogue":
            # Run in background so start_session returns immediately;
            # user messages can be injected via inject_user_message()
            asyncio.ensure_future(self._run_free_dialogue_mode(group_id, topic))
        else:
            await self._run_discussion_mode(group_id, topic)

        return self._session

    async def stop_session(self, session_id: Optional[str] = None) -> bool:
        """停止协作会话。"""
        if not self._session or (session_id and self._session.id != session_id):
            return False

        self._session.state = SessionState.CANCELLED
        self._running = False

        # Stop free dialogue if running
        if self._dialogue_mgr:
            await self._dialogue_mgr.stop()
            self._dialogue_mgr = None

        if self._session.group_id:
            set_free_dialogue_active(self._session.group_id, False)

        self.detector.clear_all(session_id=self._session.id)
        await self.detector.stall.stop_background_check()

        await self.bus.broadcast(
            group_id=self._session.group_id,
            message="协作会话已结束",
        )

        if self.audit:
            self.audit.log(
                action="group_action",
                resource_type="group",
                resource_id=self._session.group_id,
                details={"action": "stop_session", "session_id": session_id},
            )

        return True

    async def pause_session(self) -> bool:
        """暂停会话。"""
        if not self._session or self._session.state != SessionState.RUNNING:
            return False
        self._session.state = SessionState.PAUSED
        await self.bus.broadcast(
            group_id=self._session.group_id,
            message="协作会话已暂停",
        )
        return True

    async def resume_session(self) -> bool:
        """恢复会话。"""
        if not self._session or self._session.state != SessionState.PAUSED:
            return False
        self._session.state = SessionState.RUNNING
        await self.bus.broadcast(
            group_id=self._session.group_id,
            message="协作会话已恢复",
        )
        return True

    # ------------------------------------------------------------------
    # 任务模式
    # ------------------------------------------------------------------

    async def _run_task_mode(self, group_id: str, goal: str):
        """
        任务模式 — 使用主 Agent 的 PWC 编排，结果广播给群组。

        流程：
        1. 主 Agent 创建 Plan
        2. 子任务分配给不同 Agent
        3. 各 Agent 执行并广播进度
        4. 汇总结果
        """
        self._session.state = SessionState.RUNNING
        agents = self._session.agents
        if not agents:
            self._session.state = SessionState.FAILED
            self._session.error = "无可用 Agent"
            return

        main_agent = agents[0]  # 第一个 Agent 作为主控

        try:
            # 防死锁检查
            report = self.detector.check_all(main_agent.id, self._session.id)
            if report.triggered:
                raise RuntimeError(f"防死锁触发: {report.reason}")

            # 创建 Orchestrator
            orchestrator = Orchestrator(
                db=self.db,
                api_keys=self.api_keys,
                max_concurrent=self.config.max_concurrent_tasks,
            )

            # 设置进度回调
            orchestrator.set_callback(_TaskProgressCallback(self))

            # 执行 PWC 循环
            result = await orchestrator.run(
                agent=main_agent,
                conversation_id="",
                goal=goal,
                context=self._build_task_context(goal, agents),
            )

            self._session.orchestrator_result = result.to_dict()
            self._session.state = SessionState.COMPLETED

            # 广播结果
            summary = orchestrator.get_execution_summary()
            await self.bus.broadcast(
                group_id=group_id,
                message=f"任务完成: {summary.get('plan_title', goal)}\n"
                        f"状态: {summary.get('state', 'unknown')} | "
                        f"完成: {summary.get('completed', 0)}/{summary.get('total', 0)}",
            )

            # 审计
            if self.audit:
                self.audit.log(
                    action="group_action",
                    resource_type="group",
                    resource_id=group_id,
                    details={
                        "action": "task_complete",
                        "goal": goal[:200],
                        "summary": summary,
                    },
                )

        except Exception as e:
            logger.exception("任务模式执行失败")
            self._session.state = SessionState.FAILED
            self._session.error = str(e)
            await self.bus.broadcast(
                group_id=group_id,
                message=f"任务执行失败: {e}",
            )

    def _build_task_context(self, goal: str, agents: list[Agent]) -> str:
        """构建包含多 Agent 信息的任务上下文。"""
        agent_info = "\n".join(
            f"- {a.name} (角色: {a.role or '通用'}, 模型: {a.model_provider}/{a.model_name})"
            for a in agents
        )
        return (
            f"## 可用 Agent\n{agent_info}\n\n"
            f"## 协作目标\n{goal}\n\n"
            f"请合理分配子任务给不同的 Agent。"
        )

    # ------------------------------------------------------------------
    # 讨论模式
    # ------------------------------------------------------------------

    async def _run_discussion_mode(self, group_id: str, topic: str):
        """
        讨论模式 — 多 Agent 轮流发言讨论。

        流程：
        1. 广播讨论开始
        2. 各 Agent 按轮次策略轮流发言
        3. 每轮结束后检查是否达成共识或超限
        """
        self._session.state = SessionState.RUNNING

        # 开始第一轮
        round_record = self.bus.start_round(group_id, topic=topic)
        self._session.current_round = round_record

        agents = self._session.agents
        if not agents:
            self._session.state = SessionState.FAILED
            self._session.error = "无可用 Agent"
            return

        # 收集讨论历史
        discussion_history: list[dict] = []

        round_num = 0
        max_rounds = self.config.max_discussion_rounds

        while self._running and round_num < max_rounds:
            # 检查暂停
            if self._session.state == SessionState.PAUSED:
                await asyncio.sleep(1)
                continue

            # 防死锁检查
            report = self.detector.check_all("discussion", self._session.id)
            if report.triggered:
                logger.warning("讨论防死锁触发: %s", report.reason)
                await self.bus.broadcast(
                    group_id=group_id,
                    message=f"讨论结束: {report.reason}",
                )
                break

            for agent in agents:
                if not self._running:
                    break

                # 防死锁 - Level 1 环路检测
                report = self.detector.loop.check(agent.id)
                if report.triggered:
                    logger.warning("Agent %s 触发环路检测，跳过", agent.name)
                    await self.bus.broadcast(
                        group_id=group_id,
                        message=f"{agent.name} 因检测到重复发言已被跳过",
                    )
                    continue

                # 权限检查
                if self.audit:
                    perm = PermissionChecker.check_agent_active(agent)
                    if not perm.allowed:
                        self.audit.log_permission_denied(
                            agent_id=agent.id,
                            resource_type="group",
                            reason=perm.reason,
                        )
                        continue

                # 生成 Agent 发言
                try:
                    reply = await self._generate_agent_reply(
                        agent=agent,
                        topic=topic,
                        history=discussion_history,
                    )
                except Exception as e:
                    logger.error("Agent %s 发言生成失败: %s", agent.name, e)
                    continue

                # 发送到总线
                bus_msg = await self.bus.send_message(
                    group_id=group_id,
                    sender_id=agent.id,
                    content=reply,
                    msg_type="text",
                )

                # 记录环路检测
                self.detector.loop.record(agent.id, "discussion_reply")
                self.detector.budget.record_turn(self._session.id, tokens=len(reply))

                # 记录历史
                discussion_history.append({
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "content": reply,
                })

            round_num += 1

            # 轮次摘要
            if round_num % 5 == 0 and self._session.current_round:
                await self._generate_round_summary(group_id, round_record)

            # Agent 间延迟
            await asyncio.sleep(0.5)

        # 讨论结束
        if round_record:
            self.bus.end_round(round_record.id)

        self._session.state = SessionState.COMPLETED
        await self.bus.broadcast(
            group_id=group_id,
            message=f"讨论结束，共 {round_num} 轮",
        )

    async def _generate_agent_reply(
        self,
        agent: Agent,
        topic: str,
        history: list[dict],
    ) -> str:
        """使用 LLM 生成 Agent 的讨论发言。"""
        llm = llm_client_from_agent(agent, self.api_keys)

        # 构造提示
        system_prompt = (
            f"你是 {agent.name}，角色: {agent.role or '通用AI助手'}。\n"
            f"请基于你的角色定位参与群组讨论。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"讨论主题: {topic}"},
        ]

        # 注入讨论历史
        if history:
            history_text = "\n".join(
                f"{h['agent_name']}: {h['content'][:500]}"
                for h in history[-20:]  # 最近 20 条
            )
            messages.append({"role": "user", "content": f"当前讨论:\n{history_text}\n\n请基于你的角色发表见解。"})

        # 流式收集回复
        full_reply = ""
        try:
            for chunk in llm.stream(messages):
                full_reply += chunk
        except Exception as e:
            logger.error("LLM 流式生成失败: %s", e)
            full_reply = f"[{agent.name} 暂时无法参与讨论]"

        return full_reply[:2000]  # 限制发言长度

    async def _generate_round_summary(self, group_id: str, round_record: DiscussionRound):
        """生成并更新讨论轮次摘要。"""
        try:
            summary = f"第 {round_record.round_number} 轮讨论持续中，已有多轮观点交换。"
            self.bus.update_round_summary(round_record.id, summary)
        except Exception as e:
            logger.warning("轮次摘要生成失败: %s", e)

    # ------------------------------------------------------------------
    # 总线回调
    # ------------------------------------------------------------------

    def _on_bus_message(self, event: BusEvent):
        """总线消息回调 — 转发到注册的外部回调。"""
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception:
                logger.exception("外部回调执行失败")

    def on_event(self, callback: Callable):
        """注册外部事件回调（如 WebSocket 转发）。"""
        self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 自由对话模式
    # ------------------------------------------------------------------

    async def _run_free_dialogue_mode(self, group_id: str, topic: str):
        """
        自由对话模式 — Agent 自由讨论、协商、达成共识。

        流程：
        1. 创建 FreeDialogueManager
        2. 注册回调将消息转发到总线
        3. 驱动对话循环直到结束
        """
        self._session.state = SessionState.RUNNING
        agents = self._session.agents
        if not agents:
            self._session.state = SessionState.FAILED
            self._session.error = "无可用 Agent"
            return

        self._dialogue_mgr = FreeDialogueManager(
            db=self.db,
            api_keys=self.api_keys,
            group_id=group_id,
            agents=agents,
            topic=topic,
            config=FreeDialogueConfig(
                max_turns=self.config.max_discussion_rounds,
                max_tokens=self.config.max_discussion_tokens,
                stall_timeout=self.config.stall_timeout,
            ),
        )
        dialogue_mgr = self._dialogue_mgr

        # Register callback to forward messages to bus and external callbacks
        def forward_to_bus(data: dict):
            msg_type = data.get("type", "")
            if msg_type == "free_dialogue_message":
                asyncio.ensure_future(
                    self.bus.send_message(
                        group_id=group_id,
                        sender_id=data.get("agent_id", ""),
                        content=data.get("content", ""),
                        msg_type="text",
                    )
                )
            # Forward to external callbacks (e.g., WebSocket)
            for cb in self._callbacks:
                try:
                    cb(data)
                except Exception:
                    logger.exception("外部回调执行失败")

        dialogue_mgr.on_message(forward_to_bus)

        try:
            await dialogue_mgr.start()
            self._session.state = SessionState.COMPLETED
        except Exception as e:
            logger.exception("自由对话模式执行失败")
            self._session.state = SessionState.FAILED
            self._session.error = str(e)
            await dialogue_mgr.stop()
        finally:
            self._dialogue_mgr = None
            set_free_dialogue_active(group_id, False)

    async def inject_user_message(self, content: str):
        """将用户消息注入当前自由对话，触发 agents 回复。"""
        if not self._dialogue_mgr:
            return
        self._dialogue_mgr.inject_user_message(content)
        # After injecting, let the coordinator know so agents can respond
        # The dialogue loop is async; the next turn will pick up the new context

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_session(self) -> Optional[CollaborationSession]:
        """获取当前会话。"""
        return self._session

    def get_state_summary(self) -> dict:
        """获取协作状态摘要。"""
        if not self._session:
            return {"state": "idle"}

        return {
            "session_id": self._session.id,
            "mode": self._session.mode.value,
            "state": self._session.state.value,
            "topic": self._session.topic,
            "agent_count": len(self._session.agents),
            "has_error": bool(self._session.error),
        }

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------

    def cleanup(self):
        """清理引擎状态。"""
        self._running = False
        self._session = None
        self.bus.cleanup()
        self.detector.clear_all()
        self._callbacks.clear()

    @staticmethod
    def _gen_id() -> str:
        import uuid
        return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Orchestrator 进度回调
# ---------------------------------------------------------------------------

class _TaskProgressCallback(PWCProgressCallback):
    """将 PWC 进度广播到群聊的适配器。"""

    def __init__(self, engine: CollaborationEngine):
        self.engine = engine

    def on_state_change(self, state: PWCState, plan_id: str, **kwargs):
        asyncio.ensure_future(
            self.engine.bus.broadcast(
                group_id=self.engine._session.group_id if self.engine._session else "",
                message=f"任务状态变更: {state.value}",
            )
        )

    def on_subtask_start(self, subtask: SubTask):
        asyncio.ensure_future(
            self.engine.bus.broadcast(
                group_id=self.engine._session.group_id if self.engine._session else "",
                message=f"开始执行子任务: {subtask.title}",
            )
        )

    def on_subtask_complete(self, subtask: SubTask, result: dict, review=None):
        review_note = f" | 评审: {review.verdict}" if review and hasattr(review, "verdict") else ""
        asyncio.ensure_future(
            self.engine.bus.broadcast(
                group_id=self.engine._session.group_id if self.engine._session else "",
                message=f"子任务完成: {subtask.title}{review_note}",
            )
        )

    def on_error(self, error: str):
        asyncio.ensure_future(
            self.engine.bus.broadcast(
                group_id=self.engine._session.group_id if self.engine._session else "",
                message=f"任务出错: {error}",
            )
        )

    def on_complete(self, result):
        asyncio.ensure_future(
            self.engine.bus.broadcast(
                group_id=self.engine._session.group_id if self.engine._session else "",
                message=f"全部任务执行完毕",
            )
        )
