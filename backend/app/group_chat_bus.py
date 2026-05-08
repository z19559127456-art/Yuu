"""
群聊消息路由总线 — 消息分发 / 轮次管理 / 广播
"""
import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Agent, GroupConversation, GroupParticipant, DiscussionRound, Message
from app.llm_client import LLMClient, llm_client_from_agent
from app.context_manager import ContextManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class TurnStrategy(Enum):
    """轮次策略"""
    ROUND_ROBIN = "round_robin"       # 轮流发言
    FREE = "free"                     # 自由发言
    MODERATED = "moderated"           # 主持人控制


class MessageScope(Enum):
    """消息范围"""
    ALL = "all"              # 广播给所有人
    AGENT = "agent"          # 发送给指定 Agent


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class BusMessage:
    """总线消息"""
    id: str = ""
    group_id: str = ""
    sender_id: str = ""
    sender_name: str = ""
    scope: str = "all"
    target_id: str = ""              # scope=agent 时的目标 agent_id
    content: str = ""
    msg_type: str = "text"           # text / tool_call / system_notice
    round_number: int = 0
    metadata: dict = field(default_factory=dict)
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "scope": self.scope,
            "target_id": self.target_id,
            "content": self.content,
            "msg_type": self.msg_type,
            "round_number": self.round_number,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class BusEvent:
    """总线事件 — 消息收发时的回调参数"""
    message: BusMessage
    group: GroupConversation
    sender: Agent
    participants: list[GroupParticipant]


# ---------------------------------------------------------------------------
# 回调类型
# ---------------------------------------------------------------------------

MessageCallback = Callable[[BusEvent], None]
"""消息回调 — 当消息被路由时触发。"""


# ---------------------------------------------------------------------------
# 群聊消息总线
# ---------------------------------------------------------------------------

