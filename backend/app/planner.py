"""
Planner — decomposes goals into dependency-aware subtasks via LLM.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Agent, Plan, SubTask
from app.llm_client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)

DECOMPOSE_PROMPT = """你是一个任务规划专家。请将以下用户目标拆解为多个子任务。

要求：
1. 每个子任务应当是独立的、可执行的单元
2. 明确子任务间的依赖关系（用 depends_on 表示前置子任务序号，从 0 开始）
3. 子任务按执行顺序排列（order_index）

以 JSON 格式返回，格式如下：
{
  "title": "计划标题",
  "description": "计划描述",
  "subtasks": [
    {
      "title": "子任务标题",
      "description": "子任务具体描述",
      "depends_on": [],
      "order_index": 0
    }
  ]
}

确保：
- 所有子任务的 depends_on 引用的序号必须存在
- 不存在循环依赖
- 没有依赖的子任务（depends_on=[]）可以并行执行

用户目标："""


class Planner:
    """Decomposes a goal into a Plan with dependency-graph subtasks."""

    def __init__(self, db: Session, api_keys: dict):
        self.db = db
        self.api_keys = api_keys

    async def create_plan(
        self,
        agent: Agent,
        conversation_id: str,
        goal: str,
        context: Optional[str] = None,
    ) -> Plan:
        """Create a Plan from a natural-language goal."""
        llm = LLMClient(LLMConfig(
            provider=agent.model_provider or "openai",
            model=agent.model_name or "gpt-4o",
            temperature=0.3,
            max_tokens=4096,
            api_key=self.api_keys.get(agent.model_provider or "openai", ""),
        ))

        prompt = DECOMPOSE_PROMPT + goal
        if context:
            prompt += f"\n\n额外上下文：\n{context}"

        messages = [
            {"role": "system", "content": "你是一个任务规划专家。只输出 JSON，不要包含其他内容。"},
            {"role": "user", "content": prompt},
        ]

        raw = await llm.complete(messages)
        parsed = self._parse_llm_output(raw)
        if parsed is None:
            logger.error("LLM returned unparseable plan: %s", raw[:200])
            raise ValueError("规划输出解析失败")

        plan = Plan(
            agent_id=agent.id,
            conversation_id=conversation_id,
            title=parsed.get("title", goal[:80]),
            description=parsed.get("description", ""),
            status="pending",
            subtasks_json=json.dumps(parsed.get("subtasks", []), ensure_ascii=False),
        )
        self.db.add(plan)
        self.db.flush()

        # Create SubTask rows
        for st in parsed.get("subtasks", []):
            subtask = SubTask(
                plan_id=plan.id,
                title=st["title"],
                description=st.get("description", ""),
                status="pending",
                depends_on_json=json.dumps(st.get("depends_on", []), ensure_ascii=False),
                order_index=st.get("order_index", 0),
            )
            self.db.add(subtask)

        self.db.commit()
        self.db.refresh(plan)
        logger.info("Created plan %s with %d subtasks", plan.id, len(parsed.get("subtasks", [])))
        return plan

    def get_ready_subtasks(self, plan_id: str) -> list[SubTask]:
        """Return subtasks whose dependencies are all completed."""
        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            return []

        subtasks = (
            self.db.query(SubTask)
            .filter(SubTask.plan_id == plan_id)
            .order_by(SubTask.order_index)
            .all()
        )

        ready: list[SubTask] = []
        for st in subtasks:
            if st.status != "pending":
                continue
            deps = json.loads(st.depends_on_json or "[]")
            if all(self._is_subtask_done(subtasks, d) for d in deps):
                ready.append(st)
        return ready

    def _is_subtask_done(self, subtasks: list[SubTask], index: int) -> bool:
        if index < 0 or index >= len(subtasks):
            return False
        return subtasks[index].status == "completed"

    def _parse_llm_output(self, raw: str) -> Optional[dict]:
        """Extract JSON from LLM output (handles markdown fences)."""
        text = raw.strip()
        if text.startswith("```"):
            # Find the first { or [ after the fence
            start = text.find("{")
            if start == -1:
                return None
            end = text.rfind("}")
            if end == -1:
                return None
            text = text[start : end + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
