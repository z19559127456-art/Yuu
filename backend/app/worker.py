"""
Worker — executes subtasks via LLM, handles tool calls, reports results.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import Agent, SubTask, TaskExecution
from app.llm_client import LLMClient, LLMConfig
from app.context_manager import ContextManager

logger = logging.getLogger(__name__)

WORKER_SYSTEM_PROMPT = """你是一个任务执行专家。你的目标是根据子任务描述，输出高质量的结果。

请专注于以下子任务：
{描述}

任务上下文：
{上下文}

请输出完整、准确的结果。如果任务需要具体代码、配置或文档，请直接给出。"""


class Worker:
    """Executes a single subtask using the configured LLM."""

    def __init__(self, db: Session, api_keys: dict):
        self.db = db
        self.api_keys = api_keys

    async def execute(
        self,
        agent: Agent,
        subtask: SubTask,
        conversation_id: str = "",
        context: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a subtask and return the result."""
        execution = TaskExecution(
            agent_id=agent.id,
            conversation_id=conversation_id or subtask.plan_id,
            plan_id=subtask.plan_id,
            subtask_id=subtask.id,
            task_type="subtask_execution",
            input_json=json.dumps({
                "title": subtask.title,
                "description": subtask.description,
                "context": context or "",
            }, ensure_ascii=False),
            status="running",
            start_time=datetime.now(timezone.utc),
        )
        self.db.add(execution)
        self.db.commit()

        # Mark subtask running
        subtask.status = "running"
        subtask.start_time = datetime.now(timezone.utc)
        self.db.commit()

        try:
            llm = LLMClient(LLMConfig(
                provider=agent.model_provider or "openai",
                model=agent.model_name or "gpt-4o",
                temperature=0.5,
                max_tokens=4096,
                api_key=self.api_keys.get(agent.model_provider or "openai", ""),
            ))

            prompt = WORKER_SYSTEM_PROMPT.format(
                描述=subtask.description or subtask.title,
                上下文=context or "",
            )

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"请执行子任务：{subtask.title}\n\n{subtask.description or ''}"},
            ]

            result_text = await llm.complete(messages)
            result = {
                "output": result_text,
                "subtask_id": subtask.id,
                "title": subtask.title,
            }

            # Update subtask
            subtask.status = "completed"
            subtask.end_time = datetime.now(timezone.utc)
            subtask.result_json = json.dumps(result, ensure_ascii=False)

            # Update execution
            execution.status = "success"
            execution.end_time = datetime.now(timezone.utc)
            execution.duration_ms = int(
                (execution.end_time - execution.start_time).total_seconds() * 1000
            )
            execution.output_json = json.dumps(result, ensure_ascii=False)

            self.db.commit()
            logger.info("Subtask %s completed successfully", subtask.id)
            return result

        except Exception as e:
            logger.exception("Subtask %s execution failed", subtask.id)
            subtask.status = "failed"
            subtask.end_time = datetime.now(timezone.utc)

            execution.status = "failed"
            execution.end_time = datetime.now(timezone.utc)
            execution.error_message = str(e)
            execution.duration_ms = int(
                (execution.end_time - execution.start_time).total_seconds() * 1000
            )
            self.db.commit()
            raise

    async def execute_with_context(
        self,
        agent: Agent,
        subtask: SubTask,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Execute subtask with full conversation context injected."""
        ctx = ContextManager(self.db, self.api_keys)
        context_str = f"Agent: {agent.name}\nRole: {agent.role}\n"
        return await self.execute(agent, subtask, conversation_id, context=context_str)
