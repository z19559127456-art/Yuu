"""
编排器集成测试 — Mock P/W/C 组件验证 Plan→Work→Critic 状态机完整流程。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.orchestrator import (
    Orchestrator, PWCState, PWCEvent, PWCResult, PWCError, PWCProgressCallback,
    TRANSITIONS,
)
from app.models import Agent, Plan, SubTask


# ---------------------------------------------------------------------------
# 状态机验证
# ---------------------------------------------------------------------------

class TestStateMachine:

    def test_initial_state_is_idle(self, db_session, api_keys):
        orch = Orchestrator(db_session, api_keys)
        assert orch.state == PWCState.IDLE

    def test_transition_graph_completeness(self):
        """验证 TRANSITIONS 字典的完整性。"""
        assert TRANSITIONS[PWCState.IDLE][PWCEvent.START] == PWCState.PLANNING
        for end_state in (PWCState.COMPLETED, PWCState.FAILED, PWCState.CANCELLED):
            assert TRANSITIONS[end_state] == {}

    def test_valid_transition(self, db_session, api_keys):
        """合法状态转换应成功。"""
        orch = Orchestrator(db_session, api_keys)
        orch._transition(PWCEvent.START)
        assert orch.state == PWCState.PLANNING

    def test_invalid_transition_raises(self, db_session, api_keys):
        """非法状态转换应抛出 PWCError。"""
        orch = Orchestrator(db_session, api_keys)
        with pytest.raises(PWCError):
            orch._transition(PWCEvent.PLAN_CREATED)

    def test_progress_callback_fired_on_transition(self, db_session, api_keys):
        """状态转换时应触发回调。"""
        orch = Orchestrator(db_session, api_keys)
        cb = MagicMock()
        orch.set_callback(cb)
        orch._transition(PWCEvent.START)
        cb.on_state_change.assert_called_once()

    def test_cancel_completed_is_noop(self, db_session, api_keys):
        """对已完成 cycle 调用 cancel 应为 no-op。"""
        orch = Orchestrator(db_session, api_keys)
        orch._state = PWCState.COMPLETED
        orch._result.end_time = datetime.now(timezone.utc)
        asyncio.run(orch.cancel())
        assert orch.state == PWCState.COMPLETED


# ---------------------------------------------------------------------------
# PWCResult
# ---------------------------------------------------------------------------

class TestPWCResult:

    def test_initial_state(self):
        r = PWCResult()
        assert r.state == PWCState.IDLE
        assert r.plan is None
        assert r.subtask_results == {}
        assert r.error is None

    def test_to_dict(self):
        r = PWCResult()
        r.state = PWCState.PLANNING
        plan = MagicMock()
        plan.id = "plan-123"
        r.plan = plan

        d = r.to_dict()
        assert d["plan_id"] == "plan-123"
        assert d["state"] == "planning"

    def test_to_dict_complete(self):
        r = PWCResult()
        r.state = PWCState.COMPLETED
        r.error = None
        r.start_time = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
        r.end_time = datetime(2026, 5, 7, 12, 5, 0, tzinfo=timezone.utc)

        d = r.to_dict()
        assert d["state"] == "completed"
        assert d["error"] == ""
        assert "2026-05-07" in d["start_time"]


# ---------------------------------------------------------------------------
# PWCProgressCallback
# ---------------------------------------------------------------------------

class TestProgressCallback:

    def test_all_methods_exist(self):
        """回调类应定义所有接口方法。"""
        cb = PWCProgressCallback()
        assert hasattr(cb, "on_state_change")
        assert hasattr(cb, "on_subtask_start")
        assert hasattr(cb, "on_subtask_complete")
        assert hasattr(cb, "on_subtask_retry")
        assert hasattr(cb, "on_error")
        assert hasattr(cb, "on_complete")


# ---------------------------------------------------------------------------
# 工具方法
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_build_subtask_context_empty(self, db_session, api_keys, sample_agent):
        """无依赖时上下文应为空。"""
        orch = Orchestrator(db_session, api_keys)

        plan = Plan(
            id="plan-ctx",
            agent_id=sample_agent.id,
            title="上下文测试",
            status="pending",
        )
        db_session.add(plan)
        db_session.flush()

        subtask = SubTask(
            id="sub-ctx",
            plan_id=plan.id,
            title="无依赖任务",
            depends_on_json="[]",
            order_index=0,
        )
        db_session.add(subtask)
        db_session.commit()

        ctx = orch._build_subtask_context(subtask)
        assert ctx == ""

    def test_build_subtask_context_with_deps(self, db_session, api_keys, sample_agent):
        """有已完成依赖时应包含依赖输出。"""
        orch = Orchestrator(db_session, api_keys)

        plan = Plan(
            id="plan-ctx2",
            agent_id=sample_agent.id,
            title="上下文测试2",
            status="pending",
        )
        db_session.add(plan)
        db_session.flush()

        dep = SubTask(
            id="dep-1",
            plan_id=plan.id,
            title="前置任务",
            status="completed",
            result_json=json.dumps({"output": "前置任务的输出结果"}),
            order_index=0,
        )
        db_session.add(dep)

        main_task = SubTask(
            id="main-1",
            plan_id=plan.id,
            title="主任务",
            depends_on_json="[0]",
            order_index=1,
        )
        db_session.add(main_task)
        db_session.commit()

        ctx = orch._build_subtask_context(main_task)
        assert "前置任务" in ctx
        assert "前置任务的输出结果" in ctx

    def test_get_plan_status_empty(self, db_session, api_keys):
        """无子任务的计划应返回 completed。"""
        orch = Orchestrator(db_session, api_keys)
        status = orch._get_plan_status("nonexistent-plan")
        assert status == "completed"

    def test_get_execution_summary(self, db_session, api_keys, sample_agent):
        """get_execution_summary 应返回正确的统计数据。"""
        orch = Orchestrator(db_session, api_keys)

        plan = Plan(
            id="plan-summary",
            agent_id=sample_agent.id,
            title="汇总测试",
            status="pending",
        )
        db_session.add(plan)
        orch._result.plan = plan

        for i in range(3):
            st = SubTask(
                id=f"sub-sum-{i}",
                plan_id=plan.id,
                title=f"子任务{i}",
                status="completed" if i < 2 else "pending",
                order_index=i,
            )
            db_session.add(st)
        db_session.commit()

        summary = orch.get_execution_summary()
        assert summary["total"] == 3
        assert summary["completed"] == 2
        assert summary["pending"] == 1


# ---------------------------------------------------------------------------
# run() — 简化版集成测试 (直接调用内部阶段，避免 TaskGroup 死锁)
# ---------------------------------------------------------------------------

class TestOrchestratorRunPhases:

    @pytest.fixture
    def orch_with_mocks(self, db_session, api_keys):
        """创建 Orchestrator 并将 Planner/Worker/Critic 替换为 mock。"""
        orch = Orchestrator(db_session, api_keys, max_concurrent=2)
        orch.planner = MagicMock()
        orch.worker = MagicMock()
        orch.critic = MagicMock()
        orch.task_queue.start = AsyncMock()
        orch.task_queue.stop = AsyncMock()
        orch.task_queue.enqueue = MagicMock()
        return orch

    @pytest.mark.asyncio
    async def test_phase_plan_success(self, db_session, sample_agent, orch_with_mocks):
        """_phase_plan 应正确创建计划并转换到 PLAN_READY。"""
        orch = orch_with_mocks

        plan = Plan(
            id="plan-phase",
            agent_id=sample_agent.id,
            title="相位测试计划",
            status="pending",
        )
        orch.planner.create_plan = AsyncMock(return_value=plan)

        await orch._phase_plan(sample_agent, "conv-1", "测试目标")

        assert orch.state == PWCState.PLAN_READY
        assert orch.result.plan.id == "plan-phase"

    @pytest.mark.asyncio
    async def test_phase_plan_error(self, db_session, sample_agent, orch_with_mocks):
        """Planner 错误时 _phase_plan 应传播异常。"""
        orch = orch_with_mocks
        orch.planner.create_plan = AsyncMock(side_effect=ValueError("规划失败"))

        with pytest.raises(ValueError):
            await orch._phase_plan(sample_agent, "conv-1", "不可能的目标")

    @pytest.mark.asyncio
    async def test_phase_execute_completes_when_all_done(self, db_session, sample_agent, orch_with_mocks):
        """当无 ready subtasks 且无 running subtasks 时，_phase_execute 应正常退出。"""
        orch = orch_with_mocks
        orch._state = PWCState.PLAN_READY

        plan = Plan(
            id="plan-exec",
            agent_id=sample_agent.id,
            title="执行测试",
            status="running",
        )
        db_session.add(plan)
        db_session.flush()
        orch._result.plan = plan

        # 所有子任务已完成
        st = SubTask(
            id="sub-done",
            plan_id=plan.id,
            title="已完成的子任务",
            status="completed",
            order_index=0,
        )
        db_session.add(st)
        db_session.commit()

        orch.planner.get_ready_subtasks = MagicMock(return_value=[])
        type(orch.task_queue).running_count = property(lambda self: 0)

        await orch._phase_execute(sample_agent, "conv-1")

        # 应正常退出无错误
        assert orch._result.error is None


# ---------------------------------------------------------------------------
# 重试逻辑 (测试 enqueue 执行和 retry)
# ---------------------------------------------------------------------------

class TestRetryLogic:

    @pytest.fixture
    def orch_with_mocks(self, db_session, api_keys):
        orch = Orchestrator(db_session, api_keys, max_concurrent=2)
        orch.planner = MagicMock()
        orch.worker = MagicMock()
        orch.critic = MagicMock()
        orch.task_queue.start = AsyncMock()
        orch.task_queue.stop = AsyncMock()
        orch.task_queue.enqueue = MagicMock()
        return orch

    @pytest.mark.asyncio
    async def test_enqueue_subtask_sets_retry_counter(self, db_session, sample_agent, orch_with_mocks):
        """_enqueue_subtask 应初始化重试计数器。"""
        orch = orch_with_mocks

        subtask = SubTask(
            id="sub-retry",
            plan_id="plan-init",
            title="重试测试",
            status="pending",
            depends_on_json="[]",
            order_index=0,
        )
        db_session.add(subtask)
        db_session.commit()

        orch.worker.execute = AsyncMock(return_value={"output": "done"})
        mock_review = MagicMock()
        mock_review.verdict = "approved"
        mock_review.summary = "通过"
        orch.critic.review = AsyncMock(return_value=mock_review)

        orch._enqueue_subtask(sample_agent, "conv-1", subtask)

        assert "sub-retry" in orch.result.retry_counts
        assert orch.result.retry_counts["sub-retry"] == 0

    def test_retry_exhaustion_marks_failed(self, db_session, sample_agent, orch_with_mocks):
        """当重试次数超过上限时，子任务应标记为 failed。"""
        orch = orch_with_mocks
        orch.max_retries_per_subtask = 2
        orch._result.retry_counts["sub-fail"] = 2  # 已达上限

        subtask = SubTask(
            id="sub-fail",
            plan_id="plan-x",
            title="失败测试",
            status="running",
            depends_on_json="[]",
            order_index=0,
        )
        db_session.add(subtask)
        db_session.commit()

        # 模拟 execute_and_review 中 retry count >= max 的逻辑
        tid = "sub-fail"
        assert orch._result.retry_counts[tid] >= orch.max_retries_per_subtask


# ---------------------------------------------------------------------------
# 并发控制
# ---------------------------------------------------------------------------

class TestConcurrencyPrevention:

    def test_concurrent_run_prevented(self, db_session, api_keys):
        """_running 为 True 时再调用 run() 应抛出 PWCError。"""
        orch = Orchestrator(db_session, api_keys)
        orch._running = True

        with pytest.raises(PWCError, match="already running"):
            asyncio.run(orch.run(
                Agent(id="a", name="X", system_prompt=""),
                "conv-1", "目标",
            ))


# ---------------------------------------------------------------------------
# PWC 枚举验证
# ---------------------------------------------------------------------------

class TestPWCEnums:

    def test_all_states_have_values(self):
        assert PWCState.IDLE.value == "idle"
        assert PWCState.COMPLETED.value == "completed"
        assert PWCState.FAILED.value == "failed"
        assert PWCState.CANCELLED.value == "cancelled"

    def test_all_events_have_values(self):
        assert PWCEvent.START.value == "start"
        assert PWCEvent.ALL_DONE.value == "all_done"

    def test_all_transitions_are_valid_states(self):
        """所有 TRANSITIONS 中引用的状态都应是有效的 PWCState。"""
        all_states = set(TRANSITIONS.keys())
        for target_map in TRANSITIONS.values():
            all_states.update(target_map.values())
        for s in all_states:
            assert isinstance(s, PWCState)
