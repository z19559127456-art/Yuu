"""
AutoGen-style free dialogue manager — agents freely talk, negotiate, reach consensus.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.llm_client import LLMClient, llm_client_from_agent
from app.models import Agent, GroupConversation
from app.deadlock_detector import DeadlockDetector
from app.security import PermissionChecker, AuditLogger

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class FreeDialogueConfig:
    max_turns: int = 50
    max_tokens: int = 500_000
    consensus_threshold: float = 0.7
    consensus_check_interval: int = 5
    stall_timeout: float = 120.0
    agent_response_timeout: float = 30.0
    enable_consensus_detection: bool = True


@dataclass
class ConsensusResult:
    consensus_reached: bool = False
    summary: str = ""
    dissenting_agents: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "consensus_reached": self.consensus_reached,
            "summary": self.summary,
            "dissenting_agents": self.dissenting_agents,
            "confidence": self.confidence,
        }


@dataclass
class DialogueMessage:
    id: str = ""
    agent_id: str = ""
    agent_name: str = ""
    content: str = ""
    reply_to: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "content": self.content,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# 共识检测器
# ---------------------------------------------------------------------------

CONSENSUS_CHECK_PROMPT = """你是一个对话分析专家。请判断以下多轮对话是否已达成共识。

对话历史：
{历史对话}

请分析：
1. 各参与者的立场是否趋于一致？
2. 是否存在明显的反对意见？
3. 如果有反对意见，是哪些 agent 持不同立场？

以 JSON 格式返回：
{{
  "consensus_reached": true/false,
  "summary": "用一句中文总结当前共识或争议焦点",
  "dissenting_agents": ["agent名字"],
  "confidence": 0.0-1.0
}}
"""


class ConsensusDetector:
    """Analyzes dialogue history to detect when agents reach agreement."""

    def __init__(self, api_keys: dict, check_interval: int = 5):
        self.api_keys = api_keys
        self.check_interval = check_interval
        self._message_count = 0

    def should_check(self) -> bool:
        """Return True every N messages."""
        self._message_count += 1
        return self._message_count % self.check_interval == 0

    async def check(
        self,
        history: list[DialogueMessage],
        provider: str = "openai",
        model: str = "gpt-3.5-turbo",
    ) -> ConsensusResult:
        """Run consensus analysis on recent dialogue history."""
        if len(history) < 3:
            return ConsensusResult()

        history_text = "\n".join(
            f"{m.agent_name}: {m.content[:300]}"
            for m in history[-20:]
        )

        prompt = CONSENSUS_CHECK_PROMPT.format(历史对话=history_text)

        try:
            llm = LLMClient.from_config(
                provider=provider,
                model=model,
                temperature=0.2,
                max_tokens=512,
                api_key=self.api_keys.get(provider, ""),
            )
            raw = await llm.complete([
                {"role": "system", "content": "你是一个对话分析专家。只输出 JSON，不要包含其他内容。"},
                {"role": "user", "content": prompt},
            ])
            return self._parse(raw)
        except Exception as e:
            logger.warning("共识检测 LLM 调用失败: %s", e)
            return ConsensusResult()

    def _parse(self, raw: str) -> ConsensusResult:
        text = raw.strip()
        if text.startswith("```"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start:end + 1]
        try:
            data = json.loads(text)
            return ConsensusResult(
                consensus_reached=data.get("consensus_reached", False),
                summary=data.get("summary", ""),
                dissenting_agents=data.get("dissenting_agents", []),
                confidence=data.get("confidence", 0.0),
            )
        except json.JSONDecodeError:
            logger.warning("共识检测 JSON 解析失败: %s", raw[:100])
            return ConsensusResult()


# ---------------------------------------------------------------------------
# 对话协调器
# ---------------------------------------------------------------------------

class DialogueCoordinator:
    """Manages the flow: who speaks next, context assembly, mention handling."""

    def __init__(self, db: Session, api_keys: dict):
        self.db = db
        self.api_keys = api_keys
        self._pending_replies: dict[str, str] = {}  # agent_id -> mentioned_by

    def record_mention(self, mentioned_name: str, agents: list[Agent]) -> Optional[str]:
        """Record an @mention and return the target agent_id."""
        for a in agents:
            if a.name == mentioned_name:
                self._pending_replies[a.id] = mentioned_name
                return a.id
        return None

    def mark_replied(self, agent_id: str):
        """Clear pending reply status after agent has spoken."""
        self._pending_replies.pop(agent_id, None)

    def select_next_speaker(
        self,
        agents: list[Agent],
        history: list[DialogueMessage],
        topic: str = "",
    ) -> Optional[Agent]:
        """
        Select the next agent to speak.

        Priority:
        1. Agent explicitly @mentioned in the last message
        2. Agent whose role best matches the current discussion topic
        3. Agent who hasn't spoken recently (round-robin fallback)
        """
        if not agents:
            return None

        # Priority 1: Check for @mentions in last message
        if history:
            last_msg = history[-1].content
            for agent in agents:
                if f"@{agent.name}" in last_msg and agent.id not in self._pending_replies:
                    return agent

        # Priority 2: Pending replies from earlier mentions
        for agent in agents:
            if agent.id in self._pending_replies:
                return agent

        # Priority 3: Agent who hasn't spoken in longest time
        spoken_ids = {m.agent_id for m in history}
        for agent in agents:
            if agent.id not in spoken_ids:
                return agent

        # Priority 4: Last spoke longest ago
        last_turn = {}
        for i, m in enumerate(history):
            last_turn[m.agent_id] = i
        ordered = sorted(agents, key=lambda a: last_turn.get(a.id, -1))
        return ordered[0] if ordered else None

    def build_agent_context(
        self,
        agent: Agent,
        topic: str,
        history: list[DialogueMessage],
        all_agents: list[Agent],
    ) -> list[dict]:
        """Build the LLM message list for an agent's turn."""
        other_agents = [a for a in all_agents if a.id != agent.id]
        agent_list = ", ".join(f"{a.name}({a.role or '通用'})" for a in other_agents)

        system_prompt = (
            f"你是 {agent.name}，角色定位: {agent.role or '通用AI助手'}。\n"
            f"你正在参与一个群组对话，对话主题: {topic}。\n"
            f"群内其他成员: {agent_list}。\n\n"
            f"对话规则：\n"
            f"1. 基于你的角色定位发表观点，保持角色一致性\n"
            f"2. 可以参考或回应其他人的发言，用 @名字 来定向回复\n"
            f"3. 如果你同意某人的观点，明确表达支持并补充理由\n"
            f"4. 如果你不同意，礼貌地提出不同意见并给出论据\n"
            f"5. 当讨论趋于一致时，明确表态你认可共识\n"
            f"6. 发言简洁有力，每次控制在 200 字内\n"
            f"{agent.system_prompt or ''}"
        )

        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        # Inject conversation history
        if history:
            history_text = "## 当前对话进展\n\n"
            for m in history[-15:]:
                history_text += f"**{m.agent_name}**: {m.content}\n\n"
            history_text += f"\n请你以 **{agent.name}** 的身份继续参与讨论。"
            messages.append({"role": "user", "content": history_text})
        else:
            messages.append({"role": "user", "content": f"讨论主题: {topic}\n\n请以 {agent.name} 的身份首先发表你的看法。"})

        return messages


