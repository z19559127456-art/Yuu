"""
SQLAlchemy ORM models — Agent, Conversation, Message, TaskRecord, MemorySummary
"""
import uuid
import json
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Float, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(128), nullable=False)
    avatar = Column(String(256), default="")
    role = Column(String(256), default="")
    system_prompt = Column(Text, default="")

    # LLM config
    model_provider = Column(String(32), default="openai")
    model_name = Column(String(128), default="gpt-4o")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    api_base_url = Column(String(512), default="")
    api_key = Column(String(256), default="")

    # Personality (JSON string)
    personality_json = Column(Text, default='{"style":"严谨","tone":"专业","verbosity":"concise"}')

    # Tools config (JSON string)
    tools_config_json = Column(Text, default=json.dumps({
        "cli": {"enabled": False, "allowed_commands": [], "blocked_commands": []},
        "web": {"enabled": False, "max_pages": 10, "allowed_domains": [], "blocked_domains": []},
        "ui_automation": {"enabled": False},
        "vision": {"enabled": False},
    }))

    # Skills (JSON string — list of skill names)
    skills_json = Column(Text, default="[]")

    # Memory config (JSON string)
    memory_config_json = Column(Text, default=json.dumps({
        "mode": "persistent",
        "max_history_turns": 100,
        "summary_threshold": 50,
    }))

    # Concurrency config (JSON string)
    concurrency_config_json = Column(Text, default=json.dumps({
        "max_parallel_tasks": 3,
        "queue_strategy": "fifo",
    }))

    is_active = Column(Boolean, default=True)
    tags_json = Column(Text, default="[]")

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    conversations = relationship(
        "Conversation", back_populates="agent", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "avatar": self.avatar or "",
            "role": self.role or "",
            "system_prompt": self.system_prompt or "",
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_base_url": self.api_base_url or "",
            "api_key": self.api_key or "",
            "personality": json.loads(self.personality_json or "{}"),
            "tools_config": json.loads(self.tools_config_json or "{}"),
            "skills": json.loads(self.skills_json or "[]"),
            "memory_config": json.loads(self.memory_config_json or "{}"),
            "concurrency_config": json.loads(self.concurrency_config_json or "{}"),
            "is_active": bool(self.is_active),
            "tags": json.loads(self.tags_json or "[]"),
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    title = Column(String(256), default="新对话")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    agent = relationship("Agent", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "title": self.title or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    group_id = Column(String, nullable=True, default=None)  # 群聊消息关联的群组 ID
    role = Column(String(16), nullable=False)  # 'user' | 'assistant' | 'system' | 'tool'
    type = Column(String(32), default="text")  # 'text' | 'tool_call' | 'tool_result' | 'error' | 'system_notice'
    content = Column(Text, nullable=False)
    content_html = Column(Text, default="")
    attachments_json = Column(Text, default="[]")
    tool_calls_json = Column(Text, default="[]")
    tool_results_json = Column(Text, default="[]")
    reply_to = Column(String, default="")
    is_edited = Column(Boolean, default=False)
    edited_from = Column(String, default="")
    is_pinned = Column(Boolean, default=False)
    is_remembered = Column(Boolean, default=False)
    status = Column(String(16), default="sent")  # 'sending' | 'sent' | 'failed' | 'cancelled'
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "group_id": self.group_id or "",
            "role": self.role,
            "type": self.type or "text",
            "content": self.content,
            "content_html": self.content_html or "",
            "attachments": json.loads(self.attachments_json or "[]"),
            "tool_calls": json.loads(self.tool_calls_json or "[]"),
            "tool_results": json.loads(self.tool_results_json or "[]"),
            "reply_to": self.reply_to or "",
            "is_edited": bool(self.is_edited),
            "edited_from": self.edited_from or "",
            "is_pinned": bool(self.is_pinned),
            "is_remembered": bool(self.is_remembered),
            "status": self.status or "sent",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class TaskRecord(Base):
    __tablename__ = "task_records"

    id = Column(String, primary_key=True, default=_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    task_type = Column(String(64), nullable=False)
    input_json = Column(Text, default="{}")
    output_json = Column(Text, default="{}")
    status = Column(String(16), default="running")  # 'success' | 'failed' | 'partial' | 'cancelled'
    error_message = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    token_usage_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=_utcnow)


class MemorySummary(Base):
    __tablename__ = "memory_summaries"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    summary_text = Column(Text, nullable=False)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)


# ---------------------------------------------------------------------------
# 对话框 A 新增模型
# ---------------------------------------------------------------------------

class WebRecord(Base):
    """Web 工具执行结果"""
    __tablename__ = "web_records"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    url = Column(String(2048), nullable=False)
    action = Column(String(32), nullable=False)  # navigate / click / extract / screenshot
    input_json = Column(Text, default="{}")
    output_json = Column(Text, default="{}")
    status = Column(String(16), default="running")  # running / success / failed
    error_message = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id or "",
            "url": self.url,
            "action": self.action,
            "input": json.loads(self.input_json or "{}"),
            "output": json.loads(self.output_json or "{}"),
            "status": self.status or "running",
            "error_message": self.error_message or "",
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class UIRecord(Base):
    """UI 工具执行结果"""
    __tablename__ = "ui_records"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    action = Column(String(32), nullable=False)  # click / type / screenshot / locate
    target_element = Column(String(512), default="")
    input_json = Column(Text, default="{}")
    output_json = Column(Text, default="{}")
    status = Column(String(16), default="running")
    error_message = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id or "",
            "action": self.action,
            "target_element": self.target_element or "",
            "input": json.loads(self.input_json or "{}"),
            "output": json.loads(self.output_json or "{}"),
            "status": self.status or "running",
            "error_message": self.error_message or "",
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class VisionRecord(Base):
    """Vision 工具执行结果"""
    __tablename__ = "vision_records"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    image_source = Column(String(32), default="screenshot")  # screenshot / upload / url
    prompt = Column(Text, default="")
    result_text = Column(Text, default="")
    status = Column(String(16), default="running")
    error_message = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id or "",
            "image_source": self.image_source or "screenshot",
            "prompt": self.prompt or "",
            "result_text": self.result_text or "",
            "status": self.status or "running",
            "error_message": self.error_message or "",
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class Plan(Base):
    """任务计划"""
    __tablename__ = "plans"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, default="")
    status = Column(String(16), default="pending")  # pending / running / completed / failed / cancelled
    subtasks_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id or "",
            "title": self.title,
            "description": self.description or "",
            "status": self.status or "pending",
            "subtasks": json.loads(self.subtasks_json or "[]"),
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class SubTask(Base):
    """子任务"""
    __tablename__ = "subtasks"

    id = Column(String, primary_key=True, default=_uuid)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    title = Column(String(256), nullable=False)
    description = Column(Text, default="")
    status = Column(String(16), default="pending")  # pending / running / completed / failed / skipped
    depends_on_json = Column(Text, default="[]")
    result_json = Column(Text, default="{}")
    assigned_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    order_index = Column(Integer, default=0)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "title": self.title,
            "description": self.description or "",
            "status": self.status or "pending",
            "depends_on": json.loads(self.depends_on_json or "[]"),
            "result": json.loads(self.result_json or "{}"),
            "assigned_agent_id": self.assigned_agent_id or "",
            "order_index": self.order_index,
            "start_time": self.start_time.isoformat() if self.start_time else "",
            "end_time": self.end_time.isoformat() if self.end_time else "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class TaskExecution(Base):
    """任务执行记录"""
    __tablename__ = "task_executions"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=True)
    subtask_id = Column(String, ForeignKey("subtasks.id"), nullable=True)
    task_type = Column(String(64), nullable=False)
    input_json = Column(Text, default="{}")
    output_json = Column(Text, default="{}")
    status = Column(String(16), default="running")  # running / success / failed / cancelled
    error_message = Column(Text, default="")
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id or "",
            "plan_id": self.plan_id or "",
            "subtask_id": self.subtask_id or "",
            "task_type": self.task_type,
            "input": json.loads(self.input_json or "{}"),
            "output": json.loads(self.output_json or "{}"),
            "status": self.status or "running",
            "error_message": self.error_message or "",
            "start_time": self.start_time.isoformat() if self.start_time else "",
            "end_time": self.end_time.isoformat() if self.end_time else "",
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class SkillRecord(Base):
    """技能调用记录"""
    __tablename__ = "skill_records"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    skill_name = Column(String(128), nullable=False)
    input_json = Column(Text, default="{}")
    output_json = Column(Text, default="{}")
    status = Column(String(16), default="running")  # running / success / failed
    error_message = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id or "",
            "skill_name": self.skill_name,
            "input": json.loads(self.input_json or "{}"),
            "output": json.loads(self.output_json or "{}"),
            "status": self.status or "running",
            "error_message": self.error_message or "",
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class VectorMemoryEntry(Base):
    """向量记忆索引记录"""
    __tablename__ = "vector_memory_entries"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    chunk_id = Column(String(256), nullable=False, index=True)  # ChromaDB document ID
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": json.loads(self.metadata_json or "{}"),
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class GroupConversation(Base):
    """群聊会话"""
    __tablename__ = "group_conversations"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(256), nullable=False)
    topic = Column(Text, default="")
    mode = Column(String(16), default="discussion")  # task / discussion
    status = Column(String(16), default="active")  # active / archived
    created_by = Column(String, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "topic": self.topic or "",
            "mode": self.mode or "discussion",
            "status": self.status or "active",
            "created_by": self.created_by or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class GroupParticipant(Base):
    """群聊参与者"""
    __tablename__ = "group_participants"

    id = Column(String, primary_key=True, default=_uuid)
    group_id = Column(String, ForeignKey("group_conversations.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    role = Column(String(16), default="participant")  # moderator / participant / observer
    joined_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "agent_id": self.agent_id,
            "role": self.role or "participant",
            "joined_at": self.joined_at.isoformat() if self.joined_at else "",
        }


class DiscussionRound(Base):
    """讨论轮次记录"""
    __tablename__ = "discussion_rounds"

    id = Column(String, primary_key=True, default=_uuid)
    group_id = Column(String, ForeignKey("group_conversations.id"), nullable=False)
    round_number = Column(Integer, nullable=False, default=1)
    topic = Column(Text, default="")
    summary = Column(Text, default="")
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "round_number": self.round_number,
            "topic": self.topic or "",
            "summary": self.summary or "",
            "started_at": self.started_at.isoformat() if self.started_at else "",
            "ended_at": self.ended_at.isoformat() if self.ended_at else "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class ApprovalRecord(Base):
    """人工审批记录 — Human-in-the-loop 审批审计追踪"""
    __tablename__ = "approval_records"

    id = Column(String, primary_key=True, default=_uuid)
    request_id = Column(String(256), nullable=False, index=True)
    group_id = Column(String, ForeignKey("group_conversations.id"), nullable=True)
    approval_type = Column(String(32), nullable=False)  # tool_execution / plan_approval / final_result / dangerous_action
    requester = Column(String(128), default="")
    context_json = Column(Text, default="{}")
    response = Column(String(16), default="pending")  # pending / approved / rejected / modified / timeout
    user_feedback = Column(Text, default="")
    modified_params_json = Column(Text, default="{}")
    timeout_seconds = Column(Integer, default=60)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "group_id": self.group_id or "",
            "approval_type": self.approval_type,
            "requester": self.requester,
            "context": json.loads(self.context_json or "{}"),
            "response": self.response,
            "user_feedback": self.user_feedback or "",
            "modified_params": json.loads(self.modified_params_json or "{}"),
            "timeout_seconds": self.timeout_seconds,
            "responded_at": self.responded_at.isoformat() if self.responded_at else "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class AuditLog(Base):
    """安全审计日志"""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    action = Column(String(64), nullable=False)  # tool_call / config_change / skill_invoke / permission_denied
    resource_type = Column(String(64), default="")  # web / ui / vision / skill / agent / config
    resource_id = Column(String(256), default="")
    details_json = Column(Text, default="{}")
    ip_address = Column(String(45), default="")
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id or "",
            "action": self.action,
            "resource_type": self.resource_type or "",
            "resource_id": self.resource_id or "",
            "details": json.loads(self.details_json or "{}"),
            "ip_address": self.ip_address or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
