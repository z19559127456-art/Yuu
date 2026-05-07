"""
Conversation context management — builds prompts from history + memory.
"""
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Agent, Message, MemorySummary
from app.llm_client import llm_client_from_agent

logger = logging.getLogger(__name__)


class ContextManager:
    """Builds LLM prompts from conversation history and memory."""

    def __init__(self, db: Session, api_keys: dict):
        self.db = db
        self.api_keys = api_keys

    def build_messages(
        self,
        agent: Agent,
        conversation_id: str,
        current_content: str,
        max_turns: int = 50,
    ) -> list[dict]:
        """
        Build the full message list for an LLM call:
          1. System prompt (agent definition)
          2. L2 memory summaries (if any)
          3. Recent conversation history (up to max_turns)
          4. Current user input
        """
        messages: list[dict] = []

        # 1. System prompt
        system = self._build_system_prompt(agent)
        messages.append({"role": "system", "content": system})

        # 2. L2 memory summaries
        summaries = (
            self.db.query(MemorySummary)
            .filter(MemorySummary.agent_id == agent.id)
            .order_by(MemorySummary.created_at.desc())
            .limit(3)
            .all()
        )
        if summaries:
            summary_text = "\n".join(s.summary_text for s in reversed(summaries))
            messages.append({
                "role": "system",
                "content": f"历史对话摘要：\n{summary_text}",
            })

        # 3. Recent conversation history
        history = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(max_turns)
            .all()
        )
        for msg in reversed(history):
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})
            elif msg.role == "system":
                messages.append({"role": "system", "content": msg.content})

        # 4. Current input
        messages.append({"role": "user", "content": current_content})

        return messages

    def _build_system_prompt(self, agent: Agent) -> str:
        """Build the full system prompt from agent config."""
        parts = [agent.system_prompt or "你是一个有用的AI助手。"]

        # Personality
        try:
            personality = json.loads(agent.personality_json or "{}")
            if personality:
                style = personality.get("style", "")
                tone = personality.get("tone", "")
                verbosity = personality.get("verbosity", "")
                traits = "、".join(filter(None, [style, tone, verbosity]))
                if traits:
                    parts.append(f"\n风格：{traits}")
        except json.JSONDecodeError:
            pass

        # Available tools
        try:
            tools_config = json.loads(agent.tools_config_json or "{}")
            enabled_tools = []
            for tool_name, cfg in tools_config.items():
                if isinstance(cfg, dict) and cfg.get("enabled"):
                    enabled_tools.append(tool_name)
            if enabled_tools:
                parts.append(f"\n可用工具：{', '.join(enabled_tools)}")
        except json.JSONDecodeError:
            pass

        # Skills
        try:
            skills = json.loads(agent.skills_json or "[]")
            if skills:
                parts.append(f"\n可用技能：{', '.join(skills)}")
        except json.JSONDecodeError:
            pass

        parts.append("\n请用中文回复，除非用户要求使用其他语言。")
        return "\n".join(parts)
