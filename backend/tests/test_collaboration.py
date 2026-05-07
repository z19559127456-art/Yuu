"""
Tests for CollaborationEngine and Orchestrator — data classes, state machines, configs.
"""
import json
import pytest
from app.collaboration_engine import (
    CollaborationSession, CollaborationConfig,
    CollaborationMode, SessionState,
)
from app.orchestrator import PWCState, PWCEvent, TRANSITIONS


class TestPWCStateMachine:
    def test_idle_to_planning(self):
        assert TRANSITIONS[PWCState.IDLE][PWCEvent.START] == PWCState.PLANNING

    def test_planning_to_plan_ready(self):
        assert TRANSITIONS[PWCState.PLANNING][PWCEvent.PLAN_CREATED] == PWCState.PLAN_READY

    def test_planning_to_failed(self):
        assert TRANSITIONS[PWCState.PLANNING][PWCEvent.ERROR] == PWCState.FAILED

    def test_plan_ready_to_dispatching(self):
        assert TRANSITIONS[PWCState.PLAN_READY][PWCEvent.START] == PWCState.DISPATCHING

    def test_reviewing_to_completed(self):
        assert TRANSITIONS[PWCState.REVIEWING][PWCEvent.ALL_DONE] == PWCState.COMPLETED

    def test_reviewing_to_revising(self):
        assert TRANSITIONS[PWCState.REVIEWING][PWCEvent.REVIEW_FAILED] == PWCState.REVISING

    def test_revising_to_dispatching(self):
        assert TRANSITIONS[PWCState.REVISING][PWCEvent.START] == PWCState.DISPATCHING

    def test_complete_state_machine_coverage(self):
        """Every state should have defined transitions."""
        for state in PWCState:
            if state in (PWCState.COMPLETED, PWCState.FAILED, PWCState.CANCELLED):
                # Terminal states may have no transitions
                continue
            assert state in TRANSITIONS, f"State {state} missing from TRANSITIONS"

    def test_pwc_state_values(self):
        """Verify all expected states exist."""
        states = {s.value for s in PWCState}
        expected = {"idle", "planning", "plan_ready", "dispatching", "working",
                     "reviewing", "revising", "completed", "failed", "cancelled"}
        assert states == expected


class TestCollaborationSession:
    def test_default_values(self):
        session = CollaborationSession()
        assert session.mode == CollaborationMode.DISCUSSION
        assert session.state == SessionState.IDLE
        assert session.topic == ""
        assert session.agents == []

    def test_to_dict(self):
        from app.models import Agent
        agent = Agent(name="助手", id="a1")
        session = CollaborationSession(
            id="s1", group_id="g1",
            mode=CollaborationMode.TASK,
            state=SessionState.RUNNING,
            topic="构建网站",
            agents=[agent],
            created_at=1000.0,
        )
        d = session.to_dict()
        assert d["id"] == "s1"
        assert d["mode"] == "task"
        assert d["state"] == "running"
        assert d["topic"] == "构建网站"
        assert len(d["agents"]) == 1
        assert d["agents"][0]["name"] == "助手"


class TestCollaborationConfig:
    def test_defaults(self):
        config = CollaborationConfig()
        assert config.max_discussion_rounds == 50
        assert config.max_discussion_tokens == 500000
        assert config.max_task_duration == 3600
        assert config.stall_timeout == 120.0
        assert config.max_concurrent_tasks == 5
        assert config.enable_audit is True

    def test_custom_config(self):
        config = CollaborationConfig(
            max_discussion_rounds=10,
            stall_timeout=30.0,
            enable_audit=False,
        )
        assert config.max_discussion_rounds == 10
        assert config.stall_timeout == 30.0
        assert config.enable_audit is False


class TestCollaborationEngine:
    def test_init_with_defaults(self, db_session):
        from app.collaboration_engine import CollaborationEngine
        engine = CollaborationEngine(db=db_session, api_keys={})
        assert engine.config.max_discussion_rounds == 50
        assert engine._running is False
        assert engine._session is None

    def test_init_with_custom_config(self, db_session):
        from app.collaboration_engine import CollaborationEngine
        config = CollaborationConfig(max_discussion_rounds=10)
        engine = CollaborationEngine(db=db_session, api_keys={}, config=config)
        assert engine.config.max_discussion_rounds == 10

    def test_get_session_idle(self, db_session):
        from app.collaboration_engine import CollaborationEngine
        engine = CollaborationEngine(db=db_session, api_keys={})
        session = engine.get_session()
        assert session is None

    def test_get_state_summary_idle(self, db_session):
        from app.collaboration_engine import CollaborationEngine
        engine = CollaborationEngine(db=db_session, api_keys={})
        summary = engine.get_state_summary()
        assert summary["state"] == "idle"

    def test_on_event_callback(self, db_session):
        from app.collaboration_engine import CollaborationEngine
        engine = CollaborationEngine(db=db_session, api_keys={})
        events = []
        engine.on_event(lambda e: events.append(e))
        assert len(engine._callbacks) == 1

    def test_cleanup(self, db_session):
        from app.collaboration_engine import CollaborationEngine
        engine = CollaborationEngine(db=db_session, api_keys={})
        engine.on_event(lambda e: None)
        engine.cleanup()
        assert engine._running is False
        assert engine._session is None
        assert len(engine._callbacks) == 0

    def test_build_task_context(self, db_session):
        from app.collaboration_engine import CollaborationEngine
        from app.models import Agent
        engine = CollaborationEngine(db=db_session, api_keys={})
        agents = [
            Agent(name="Alice", role="前端", model_provider="openai", model_name="gpt-4o"),
            Agent(name="Bob", role="后端", model_provider="anthropic", model_name="claude-sonnet-4-6"),
        ]
        ctx = engine._build_task_context("构建网页", agents)
        assert "Alice" in ctx
        assert "Bob" in ctx
        assert "前端" in ctx
        assert "后端" in ctx
        assert "构建网页" in ctx