# ---------------------------------------------------------------------------
# 自由对话管理器
# ---------------------------------------------------------------------------

class FreeDialogueManager:
    """
    AutoGen-style free dialogue — agents converse freely until consensus.

    Usage:
        mgr = FreeDialogueManager(db, api_keys, group_id, agents, topic)
        mgr.on_message(lambda msg: ws.send(msg))
        await mgr.start()
        await mgr.stop()
    """

    def __init__(
        self,
        db: Session,
        api_keys: dict,
        group_id: str,
        agents: list[Agent],
        topic: str = "",
        config: Optional[FreeDialogueConfig] = None,
    ):
        self.db = db
        self.api_keys = api_keys
        self.group_id = group_id
        self.agents = agents
        self.topic = topic
        self.config = config or FreeDialogueConfig()

        self.coordinator = DialogueCoordinator(db, api_keys)
        self.consensus = ConsensusDetector(
            api_keys,
            check_interval=self.config.consensus_check_interval,
        )
        self.deadlock = DeadlockDetector(
            loop_window=50,
            repeat_threshold=5,
            max_turns=self.config.max_turns,
            max_tokens=self.config.max_tokens,
            max_duration=3600,
            stall_timeout=self.config.stall_timeout,
        )
        self.audit = AuditLogger(db)

        self._history: list[DialogueMessage] = []
        self._running = False
        self._callbacks: list[Callable] = []
        self._turn_count = 0
        self._session_id = self._gen_id()
        self._token_budget = 0

    @property
    def history(self) -> list[DialogueMessage]:
        return list(self._history)

    @property
    def turn_count(self) -> int:
        return self._turn_count

    def on_message(self, callback: Callable):
        """Register a callback receiving (dict) for each agent reply."""
        self._callbacks.append(callback)

    def _emit(self, data: dict):
        for cb in self._callbacks:
            try:
                cb(data)
            except Exception:
                logger.exception("对话回调执行失败")

    async def start(self):
        """Start the free dialogue loop."""
        if self._running:
            return
        self._running = True
        self.deadlock.budget.start_session(self._session_id)
        self.deadlock.stall.start_monitoring(self._session_id)

        logger.info("自由对话开始: group=%s topic=%s agents=%d",
                     self.group_id, self.topic, len(self.agents))

        while self._running and self._turn_count < self.config.max_turns:
            # Deadlock check
            report = self.deadlock.check_all("free_dialogue", self._session_id)
            if report.triggered:
                logger.warning("自由对话死锁触发: %s", report.reason)
                self._emit({
                    "type": "free_dialogue_ended",
                    "group_id": self.group_id,
                    "reason": report.reason,
                    "turns": self._turn_count,
                })
                break

            # Select next speaker
            speaker = self.coordinator.select_next_speaker(
                self.agents, self._history, self.topic,
            )
            if not speaker:
                await asyncio.sleep(0.5)
                continue

            # Permission check
            perm = PermissionChecker.check_agent_active(speaker)
            if not perm.allowed:
                self.audit.log_permission_denied(
                    agent_id=speaker.id,
                    resource_type="group",
                    reason=perm.reason,
                )
                continue

            # Generate reply
            try:
                reply_content = await self._generate_reply(speaker)
            except Exception as e:
                logger.error("Agent %s 发言生成失败: %s", speaker.name, e)
                continue

            if not reply_content.strip():
                continue

            # Record message
            msg = DialogueMessage(
                id=self._gen_id(),
                agent_id=speaker.id,
                agent_name=speaker.name,
                content=reply_content,
                timestamp=datetime.now(timezone.utc).timestamp(),
            )
            self._history.append(msg)
            self._turn_count += 1

            # Update deadlock tracking
            self.deadlock.loop.record(speaker.id, reply_content[:100])
            self.deadlock.budget.record_turn(self._session_id, tokens=len(reply_content))
            self.deadlock.stall.mark_activity(self._session_id)

            # Mark agent as having replied
            self.coordinator.mark_replied(speaker.id)

            # Handle @mentions in the reply
            for a in self.agents:
                if f"@{a.name}" in reply_content and a.id != speaker.id:
                    self.coordinator.record_mention(a.name, self.agents)

            # Emit to callbacks
            self._emit({
                "type": "free_dialogue_message",
                "group_id": self.group_id,
                "agent_id": speaker.id,
                "agent_name": speaker.name,
                "content": reply_content,
                "reply_to": msg.reply_to,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Consensus check
            if self.config.enable_consensus_detection and self.consensus.should_check():
                result = await self.consensus.check(self._history)
                if result.consensus_reached and result.confidence >= self.config.consensus_threshold:
                    logger.info("共识达成: %s", result.summary)
                    self._emit({
                        "type": "consensus_reached",
                        "group_id": self.group_id,
                        "summary": result.summary,
                        "dissenting_agents": result.dissenting_agents,
                    })
                    # Give a final round for dissenting agents
                    if result.dissenting_agents:
                        remaining_rounds = min(2, len(result.dissenting_agents))
                        for _ in range(remaining_rounds):
                            if not self._running:
                                break
                            for agent in self.agents:
                                if agent.name in result.dissenting_agents:
                                    try:
                                        reply = await self._generate_reply(agent)
                                        msg2 = DialogueMessage(
                                            id=self._gen_id(),
                                            agent_id=agent.id,
                                            agent_name=agent.name,
                                            content=reply,
                                            timestamp=datetime.now(timezone.utc).timestamp(),
                                        )
                                        self._history.append(msg2)
                                        self._turn_count += 1
                                        self._emit({
                                            "type": "free_dialogue_message",
                                            "group_id": self.group_id,
                                            "agent_id": agent.id,
                                            "agent_name": agent.name,
                                            "content": reply,
                                            "timestamp": datetime.now(timezone.utc).isoformat(),
                                        })
                                    except Exception as e:
                                        logger.error("异议 agent 发言失败: %s", e)
                    else:
                        break

            # Delay between turns
            await asyncio.sleep(0.3)

        # End dialogue
        self._running = False
        end_reason = "达到最大轮次限制" if self._turn_count >= self.config.max_turns else "对话自然结束"
        self._emit({
            "type": "free_dialogue_ended",
            "group_id": self.group_id,
            "reason": end_reason,
            "turns": self._turn_count,
        })

        logger.info("自由对话结束: group=%s turns=%d", self.group_id, self._turn_count)

    async def stop(self):
        """Gracefully stop the dialogue."""
        self._running = False
        self.deadlock.clear_all(session_id=self._session_id)

    def inject_user_message(self, content: str):
        """Inject a user message into the dialogue context."""
        msg = DialogueMessage(
            id=self._gen_id(),
            agent_id="user",
            agent_name="用户",
            content=content,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )
        self._history.append(msg)
        # Check for @mentions from user
        for agent in self.agents:
            if f"@{agent.name}" in content:
                self.coordinator.record_mention(agent.name, self.agents)

    async def _generate_reply(self, agent: Agent) -> str:
        """Generate an agent's reply using LLM."""
        llm = llm_client_from_agent(agent, self.api_keys)
        messages = self.coordinator.build_agent_context(
            agent, self.topic, self._history, self.agents,
        )

        full = ""
        try:
            # Non-streaming for dialogue to keep it fast
            full = await llm.complete(messages)
        except Exception as e:
            logger.error("LLM 调用失败: %s", e)
            return f"[{agent.name} 暂时无法参与讨论]"

        return full[:2000]

    @staticmethod
    def _gen_id() -> str:
        import uuid
        return str(uuid.uuid4())
