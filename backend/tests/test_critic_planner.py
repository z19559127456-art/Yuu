"""
Tests for Critic and Planner — focuses on parsing logic since LLM calls are external.
"""
import json
import pytest
from app.critic import Critic, ReviewResult, ReviewScore, CRITIC_PROMPT
from app.planner import Planner


# ---------------------------------------------------------------------------
# Critic Tests
# ---------------------------------------------------------------------------

class TestCriticParsing:
    def test_parse_valid_json(self):
        """Critic should parse valid JSON review output."""
        critic = Critic.__new__(Critic)
        raw = json.dumps({
            "passed": True,
            "score": {"completeness": 8, "correctness": 9, "clarity": 7, "actionability": 8},
            "summary": "输出质量良好",
            "issues": ["缺少错误处理"],
            "suggestions": ["添加 try-except"],
            "verdict": "approved",
        })
        result = critic._parse_review(raw)
        assert result.passed is True
        assert result.score.average == 8.0
        assert result.verdict == "approved"
        assert len(result.issues) == 1

    def test_parse_json_in_fence(self):
        """Critic should handle JSON wrapped in markdown code fences."""
        critic = Critic.__new__(Critic)
        raw = f"""```json
{json.dumps({"passed": False, "score": {"completeness": 4, "correctness": 5, "clarity": 6, "actionability": 4}, "summary": "需要改进", "issues": ["不完整"], "suggestions": ["补充细节"], "verdict": "major_revision"})}
```"""
        result = critic._parse_review(raw)
        assert result.passed is False
        assert result.verdict == "major_revision"

    def test_parse_invalid_json_returns_default(self):
        """Critic should return a default ReviewResult on parse failure."""
        critic = Critic.__new__(Critic)
        result = critic._parse_review("not json at all")
        assert result.passed is False
        assert result.verdict == "major_revision"

    def test_should_retry_logic(self):
        critic = Critic.__new__(Critic)

        approved = ReviewResult(passed=True, verdict="approved")
        assert critic.should_retry(approved) is False

        minor = ReviewResult(passed=True, verdict="minor_revision")
        assert critic.should_retry(minor) is False

        major = ReviewResult(passed=False, verdict="major_revision")
        assert critic.should_retry(major) is True

        rejected = ReviewResult(passed=False, verdict="rejected")
        assert critic.should_retry(rejected) is True

    def test_review_score_average(self):
        score = ReviewScore(completeness=8, correctness=7, clarity=6, actionability=9)
        assert score.average == 7.5

    def test_review_result_to_dict(self):
        r = ReviewResult(
            passed=True,
            score=ReviewScore(8, 9, 7, 8),
            summary="好",
            issues=["问题1"],
            suggestions=["建议1"],
            verdict="approved",
        )
        d = r.to_dict()
        assert d["passed"] is True
        assert d["verdict"] == "approved"
        assert d["score"]["completeness"] == 8


# ---------------------------------------------------------------------------
# Planner Tests
# ---------------------------------------------------------------------------

class TestPlannerParsing:
    def test_parse_valid_json(self):
        planner = Planner.__new__(Planner)
        raw = json.dumps({
            "title": "测试计划",
            "description": "一个测试",
            "subtasks": [
                {"title": "步骤1", "description": "第一步", "depends_on": [], "order_index": 0},
                {"title": "步骤2", "description": "第二步", "depends_on": [0], "order_index": 1},
            ],
        })
        result = planner._parse_llm_output(raw)
        assert result is not None
        assert result["title"] == "测试计划"
        assert len(result["subtasks"]) == 2

    def test_parse_with_fence(self):
        planner = Planner.__new__(Planner)
        raw = f"""```json
{json.dumps({"title": "计划", "subtasks": [{"title": "任务1", "depends_on": [], "order_index": 0}]})}
```"""
        result = planner._parse_llm_output(raw)
        assert result is not None
        assert result["title"] == "计划"

    def test_parse_invalid_returns_none(self):
        planner = Planner.__new__(Planner)
        result = planner._parse_llm_output("not json")
        assert result is None

    def test_parse_empty_fence_returns_none(self):
        planner = Planner.__new__(Planner)
        result = planner._parse_llm_output("```\n```")
        assert result is None

    def test_get_ready_subtasks_no_deps(self, db_session, sample_agent):
        """Subtask with no dependencies should be ready."""
        from app.models import Plan, SubTask
        plan = Plan(agent_id=sample_agent.id, title="测试", status="pending")
        db_session.add(plan)
        db_session.flush()

        st = SubTask(plan_id=plan.id, title="独立任务", depends_on_json="[]", order_index=0, status="pending")
        db_session.add(st)
        db_session.commit()

        planner = Planner(db=db_session, api_keys={})
        ready = planner.get_ready_subtasks(plan.id)
        assert len(ready) == 1
        assert ready[0].id == st.id

    def test_get_ready_subtasks_with_unmet_deps(self, db_session, sample_agent):
        """Subtask with pending dependency should not be ready."""
        from app.models import Plan, SubTask
        plan = Plan(agent_id=sample_agent.id, title="测试", status="pending")
        db_session.add(plan)
        db_session.flush()

        st1 = SubTask(plan_id=plan.id, title="前置", depends_on_json="[]", order_index=0, status="pending")
        st2 = SubTask(plan_id=plan.id, title="后置", depends_on_json=json.dumps([0]), order_index=1, status="pending")
        db_session.add(st1)
        db_session.add(st2)
        db_session.commit()

        planner = Planner(db=db_session, api_keys={})
        ready = planner.get_ready_subtasks(plan.id)
        # Only the first one is ready (second depends on first which is still pending)
        assert len(ready) == 1
        assert ready[0].id == st1.id

    def test_subtask_dependency_check(self, db_session, sample_agent):
        """When dependency is completed, subtask should become ready."""
        from app.models import Plan, SubTask
        plan = Plan(agent_id=sample_agent.id, title="测试", status="pending")
        db_session.add(plan)
        db_session.flush()

        st1 = SubTask(plan_id=plan.id, title="前置", depends_on_json="[]", order_index=0, status="completed")
        st2 = SubTask(plan_id=plan.id, title="后置", depends_on_json=json.dumps([0]), order_index=1, status="pending")
        db_session.add(st1)
        db_session.add(st2)
        db_session.commit()

        planner = Planner(db=db_session, api_keys={})
        ready = planner.get_ready_subtasks(plan.id)
        assert len(ready) == 1
        assert ready[0].id == st2.id