class GroupChatBus:
    """
    群聊消息路由总线。

    职责：
    - 消息广播与定向发送
    - 轮次管理与分发
    - 参与者动态加入/离开
    - 消息历史查询
    """

    def __init__(self, db: Session):
        self.db = db
        self._callbacks: list[MessageCallback] = []
        self._turn_order: dict[str, list[str]] = {}          # group_id -> [agent_id]
        self._current_turn: dict[str, int] = {}              # group_id -> index
        self._strategy: dict[str, TurnStrategy] = {}

    # ------------------------------------------------------------------
    # 回调注册
    # ------------------------------------------------------------------

    def on_message(self, callback: MessageCallback):
        """注册消息回调。"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: MessageCallback):
        """移除消息回调。"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _trigger_callbacks(self, event: BusEvent):
        """触发所有已注册的回调。"""
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception:
                logger.exception("消息回调执行失败")

    # ------------------------------------------------------------------
    # 群组管理
    # ------------------------------------------------------------------

    def create_group(
        self,
        title: str,
        created_by: str,
        topic: str = "",
        mode: str = "discussion",
        turn_strategy: str = "round_robin",
    ) -> GroupConversation:
        """创建群聊会话。"""
        group = GroupConversation(
            title=title,
            topic=topic,
            mode=mode,
            created_by=created_by,
        )
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)

        self._strategy[group.id] = TurnStrategy(turn_strategy)
        self._turn_order[group.id] = []
        self._current_turn[group.id] = 0

        logger.info("群聊已创建: %s (%s)", title, group.id)
        return group

    def archive_group(self, group_id: str) -> bool:
        """归档群聊。"""
        group = self.db.query(GroupConversation).filter(GroupConversation.id == group_id).first()
        if not group:
            return False
        group.status = "archived"
        self.db.commit()
        return True

    # ------------------------------------------------------------------
    # 参与者管理
    # ------------------------------------------------------------------

    def add_participant(self, group_id: str, agent_id: str, role: str = "participant") -> bool:
        """添加参与者。"""
        group = self.db.query(GroupConversation).filter(GroupConversation.id == group_id).first()
        if not group:
            logger.warning("群聊不存在: %s", group_id)
            return False

        existing = (
            self.db.query(GroupParticipant)
            .filter(
                GroupParticipant.group_id == group_id,
                GroupParticipant.agent_id == agent_id,
            )
            .first()
        )
        if existing:
            return True  # 已存在

        participant = GroupParticipant(
            group_id=group_id,
            agent_id=agent_id,
            role=role,
        )
        self.db.add(participant)
        self.db.commit()

        # 更新轮次顺序
        if group_id not in self._turn_order:
            self._turn_order[group_id] = []
        if agent_id not in self._turn_order[group_id]:
            self._turn_order[group_id].append(agent_id)

        logger.info("参与者已加入: %s -> %s", agent_id, group_id)
        return True

    def remove_participant(self, group_id: str, agent_id: str) -> bool:
        """移除参与者。"""
        participant = (
            self.db.query(GroupParticipant)
            .filter(
                GroupParticipant.group_id == group_id,
                GroupParticipant.agent_id == agent_id,
            )
            .first()
        )
        if not participant:
            return False

        self.db.delete(participant)
        self.db.commit()

        if group_id in self._turn_order and agent_id in self._turn_order[group_id]:
            self._turn_order[group_id].remove(agent_id)

        logger.info("参与者已离开: %s -> %s", agent_id, group_id)
        return True

    def get_participants(self, group_id: str) -> list[GroupParticipant]:
        """获取群聊的所有参与者。"""
        return (
            self.db.query(GroupParticipant)
            .filter(GroupParticipant.group_id == group_id)
            .all()
        )

    def get_active_agents(self, group_id: str) -> list[Agent]:
        """获取群聊中的活跃 Agent 列表（按轮次顺序）。"""
        participants = self.get_participants(group_id)
        agent_ids = [p.agent_id for p in participants]
        agents = (
            self.db.query(Agent)
            .filter(Agent.id.in_(agent_ids), Agent.is_active == True)
            .all()
        )
        # 按轮次顺序排序
        order = self._turn_order.get(group_id, [])
        if order:
            agent_map = {a.id: a for a in agents}
            ordered = [agent_map[aid] for aid in order if aid in agent_map]
            remaining = [a for a in agents if a.id not in order]
            return ordered + remaining
        return agents

    # ------------------------------------------------------------------
    # 轮次管理
    # ------------------------------------------------------------------

    def next_turn(self, group_id: str) -> Optional[str]:
        """获取下一个发言的 agent_id。"""
        order = self._turn_order.get(group_id, [])
        if not order:
            # 按数据库顺序
            participants = self.get_participants(group_id)
            order = [p.agent_id for p in participants]
            self._turn_order[group_id] = order

        if not order:
            return None

        idx = self._current_turn.get(group_id, 0)
        agent_id = order[idx % len(order)]
        self._current_turn[group_id] = idx + 1
        return agent_id

    def set_turn_strategy(self, group_id: str, strategy: str):
        """设置轮次策略。"""
        self._strategy[group_id] = TurnStrategy(strategy)

    # ------------------------------------------------------------------
    # 讨论轮次
    # ------------------------------------------------------------------

    def start_round(self, group_id: str, topic: str = "") -> Optional[DiscussionRound]:
        """开始新的讨论轮次。"""
        group = self.db.query(GroupConversation).filter(GroupConversation.id == group_id).first()
        if not group:
            return None

        # 获取当前最大轮次号
        last = (
            self.db.query(DiscussionRound)
            .filter(DiscussionRound.group_id == group_id)
            .order_by(DiscussionRound.round_number.desc())
            .first()
        )
        round_number = (last.round_number + 1) if last else 1

        round_record = DiscussionRound(
            group_id=group_id,
            round_number=round_number,
            topic=topic,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(round_record)
        self.db.commit()
        self.db.refresh(round_record)
        logger.info("讨论轮次开始: #%d - %s", round_number, group_id)
        return round_record

    def end_round(self, round_id: str) -> bool:
        """结束讨论轮次。"""
        round_record = self.db.query(DiscussionRound).filter(DiscussionRound.id == round_id).first()
        if not round_record:
            return False
        round_record.ended_at = datetime.now(timezone.utc)
        self.db.commit()
        return True

    def update_round_summary(self, round_id: str, summary: str):
        """更新讨论轮次的摘要。"""
        round_record = self.db.query(DiscussionRound).filter(DiscussionRound.id == round_id).first()
        if round_record:
            round_record.summary = summary
            self.db.commit()

    # ------------------------------------------------------------------
    # 消息发送与路由
    # ------------------------------------------------------------------

    async def send_message(
        self,
        group_id: str,
        sender_id: str,
        content: str,
        msg_type: str = "text",
        scope: str = "all",
        target_id: str = "",
        metadata: Optional[dict] = None,
    ) -> BusMessage:
        """发送消息到总线。"""
        group = self.db.query(GroupConversation).filter(GroupConversation.id == group_id).first()
        if not group:
            raise ValueError(f"群聊不存在: {group_id}")

        # 系统消息不需要查 Agent 表
        if sender_id == "system" or msg_type == "system_notice":
            sender = None
            sender_name = "系统"
        else:
            sender = self.db.query(Agent).filter(Agent.id == sender_id).first()
            if not sender:
                raise ValueError(f"发送者 Agent 不存在: {sender_id}")
            sender_name = sender.name

        # 获取当前轮次号
        last_round = (
            self.db.query(DiscussionRound)
            .filter(DiscussionRound.group_id == group_id)
            .order_by(DiscussionRound.round_number.desc())
            .first()
        )
        round_number = last_round.round_number if last_round else 0

        # 构造总线消息
        bus_msg = BusMessage(
            id=Message(id=self._gen_id()).id,
            group_id=group_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            msg_type=msg_type,
            scope=scope,
            target_id=target_id,
            round_number=round_number,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        # 保存消息到数据库
        db_message = Message(
            id=bus_msg.id,
            conversation_id="",  # 群聊消息不属于某个单聊对话
            role="assistant",
            type=msg_type,
            content=content,
        )
        self.db.add(db_message)
        self.db.commit()

        # 构造事件并触发回调
        participants = self.get_participants(group_id)
        event = BusEvent(
            message=bus_msg,
            group=group,
            sender=sender,
            participants=participants,
        )
        self._trigger_callbacks(event)

        return bus_msg

    async def broadcast(self, group_id: str, message: str, sender_id: str = "system"):
        """广播系统消息给所有参与者。"""
        return await self.send_message(
            group_id=group_id,
            sender_id=sender_id,
            content=message,
            msg_type="system_notice",
        )

    def send_sync(
        self,
        group_id: str,
        sender_id: str,
        content: str,
        msg_type: str = "text",
        scope: str = "all",
        target_id: str = "",
    ) -> BusMessage:
        """同步发送消息（非协程环境用）。"""
        group = self.db.query(GroupConversation).filter(GroupConversation.id == group_id).first()
        if not group:
            raise ValueError(f"群聊不存在: {group_id}")

        # 系统消息不需要查 Agent 表
        if sender_id == "system" or msg_type == "system_notice":
            sender = None
            sender_name = "系统"
        else:
            sender = self.db.query(Agent).filter(Agent.id == sender_id).first()
            if not sender:
                raise ValueError(f"发送者 Agent 不存在: {sender_id}")
            sender_name = sender.name

        bus_msg = BusMessage(
            group_id=group_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            msg_type=msg_type,
            scope=scope,
            target_id=target_id,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        participants = self.get_participants(group_id)
        event = BusEvent(
            message=bus_msg,
            group=group,
            sender=sender,
            participants=participants,
        )
        self._trigger_callbacks(event)
        return bus_msg

    # ------------------------------------------------------------------
    # 消息查询
    # ------------------------------------------------------------------

    def get_group_messages(
        self,
        group_id: str,
        limit: int = 100,
        before_id: Optional[str] = None,
    ) -> list[Message]:
        """获取群聊消息历史。"""
        group = self.db.query(GroupConversation).filter(GroupConversation.id == group_id).first()
        if not group:
            return []

        # 群聊消息的 conversation_id 为空的 Message
        q = (
            self.db.query(Message)
            .filter(Message.conversation_id == "")
            .order_by(Message.created_at.desc())
        )
        if before_id:
            before_msg = self.db.query(Message).filter(Message.id == before_id).first()
            if before_msg:
                q = q.filter(Message.created_at < before_msg.created_at)

        return q.limit(limit).all()

    def get_round_messages(self, group_id: str, round_number: int) -> list[Message]:
        """获取指定讨论轮次的消息。"""
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == "")
            .order_by(Message.created_at)
            .all()
        )  # 简化实现，实际应关联 round_number

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    @staticmethod
    def _gen_id() -> str:
        import uuid
        return str(uuid.uuid4())

    def cleanup(self):
        """清理总线状态。"""
        self._callbacks.clear()
        self._turn_order.clear()
        self._current_turn.clear()
        self._strategy.clear()
