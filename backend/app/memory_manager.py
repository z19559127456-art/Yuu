"""
记忆管理 — 三层记忆架构
  L1: 进程内缓存（最近消息）
  L2: 数据库摘要（定期压缩历史）
  L3: 向量记忆（ChromaDB 语义搜索，在 vector_memory.py 中实现）
"""
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Optional
from collections import OrderedDict

from sqlalchemy.orm import Session

from app.models import MemorySummary, Message
from app.llm_client import LLMClient

logger = logging.getLogger(__name__)


class L1Cache:
    """进程内最近消息缓存 — 避免频繁读库。"""

    def __init__(self, max_entries: int = 200):
        self._cache: OrderedDict[str, list[dict]] = OrderedDict()
        self._max = max_entries
        self._lock = threading.Lock()

    def push(self, conversation_id: str, message: dict):
        with self._lock:
            if conversation_id not in self._cache:
                self._cache[conversation_id] = []
            self._cache[conversation_id].append(message)
            # 只保留最近 N 条
            if len(self._cache[conversation_id]) > self._max:
                self._cache[conversation_id] = self._cache[conversation_id][-self._max:]
            self._cache.move_to_end(conversation_id)

    def get(self, conversation_id: str, limit: int = 50) -> list[dict]:
        with self._lock:
            entries = self._cache.get(conversation_id, [])
            return entries[-limit:]

    def clear(self, conversation_id: str | None = None):
        with self._lock:
            if conversation_id:
                self._cache.pop(conversation_id, None)
            else:
                self._cache.clear()

    def invalidate(self, conversation_id: str):
        """标记某对话的缓存为脏（下次读从 DB 拉取）。"""
        with self._lock:
            self._cache.pop(conversation_id, None)


class L2SummaryManager:
    """L2 摘要记忆 — 定期将历史对话压缩为摘要存入 DB。"""

    def __init__(self, db: Session, llm_client: Optional[LLMClient] = None):
        self.db = db
        self.llm = llm_client

    # ------------------------------------------------------------------
    # 创建摘要
    # ------------------------------------------------------------------

    def summarize_conversation(
        self,
        agent_id: str,
        conversation_id: str,
        force: bool = False,
    ) -> Optional[MemorySummary]:
        """将对话中未摘要的消息压缩为一条摘要记录。"""
        # 获取上次摘要之后的未摘要消息
        last_summary = (
            self.db.query(MemorySummary)
            .filter(MemorySummary.agent_id == agent_id)
            .order_by(MemorySummary.created_at.desc())
            .first()
        )

        cutoff = last_summary.created_at if last_summary else datetime(2000, 1, 1, tzinfo=timezone.utc)

        new_messages = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.created_at > cutoff,
                Message.role.in_(["user", "assistant"]),
            )
            .order_by(Message.created_at)
            .all()
        )

        if len(new_messages) < 5 and not force:
            return None  # 消息太少，暂不创建摘要

        # 将消息拼接为文本
        text_parts = []
        for m in new_messages:
            prefix = "用户" if m.role == "user" else "助手"
            text_parts.append(f"{prefix}: {m.content[:200]}")
        raw_text = "\n".join(text_parts)

        # 使用 LLM 生成摘要（如果有），否则用截断方案
        if self.llm:
            summary_text = self._llm_summarize(raw_text)
        else:
            summary_text = self._fallback_summarize(raw_text)

        record = MemorySummary(
            agent_id=agent_id,
            summary_text=summary_text,
            message_count=len(new_messages),
        )
        self.db.add(record)
        self.db.commit()
        logger.info("L2 摘要已创建: agent=%s msgs=%d", agent_id, len(new_messages))
        return record

    def _llm_summarize(self, text: str) -> str:
        try:
            summary = self.llm.complete([
                {"role": "system", "content": "将以下对话浓缩为 3-5 句中文摘要，保留关键事实和决策。"},
                {"role": "user", "content": text[:8000]},
            ])
            return summary
        except Exception as e:
            logger.warning("LLM 摘要失败，使用 fallback: %s", e)
            return self._fallback_summarize(text)

    @staticmethod
    def _fallback_summarize(text: str, max_chars: int = 500) -> str:
        """不用 LLM 的简易截取方案。"""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "…"

    # ------------------------------------------------------------------
    # 查询摘要
    # ------------------------------------------------------------------

    def get_recent_summaries(self, agent_id: str, limit: int = 5) -> list[MemorySummary]:
        return (
            self.db.query(MemorySummary)
            .filter(MemorySummary.agent_id == agent_id)
            .order_by(MemorySummary.created_at.desc())
            .limit(limit)
            .all()
        )

    def build_summary_context(self, agent_id: str, max_summaries: int = 3) -> str:
        """构建摘要上下文文本，供 system prompt 注入。"""
        summaries = self.get_recent_summaries(agent_id, max_summaries)
        if not summaries:
            return ""
        parts = ["以下是该 Agent 的历史对话摘要："]
        for s in reversed(summaries):
            parts.append(f"- [{s.created_at.strftime('%m-%d %H:%M')}] {s.summary_text}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
l1_cache = L1Cache()
