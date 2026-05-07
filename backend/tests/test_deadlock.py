"""
Tests for the 3-level deadlock detection system.
"""
import asyncio
import time
import pytest
from app.deadlock_detector import (
    LoopDetector, BudgetDetector, StallDetector,
    DeadlockDetector, DeadlockReport,
)


class TestLoopDetector:
    def test_no_loop_with_few_records(self):
        d = LoopDetector(max_window=50, repeat_threshold=5)
        for i in range(3):
            d.record("agent1", f"action_{i}")
        report = d.check("agent1")
        assert report.triggered is False

    def test_detects_repeated_same_action(self):
        d = LoopDetector(max_window=50, repeat_threshold=5)
        for _ in range(5):
            d.record("agent1", "same_action")
        report = d.check("agent1")
        assert report.triggered is True
        assert report.level == 1
        assert "环路" in report.reason

    def test_no_false_positive_with_different_actions(self):
        d = LoopDetector(max_window=50, repeat_threshold=5)
        for i in range(10):
            d.record("agent1", f"action_{i % 3}")
        report = d.check("agent1")
        assert report.triggered is False

    def test_high_frequency_detection(self):
        d = LoopDetector(max_window=50, repeat_threshold=3)
        # 7 times same action: consecutive check triggers first (repeat_threshold=3)
        for _ in range(7):
            d.record("agent1", "loop_action")
        report = d.check("agent1")
        assert report.triggered is True
        assert report.level == 1

    def test_clear_resets(self):
        d = LoopDetector(max_window=50, repeat_threshold=3)
        for _ in range(5):
            d.record("agent1", "same")
        d.clear("agent1")
        report = d.check("agent1")
        assert report.triggered is False

    def test_clear_all(self):
        d = LoopDetector(max_window=50, repeat_threshold=3)
        for _ in range(5):
            d.record("agent1", "same")
        d.clear()
        report = d.check("agent1")
        assert report.triggered is False

    def test_window_sliding(self):
        d = LoopDetector(max_window=10, repeat_threshold=5)
        # Fill with unique actions, then 5 same
        for i in range(6):
            d.record("agent1", f"unique_{i}")
        for _ in range(5):
            d.record("agent1", "same")
        report = d.check("agent1")
        assert report.triggered is True

    def test_separate_callers_independent(self):
        d = LoopDetector(max_window=50, repeat_threshold=3)
        for _ in range(5):
            d.record("agent1", "loop")
        # agent2 should not be affected
        report = d.check("agent2")
        assert report.triggered is False
        # agent1 should be triggered
        report = d.check("agent1")
        assert report.triggered is True


class TestBudgetDetector:
    def test_no_exceed_defaults(self):
        b = BudgetDetector(max_turns=100, max_tokens=1_000_000)
        b.start_session("s1")
        for _ in range(10):
            b.record_turn("s1", tokens=100)
        report = b.check("s1")
        assert report.triggered is False

    def test_exceed_max_turns(self):
        b = BudgetDetector(max_turns=5)
        b.start_session("s1")
        for _ in range(6):
            b.record_turn("s1")
        report = b.check("s1")
        assert report.triggered is True
        assert report.level == 2
        assert "轮次上限" in report.reason

    def test_exceed_max_tokens(self):
        b = BudgetDetector(max_tokens=1000)
        b.start_session("s1")
        b.record_turn("s1", tokens=1500)
        report = b.check("s1")
        assert report.triggered is True
        assert "Token 预算" in report.reason

    def test_exceed_max_duration(self):
        b = BudgetDetector(max_duration_seconds=1)
        b.start_session("s1")
        time.sleep(1.1)
        report = b.check("s1")
        assert report.triggered is True
        assert "执行时长上限" in report.reason

    def test_clear_resets_budget(self):
        b = BudgetDetector(max_turns=3)
        b.start_session("s1")
        for _ in range(4):
            b.record_turn("s1")
        b.clear("s1")
        report = b.check("s1")
        assert report.triggered is False


class TestStallDetector:
    def test_no_stall_with_recent_activity(self):
        s = StallDetector(stall_timeout=60.0)
        s.mark_activity("s1")
        report = s.check("s1")
        assert report.triggered is False

    def test_detects_stall(self):
        s = StallDetector(stall_timeout=0.1)
        s.mark_activity("s1")
        time.sleep(0.2)
        report = s.check("s1")
        assert report.triggered is True
        assert report.level == 3
        assert "无响应超时" in report.reason

    def test_no_report_for_unknown_session(self):
        s = StallDetector(stall_timeout=0.1)
        report = s.check("unknown")
        assert report.triggered is False

    def test_stop_clears_session(self):
        s = StallDetector(stall_timeout=0.1)
        s.mark_activity("s1")
        s.stop_monitoring("s1")
        report = s.check("s1")
        assert report.triggered is False

    def test_start_stop_background_check(self):
        s = StallDetector(stall_timeout=60.0)

        async def run():
            await s.start_background_check("s1", interval=1.0)
            await asyncio.sleep(0.1)
            await s.stop_background_check()

        asyncio.run(run())
        # Should not crash
        assert s._running is False


class TestDeadlockDetector:
    def test_check_all_passes(self):
        d = DeadlockDetector()
        d.loop.record("agent1", "action1")
        d.budget.start_session("s1")
        d.budget.record_turn("s1", tokens=100)
        d.stall.mark_activity("s1")
        report = d.check_all("agent1", "s1")
        assert report.triggered is False

    def test_check_all_loop_first(self):
        """Loop detection should trigger before budget/stall."""
        d = DeadlockDetector(repeat_threshold=3)
        d.budget.start_session("s1")
        for _ in range(5):
            d.loop.record("agent1", "same")
        report = d.check_all("agent1", "s1")
        assert report.triggered is True
        assert report.level == 1

    def test_check_all_budget_second(self):
        d = DeadlockDetector(max_turns=3)
        d.budget.start_session("s1")
        d.stall.mark_activity("s1")
        for _ in range(4):
            d.budget.record_turn("s1")
        report = d.check_all("agent1", "s1")
        assert report.triggered is True
        assert report.level == 2

    def test_clear_all(self):
        d = DeadlockDetector()
        d.loop.record("agent1", "test")
        d.budget.start_session("s1")
        d.budget.record_turn("s1")
        d.stall.mark_activity("s1")
        d.clear_all(session_id="s1", caller_id="agent1")
        report = d.check_all("agent1", "s1")
        assert report.triggered is False

    def test_deadlock_report_to_dict(self):
        r = DeadlockReport(triggered=True, level=2, reason="测试", details={"key": "val"})
        d = r.to_dict()
        assert d["triggered"] is True
        assert d["level"] == 2
        assert d["reason"] == "测试"
        assert d["details"]["key"] == "val"
