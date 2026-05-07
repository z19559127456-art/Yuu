"""
Orchestrator — Plan → Work → Critic state machine with concurrency control.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.models import Agent, Plan, SubTask, TaskExecution
from app.planner import Planner
from app.worker import Worker
from app.critic import Critic, ReviewResult
from app.concurrency import TaskQueue, RetryHandler, Priority

logger = logging.getLogger(__name__)


class PWCState(Enum):
    """Plan-Work-Critic cycle states."""
    IDLE = "idle"
    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    DISPATCHING = "dispatching"
    WORKING = "working"
    REVIEWING = "reviewing"
    REVISING = "revising"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PWCEvent(str, Enum):
    """Events that trigger state transitions."""
    START = "start"
    PLAN_CREATED = "plan_created"
    SUBTASK_DONE = "subtask_done"
    REVIEW_PASSED = "review_passed"
    REVIEW_FAILED = "review_failed"
    ALL_DONE = "all_done"
    ERROR = "error"
    CANCEL = "cancel"


TRANSITIONS: dict[PWCState, dict[PWCEvent, PWCState]] = {
    PWCState.IDLE: {PWCEvent.START: PWCState.PLANNING},
    PWCState.PLANNING: {PWCEvent.PLAN_CREATED: PWCState.PLAN_READY, PWCEvent.ERROR: PWCState.FAILED},
    PWCState.PLAN_READY: {PWCEvent.START: PWCState.DISPATCHING},
    PWCState.DISPATCHING: {PWCEvent.SUBTASK_DONE: PWCState.REVIEWING, PWCEvent.ERROR: PWCState.FAILED},
    PWCState.WORKING: {PWCEvent.SUBTASK_DONE: PWCState.REVIEWING, PWCEvent.ERROR: PWCState.FAILED},
    PWCState.REVIEWING: {
        PWCEvent.REVIEW_PASSED: PWCState.DISPATCHING,
        PWCEvent.REVIEW_FAILED: PWCState.REVISING,
        PWCEvent.ALL_DONE: PWCState.COMPLETED,
        PWCEvent.ERROR: PWCState.FAILED,
    },
    PWCState.REVISING: {PWCEvent.START: PWCState.DISPATCHING, PWCEvent.ERROR: PWCState.FAILED},
    PWCState.COMPLETED: {},
    PWCState.FAILED: {},
    PWCState.CANCELLED: {},
}


class PWCError(Exception):
    """Orchestrator-level error."""
    pass


class PWCResult:
    """Result of a full PWC cycle."""

    def __init__(self):
        self.plan: Optional[Plan] = None
        self.state: PWCState = PWCState.IDLE
        self.subtask_results: dict[str, dict] = {}
        self.review_results: dict[str, ReviewResult] = {}
        self.retry_counts: dict[str, int] = {}
        self.error: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan.id if self.plan else "",
            "state": self.state.value,
            "subtask_results": self.subtask_results,
            "reviews": {
                sid: r.to_dict() for sid, r in self.review_results.items()
            },
            "retry_counts": self.retry_counts,
            "error": self.error or "",
            "start_time": self.start_time.isoformat() if self.start_time else "",
            "end_time": self.end_time.isoformat() if self.end_time else "",
        }


class PWCProgressCallback:
    """Callback interface for progress updates during PWC cycles."""

    def on_state_change(self, state: PWCState, plan_id: str, **kwargs):
        pass

    def on_subtask_start(self, subtask: SubTask):
        pass

    def on_subtask_complete(self, subtask: SubTask, result: dict, review: Optional[ReviewResult] = None):
        pass

    def on_subtask_retry(self, subtask: SubTask, attempt: int, reason: str):
        pass

    def on_error(self, error: str):
        pass

    def on_complete(self, result: PWCResult):
        pass


class Orchestrator:
    """
    Plan-Work-Critic state machine.

    Coordinates the full lifecycle:
      1. Plan  — decompose goal into subtasks (Planner)
      2. Work  — execute ready subtasks via LLM (Worker)
      3. Critic — validate output quality (Critic)
    """

    def __init__(
        self,
        db: Session,
        api_keys: dict,
        max_concurrent: int = 5,
        max_retries_per_subtask: int = 2,
    ):
        self.db = db
        self.api_keys = api_keys
        self.max_retries_per_subtask = max_retries_per_subtask

        self.planner = Planner(db, api_keys)
        self.worker = Worker(db, api_keys)
        self.critic = Critic(db, api_keys)
        self.task_queue = TaskQueue(max_concurrent=max_concurrent)
        self.retry_handler = RetryHandler(max_retries=2)

        self._state: PWCState = PWCState.IDLE
        self._result = PWCResult()
        self._callback: Optional[PWCProgressCallback] = None
        self._running = False

    @property
    def state(self) -> PWCState:
        return self._state

    @property
    def result(self) -> PWCResult:
        return self._result

    def set_callback(self, callback: PWCProgressCallback):
        """Set a progress callback for lifecycle events."""
        self._callback = callback

    def _transition(self, event: PWCEvent, **kwargs):
        """Attempt a state transition."""
        current = self._state
        targets = TRANSITIONS.get(current, {})
        if event not in targets:
            logger.warning("Invalid transition %s from %s", event.value, current.value)
            raise PWCError(f"不能从 {current.value} 状态进行 {event.value} 转换")

        next_state = targets[event]
        logger.info("PWC: %s --[%s]--> %s", current.value, event.value, next_state.value)
        self._state = next_state

        if self._callback:
            self._callback.on_state_change(next_state, self._result.plan.id if self._result.plan else "", **kwargs)

    async def run(
        self,
        agent: Agent,
        conversation_id: str,
        goal: str,
        context: Optional[str] = None,
    ) -> PWCResult:
        """Run a full PWC cycle for a given goal."""
        if self._running:
            raise PWCError("Orchestrator is already running")
        self._running = True
        self._result = PWCResult()
        self._result.start_time = datetime.now(timezone.utc)

        try:
            await self.task_queue.start(worker_count=2)

            # Phase 1: Plan
            await self._phase_plan(agent, conversation_id, goal, context)

            # Phase 2 & 3: Work + Critic (interleaved)
            await self._phase_execute(agent, conversation_id)

            self._transition(PWCEvent.ALL_DONE)
        except Exception as e:
            logger.exception("PWC cycle failed")
            self._result.error = str(e)
            try:
                self._transition(PWCEvent.ERROR)
            except PWCError:
                self._state = PWCState.FAILED
            if self._callback:
                self._callback.on_error(str(e))

        self._result.end_time = datetime.now(timezone.utc)
        self._running = False

        if self._callback:
            self._callback.on_complete(self._result)

        await self.task_queue.stop(wait=False)
        return self._result

    async def cancel(self):
        """Cancel the running PWC cycle."""
        if self._state in (PWCState.COMPLETED, PWCState.FAILED, PWCState.CANCELLED):
            return
        self._state = PWCState.CANCELLED
        self._result.end_time = datetime.now(timezone.utc)
        self._running = False
        await self.task_queue.stop(wait=False)

    # ------------------------------------------------------------------
    # Phase 1: Plan
    # ------------------------------------------------------------------

    async def _phase_plan(
        self,
        agent: Agent,
        conversation_id: str,
        goal: str,
        context: Optional[str] = None,
    ):
        self._transition(PWCEvent.START)

        plan = await self.planner.create_plan(agent, conversation_id, goal, context)
        self._result.plan = plan

        self._transition(PWCEvent.PLAN_CREATED)

    # ------------------------------------------------------------------
    # Phase 2 & 3: Work + Critic (interleaved via task queue)
    # ------------------------------------------------------------------

    async def _phase_execute(self, agent: Agent, conversation_id: str):
        self._transition(PWCEvent.START)

        plan = self._result.plan
        if not plan:
            raise PWCError("没有可执行的计划")

        while True:
            # Check cancellation
            if self._state == PWCState.CANCELLED:
                return

            # Check completion
            plan_status = self._get_plan_status(plan.id)
            if plan_status == "completed":
                return

            # Get ready subtasks
            ready = self.planner.get_ready_subtasks(plan.id)
            if not ready:
                # If nothing ready and nothing running, something is stuck
                running = self._count_running_subtasks(plan.id)
                if running == 0:
                    failed = self._count_failed_subtasks(plan.id)
                    if failed > 0:
                        self._result.error = f"{failed} 个子任务失败，无法继续"
                        self._transition(PWCEvent.ERROR)
                        return
                    if self.task_queue.running_count == 0:
                        # All done
                        return
                await self._wait(0.5)
                continue

            # Dispatch ready subtasks
            for subtask in ready:
                if self._state == PWCState.CANCELLED:
                    return
                self._enqueue_subtask(agent, conversation_id, subtask)

            # Brief wait before re-checking
            await self._wait(0.3)

    def _enqueue_subtask(self, agent: Agent, conversation_id: str, subtask: SubTask):
        """Enqueue a subtask for execution + review."""
        tid = subtask.id
        self._result.retry_counts.setdefault(tid, 0)

        async def execute_and_review():
            if self._callback:
                self._callback.on_subtask_start(subtask)

            # Work phase
            worker_result = await self.worker.execute(
                agent, subtask, conversation_id,
                context=self._build_subtask_context(subtask),
            )
            self._result.subtask_results[tid] = worker_result

            # Critic phase
            review = await self.critic.review(
                provider=agent.model_provider or "openai",
                model=agent.model_name or "gpt-4o",
                title=subtask.title,
                description=subtask.description or "",
                output=worker_result.get("output", ""),
            )
            self._result.review_results[tid] = review

            if self._callback:
                self._callback.on_subtask_complete(subtask, worker_result, review)

            if review.verdict == "approved":
                logger.info("Subtask %s approved by critic", tid)
            elif self._result.retry_counts[tid] < self.max_retries_per_subtask:
                self._result.retry_counts[tid] += 1
                retry_msg = f"评审未通过 ({review.verdict}): {review.summary}"
                logger.warning("Subtask %s needs revision: %s", tid, retry_msg)

                subtask.status = "pending"
                subtask.end_time = None
                self.db.commit()

                if self._callback:
                    self._callback.on_subtask_retry(
                        subtask, self._result.retry_counts[tid], retry_msg
                    )
            else:
                logger.warning(
                    "Subtask %s exhausted retries (%d), marking failed",
                    tid, self.max_retries_per_subtask,
                )
                subtask.status = "failed"
                self.db.commit()

        self.task_queue.enqueue(
            task_id=tid,
            coro=execute_and_review,
            priority=Priority.NORMAL,
            timeout=300.0,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_subtask_context(self, subtask: SubTask) -> str:
        """Collect outputs from completed dependency subtasks as context."""
        plan_id = subtask.plan_id
        all_subtasks = (
            self.db.query(SubTask)
            .filter(SubTask.plan_id == plan_id)
            .order_by(SubTask.order_index)
            .all()
        )
        deps = json.loads(subtask.depends_on_json or "[]")

        parts = []
        for idx in deps:
            if 0 <= idx < len(all_subtasks):
                dep = all_subtasks[idx]
                if dep.result_json:
                    result = json.loads(dep.result_json)
                    output = result.get("output", "")
                    parts.append(f"## {dep.title}\n{output[:2000]}")

        return "\n\n".join(parts)

    def _get_plan_status(self, plan_id: str) -> str:
        subtasks = (
            self.db.query(SubTask)
            .filter(SubTask.plan_id == plan_id)
            .all()
        )
        if not subtasks:
            return "completed"
        statuses = {st.status for st in subtasks}
        if statuses == {"completed"}:
            return "completed"
        if "failed" in statuses:
            return "failed"
        return "running"

    def _count_running_subtasks(self, plan_id: str) -> int:
        return (
            self.db.query(SubTask)
            .filter(SubTask.plan_id == plan_id, SubTask.status == "running")
            .count()
        )

    def _count_failed_subtasks(self, plan_id: str) -> int:
        return (
            self.db.query(SubTask)
            .filter(SubTask.plan_id == plan_id, SubTask.status == "failed")
            .count()
        )

    async def _wait(self, seconds: float):
        """Async wait that's interruptible."""
        for _ in range(int(seconds * 10)):
            if self._state == PWCState.CANCELLED:
                return
            await asyncio.sleep(0.1)

    def get_execution_summary(self) -> dict:
        """Return a human-readable execution summary."""
        plan = self._result.plan
        if not plan:
            return {"state": self._state.value, "error": "无计划"}

        subtasks = (
            self.db.query(SubTask)
            .filter(SubTask.plan_id == plan.id)
            .order_by(SubTask.order_index)
            .all()
        )
        summary = {
            "plan_title": plan.title,
            "state": self._state.value,
            "total": len(subtasks),
            "completed": sum(1 for st in subtasks if st.status == "completed"),
            "failed": sum(1 for st in subtasks if st.status == "failed"),
            "running": sum(1 for st in subtasks if st.status == "running"),
            "pending": sum(1 for st in subtasks if st.status == "pending"),
        }
        return summary
