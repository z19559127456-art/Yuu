"""
Task Dispatcher — decomposes complex tasks and dispatches subtasks to
the most suitable agents based on roles, skills, and capabilities.
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.models import Agent, Plan, SubTask, TaskExecution, GroupConversation
from app.planner import Planner
from app.worker import Worker
from app.critic import Critic
from app.orchestrator import Orchestrator, PWCProgressCallback, PWCState
from app.llm_client import LLMClient, llm_client_from_agent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

class DispatchStrategy(str, Enum):
    ROLE_MATCH = "role_match"
    CAPABILITY_SCORE = "capability_score"
    LOAD_BALANCED = "load_balanced"
    ROUND_ROBIN = "round_robin"


@dataclass
class AgentCapabilityProfile:
    """Capability signature extracted from an Agent."""
    agent_id: str = ""
    agent_name: str = ""
    role: str = ""
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    personality_style: str = ""
    personality_tone: str = ""

    def to_text(self) -> str:
        skills_str = ", ".join(self.skills) if self.skills else "无"
        tools_str = ", ".join(self.tools) if self.tools else "无"
        return (
            f"- {self.agent_name} (ID: {self.agent_id})\n"
            f"  角色: {self.role or '通用'}\n"
            f"  技能: {skills_str}\n"
            f"  可用工具: {tools_str}\n"
            f"  风格: {self.personality_style or '严谨'}/{self.personality_tone or '专业'}"
        )

    @classmethod
    def from_agent(cls, agent: Agent) -> "AgentCapabilityProfile":
        try:
            personality = json.loads(agent.personality_json or '{"style":"严谨","tone":"专业","verbosity":"concise"}')
        except (json.JSONDecodeError, TypeError):
            personality = {"style": "严谨", "tone": "专业"}

        try:
            tools_config = json.loads(agent.tools_config_json or "{}")
            enabled_tools = [k for k, v in tools_config.items()
                           if isinstance(v, dict) and v.get("enabled")]
        except (json.JSONDecodeError, TypeError):
            enabled_tools = []

        try:
            skills = json.loads(agent.skills_json or "[]")
        except (json.JSONDecodeError, TypeError):
            skills = []

        return cls(
            agent_id=agent.id,
            agent_name=agent.name,
            role=agent.role or "",
            skills=skills,
            tools=enabled_tools,
            provider=agent.model_provider or "openai",
            model=agent.model_name or "gpt-4o",
            personality_style=personality.get("style", "严谨"),
            personality_tone=personality.get("tone", "专业"),
        )


# ---------------------------------------------------------------------------
# 任务派发器
# ---------------------------------------------------------------------------

ASSIGN_PROMPT = """你是一个任务分配专家。请根据子任务的需求，从可用 Agent 中选择最合适的一个来执行。

**子任务**：
标题: {任务标题}
描述: {任务描述}

**可用 Agent**：
{Agent列表}

**请分析**：
1. 每个 Agent 的角色、技能、工具是否匹配子任务需求
2. 谁最适合执行这个子任务

以 JSON 格式返回：
{{
  "assigned_agent_id": "选中的 agent_id",
  "reason": "为什么选择这个 Agent（一句话）",
  "confidence": 0.0-1.0
}}
"""

MERGE_PROMPT = """你是一个任务合成专家。请根据所有子任务的执行结果，生成一个综合的最终输出。

**原始目标**：{目标}

**各子任务结果**：
{子任务结果}

请将所有结果整合为一个连贯的最终输出，使用 markdown 格式组织。"""


class TaskDispatcher:
    """
    Decomposes complex tasks, assigns subtasks to agents, and orchestrates execution.

    Usage:
        dispatcher = TaskDispatcher(db, api_keys, available_agents)
        plan = await dispatcher.decompose_and_dispatch(goal, context)
        result = await dispatcher.execute_plan(plan, main_agent)
    """

    def __init__(
        self,
        db: Session,
        api_keys: dict,
        available_agents: Optional[list[Agent]] = None,
        strategy: DispatchStrategy = DispatchStrategy.CAPABILITY_SCORE,
    ):
        self.db = db
        self.api_keys = api_keys
        self.available_agents = available_agents or []
        self.strategy = strategy
        self._callbacks: list[Callable] = []

    def on_progress(self, callback: Callable):
        """Register a callback receiving progress events as dict."""
        self._callbacks.append(callback)

    def _emit(self, data: dict):
        for cb in self._callbacks:
            try:
                cb(data)
            except Exception:
                logger.exception("Progress callback failed")

    async def decompose_and_dispatch(
        self,
        agent: Agent,
        goal: str,
        context: str = "",
        conversation_id: str = "",
    ) -> Plan:
        """
        Decompose a goal into subtasks and assign each to the best agent.

        Steps:
        1. Use Planner to decompose the goal
        2. For each subtask, run agent-assignment LLM call
        3. Set subtask.assigned_agent_id
        """
        profiles = [AgentCapabilityProfile.from_agent(a) for a in self.available_agents]

        # Step 1: Decompose (use enhanced prompt with agent info)
        planner = Planner(self.db, self.api_keys)
        agent_context = "\n".join(p.to_text() for p in profiles)

        enhanced_context = f"可用 Agent 列表：\n{agent_context}\n\n{context}" if context else f"可用 Agent 列表：\n{agent_context}"

        plan = await planner.create_plan(agent, conversation_id, goal, enhanced_context)

        # Step 2: Assign each subtask
        subtasks = (
            self.db.query(SubTask)
            .filter(SubTask.plan_id == plan.id)
            .order_by(SubTask.order_index)
            .all()
        )

        for subtask in subtasks:
            if self.strategy == DispatchStrategy.ROUND_ROBIN:
                # Round-robin: just cycle through agents
                idx = subtask.order_index % len(self.available_agents)
                subtask.assigned_agent_id = self.available_agents[idx].id
            else:
                # CAPABILITY_SCORE or ROLE_MATCH: use LLM
                assigned_id = await self._assign_agent(subtask, profiles)
                if assigned_id:
                    subtask.assigned_agent_id = assigned_id

        self.db.commit()

        # Emit decomposed plan
        self._emit({
            "type": "plan_decomposed",
            "plan": plan.to_dict(),
        })

        logger.info("Plan decomposed: %s with %d subtasks, %d agents",
                     plan.id, len(subtasks), len(self.available_agents))
        return plan

    async def _assign_agent(
        self,
        subtask: SubTask,
        profiles: list[AgentCapabilityProfile],
    ) -> Optional[str]:
        """Use LLM to assign the best agent for a subtask."""
        if not profiles:
            return None
        if len(profiles) == 1:
            return profiles[0].agent_id

        agent_list = "\n\n".join(p.to_text() for p in profiles)
        prompt = ASSIGN_PROMPT.format(
            任务标题=subtask.title,
            任务描述=subtask.description or subtask.title,
            Agent列表=agent_list,
        )

        try:
            # Use a lightweight model for assignment
            llm = LLMClient.from_config(
                provider="openai",
                model="gpt-3.5-turbo",
                temperature=0.2,
                max_tokens=512,
                api_key=self.api_keys.get("openai", ""),
            )
            raw = await llm.complete([
                {"role": "system", "content": "你是一个任务分配专家。只输出 JSON，不要包含其他内容。"},
                {"role": "user", "content": prompt},
            ])
            return self._parse_assignment(raw, profiles)
        except Exception as e:
            logger.warning("Agent assignment failed, falling back to round-robin: %s", e)
            idx = subtask.order_index % len(profiles)
            return profiles[idx].agent_id

    def _parse_assignment(self, raw: str, profiles: list[AgentCapabilityProfile]) -> Optional[str]:
        text = raw.strip()
        if text.startswith("```"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start:end + 1]
        try:
            data = json.loads(text)
            agent_id = data.get("assigned_agent_id", "")
            # Validate the agent_id is in our profiles
            valid_ids = {p.agent_id for p in profiles}
            if agent_id in valid_ids:
                return agent_id
        except json.JSONDecodeError:
            pass
        return None

    async def execute_plan(
        self,
        plan: Plan,
        main_agent: Agent,
        conversation_id: str = "",
    ) -> dict:
        """
        Execute a plan using assigned agents for each subtask.

        Uses the Orchestrator's PWC cycle but with per-subtask agent assignments.
        """
        orchestrator = Orchestrator(
            db=self.db,
            api_keys=self.api_keys,
            max_concurrent=5,
            max_retries_per_subtask=2,
        )

        # Set progress callback to forward events
        orchestrator.set_callback(_DispatchProgressCallback(self))

        try:
            result = await orchestrator.run(
                agent=main_agent,
                conversation_id=conversation_id,
                goal=plan.title,
                context=plan.description or "",
            )

            # Merge results
            merged = await self.merge_results(plan.id)
            self._emit({
                "type": "plan_merged_result",
                "plan_id": plan.id,
                "merged_output": merged.get("merged_output", ""),
                "summary": merged.get("summary", ""),
            })

            return merged
        except Exception as e:
            logger.exception("Plan execution failed")
            raise

    async def merge_results(self, plan_id: str) -> dict:
        """Collect all subtask results and synthesize using LLM."""
        subtasks = (
            self.db.query(SubTask)
            .filter(SubTask.plan_id == plan_id)
            .order_by(SubTask.order_index)
            .all()
        )

        results_text = ""
        for st in subtasks:
            try:
                result = json.loads(st.result_json or "{}")
                output = result.get("output", "")[:1000]
            except json.JSONDecodeError:
                output = str(st.result_json)[:1000]

            agent_info = ""
            if st.assigned_agent_id:
                agent = self.db.query(Agent).filter(Agent.id == st.assigned_agent_id).first()
                if agent:
                    agent_info = f" (执行者: {agent.name})"

            results_text += f"## {st.title}{agent_info}\n\n{output}\n\n"

        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        goal = plan.title if plan else ""

        prompt = MERGE_PROMPT.format(目标=goal, 子任务结果=results_text)

        try:
            llm = LLMClient.from_config(
                provider="openai",
                model="gpt-4o",
                temperature=0.3,
                max_tokens=4096,
                api_key=self.api_keys.get("openai", ""),
            )
            raw = await llm.complete([
                {"role": "system", "content": "你是一个任务合成专家。请用 markdown 格式输出最终结果。"},
                {"role": "user", "content": prompt},
            ])

            return {
                "merged_output": raw,
                "summary": f"成功完成 {sum(1 for st in subtasks if st.status == 'completed')}/{len(subtasks)} 个子任务",
            }
        except Exception as e:
            logger.warning("Merge failed: %s", e)
            return {
                "merged_output": results_text,
                "summary": f"结果合并失败: {e}",
            }


# ---------------------------------------------------------------------------
# Orchestrator 进度回调
# ---------------------------------------------------------------------------

class _DispatchProgressCallback(PWCProgressCallback):
    """Converts PWC progress events to task dispatch events."""

    def __init__(self, dispatcher: TaskDispatcher):
        self.dispatcher = dispatcher

    def on_state_change(self, state: PWCState, plan_id: str, **kwargs):
        self.dispatcher._emit({
            "type": "plan_progress",
            "plan_id": plan_id,
            "state": state.value,
        })

    def on_subtask_start(self, subtask: SubTask):
        self.dispatcher._emit({
            "type": "subtask_started",
            "subtask_id": subtask.id,
            "assigned_agent_id": subtask.assigned_agent_id or "",
            "agent_name": "",
        })

    def on_subtask_complete(self, subtask: SubTask, result: dict, review=None):
        self.dispatcher._emit({
            "type": "subtask_completed",
            "subtask_id": subtask.id,
            "result": result,
        })

    def on_subtask_retry(self, subtask: SubTask, attempt: int, reason: str):
        pass

    def on_error(self, error: str):
        self.dispatcher._emit({
            "type": "subtask_failed",
            "subtask_id": "",
            "error": error,
        })

    def on_complete(self, result):
        self.dispatcher._emit({
            "type": "plan_progress",
            "plan_id": result.to_dict().get("plan_id", ""),
            "state": "completed",
        })
