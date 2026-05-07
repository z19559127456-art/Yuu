"""
Tests for all ORM models: CRUD, relationships, to_dict().
"""
import json
import pytest
from datetime import datetime, timezone

from app.models import (
    Agent, Conversation, Message, TaskRecord, MemorySummary,
    WebRecord, UIRecord, VisionRecord, Plan, SubTask,
    TaskExecution, SkillRecord, VectorMemoryEntry,
    GroupConversation, GroupParticipant, DiscussionRound, AuditLog,
)


class TestAgent:
    def test_create_agent(self, db_session, sample_agent_dict):
        agent = Agent(**sample_agent_dict)
        db_session.add(agent)
        db_session.commit()

        assert agent.id is not None
        assert agent.name == "测试助手"
        assert agent.is_active is True
        assert agent.created_at is not None

    def test_to_dict(self, sample_agent):
        d = sample_agent.to_dict()
        assert d["name"] == "测试助手"
        assert d["model_provider"] == "openai"
        assert d["is_active"] is True
        assert d["personality"]["style"] == "严谨"
        assert d["tools_config"]["cli"]["enabled"] is True
        assert d["skills"] == ["code_review", "summarize"]
        assert "id" in d
        assert "created_at" in d

    def test_update_agent(self, sample_agent, db_session):
        sample_agent.name = "更新助手"
        sample_agent.temperature = 0.9
        db_session.commit()
        db_session.refresh(sample_agent)
        assert sample_agent.name == "更新助手"
        assert sample_agent.temperature == 0.9

    def test_delete_agent_cascades(self, sample_agent, sample_conversation, db_session):
        """Deleting an agent should cascade-delete its conversations."""
        db_session.delete(sample_agent)
        db_session.commit()
        assert db_session.query(Agent).count() == 0
        assert db_session.query(Conversation).count() == 0


class TestConversation:
    def test_create_conversation(self, sample_agent, db_session):
        conv = Conversation(agent_id=sample_agent.id, title="测试对话")
        db_session.add(conv)
        db_session.commit()
        assert conv.id is not None
        assert conv.title == "测试对话"

    def test_to_dict(self, sample_conversation):
        d = sample_conversation.to_dict()
        assert d["title"] == "测试对话"
        assert d["agent_id"] is not None

    def test_relationship(self, sample_agent, sample_conversation, db_session):
        """Conversation should be accessible from agent.conversations."""
        assert len(sample_agent.conversations) == 1
        assert sample_agent.conversations[0].id == sample_conversation.id


class TestMessage:
    def test_create_message(self, sample_conversation, db_session):
        msg = Message(
            conversation_id=sample_conversation.id,
            role="user",
            content="你好",
        )
        db_session.add(msg)
        db_session.commit()
        assert msg.id is not None
        assert msg.status == "sent"

    def test_to_dict(self, sample_conversation, db_session):
        msg = Message(conversation_id=sample_conversation.id, role="assistant", content="Hello!")
        db_session.add(msg)
        db_session.commit()
        d = msg.to_dict()
        assert d["role"] == "assistant"
        assert d["content"] == "Hello!"
        assert d["status"] == "sent"
        assert d["is_edited"] is False

    def test_message_types(self, sample_conversation, db_session):
        """Test different message types: text, tool_call, tool_result, error."""
        types = ["text", "tool_call", "tool_result", "error", "system_notice"]
        for t in types:
            msg = Message(conversation_id=sample_conversation.id, role="assistant", type=t, content="test")
            db_session.add(msg)
        db_session.commit()
        assert db_session.query(Message).count() == len(types)

    def test_edit_message(self, sample_conversation, db_session):
        msg = Message(conversation_id=sample_conversation.id, role="user", content="original")
        db_session.add(msg)
        db_session.commit()

        msg.content = "edited"
        msg.is_edited = True
        msg.edited_from = "original"
        db_session.commit()
        db_session.refresh(msg)
        assert msg.content == "edited"
        assert msg.is_edited is True


class TestWebRecord:
    def test_create(self, sample_agent, db_session):
        r = WebRecord(agent_id=sample_agent.id, url="https://example.com", action="navigate")
        db_session.add(r)
        db_session.commit()
        assert r.id is not None
        assert r.status == "running"

    def test_to_dict(self, sample_agent, db_session):
        r = WebRecord(agent_id=sample_agent.id, url="https://example.com", action="screenshot", status="success")
        db_session.add(r)
        db_session.commit()
        d = r.to_dict()
        assert d["url"] == "https://example.com"
        assert d["action"] == "screenshot"
        assert d["status"] == "success"


class TestUIRecord:
    def test_create(self, sample_agent, db_session):
        r = UIRecord(agent_id=sample_agent.id, action="click", target_element="#btn")
        db_session.add(r)
        db_session.commit()
        d = r.to_dict()
        assert d["action"] == "click"
        assert d["target_element"] == "#btn"

    def test_status_transitions(self, sample_agent, db_session):
        r = UIRecord(agent_id=sample_agent.id, action="type", status="running")
        db_session.add(r)
        db_session.commit()
        r.status = "success"
        db_session.commit()
        db_session.refresh(r)
        assert r.status == "success"


class TestVisionRecord:
    def test_create(self, sample_agent, db_session):
        r = VisionRecord(
            agent_id=sample_agent.id,
            image_source="upload",
            prompt="描述这张图片",
            result_text="这是一只猫",
            status="success",
        )
        db_session.add(r)
        db_session.commit()
        d = r.to_dict()
        assert d["image_source"] == "upload"
        assert d["result_text"] == "这是一只猫"

    def test_default_image_source(self, sample_agent, db_session):
        r = VisionRecord(agent_id=sample_agent.id, image_source="", prompt="test")
        db_session.add(r)
        db_session.commit()
        d = r.to_dict()
        assert d["image_source"] == "screenshot"


class TestPlan:
    def test_create_plan(self, sample_agent, db_session):
        plan = Plan(
            agent_id=sample_agent.id,
            title="测试计划",
            description="一个测试计划",
            subtasks_json=json.dumps([
                {"title": "步骤1", "depends_on": [], "order_index": 0},
                {"title": "步骤2", "depends_on": [0], "order_index": 1},
            ]),
        )
        db_session.add(plan)
        db_session.commit()
        d = plan.to_dict()
        assert d["title"] == "测试计划"
        assert d["status"] == "pending"
        assert len(d["subtasks"]) == 2

    def test_status_flow(self, sample_agent, db_session):
        plan = Plan(agent_id=sample_agent.id, title="流程图", status="pending")
        db_session.add(plan)
        db_session.commit()
        for status in ["running", "completed", "failed", "cancelled"]:
            plan.status = status
            db_session.commit()
            db_session.refresh(plan)
            assert plan.status == status


class TestSubTask:
    def test_create_with_dependencies(self, sample_agent, db_session):
        plan = Plan(agent_id=sample_agent.id, title="P")
        db_session.add(plan)
        db_session.flush()

        st1 = SubTask(plan_id=plan.id, title="前置任务", order_index=0)
        st2 = SubTask(plan_id=plan.id, title="后置任务", depends_on_json=json.dumps([0]), order_index=1)
        db_session.add(st1)
        db_session.add(st2)
        db_session.commit()

        assert st1.status == "pending"
        assert json.loads(st2.depends_on_json) == [0]

    def test_completion(self, sample_agent, db_session):
        plan = Plan(agent_id=sample_agent.id, title="P")
        db_session.add(plan)
        db_session.flush()

        st = SubTask(plan_id=plan.id, title="任务", status="running")
        db_session.add(st)
        db_session.commit()

        st.status = "completed"
        st.result_json = json.dumps({"output": "done"})
        db_session.commit()
        db_session.refresh(st)
        assert st.status == "completed"
        assert json.loads(st.result_json)["output"] == "done"


class TestTaskExecution:
    def test_execution_lifecycle(self, sample_agent, db_session):
        ex = TaskExecution(agent_id=sample_agent.id, task_type="subtask_execution")
        db_session.add(ex)
        db_session.commit()
        assert ex.status == "running"

        ex.status = "success"
        ex.duration_ms = 1500
        db_session.commit()
        db_session.refresh(ex)
        assert ex.status == "success"
        assert ex.duration_ms == 1500


class TestGroupConversation:
    def test_create_group(self, sample_agent, db_session):
        g = GroupConversation(title="测试群聊", topic="讨论AI", mode="discussion", created_by=sample_agent.id)
        db_session.add(g)
        db_session.commit()
        d = g.to_dict()
        assert d["title"] == "测试群聊"
        assert d["mode"] == "discussion"
        assert d["status"] == "active"

    def test_group_modes(self, db_session):
        modes = ["discussion", "task"]
        for mode in modes:
            g = GroupConversation(title=f"群聊-{mode}", mode=mode)
            db_session.add(g)
        db_session.commit()
        assert db_session.query(GroupConversation).count() == 2


class TestGroupParticipant:
    def test_add_participant(self, sample_agent, db_session):
        g = GroupConversation(title="群聊")
        db_session.add(g)
        db_session.flush()

        p = GroupParticipant(group_id=g.id, agent_id=sample_agent.id, role="moderator")
        db_session.add(p)
        db_session.commit()
        d = p.to_dict()
        assert d["role"] == "moderator"
        assert d["agent_id"] == sample_agent.id

    def test_default_role(self, sample_agent, db_session):
        g = GroupConversation(title="群聊")
        db_session.add(g)
        db_session.flush()

        p = GroupParticipant(group_id=g.id, agent_id=sample_agent.id)
        db_session.add(p)
        db_session.commit()
        d = p.to_dict()
        assert d["role"] == "participant"


class TestDiscussionRound:
    def test_create_round(self, db_session):
        g = GroupConversation(title="讨论组")
        db_session.add(g)
        db_session.flush()

        r = DiscussionRound(group_id=g.id, round_number=1, topic="议题1")
        db_session.add(r)
        db_session.commit()
        d = r.to_dict()
        assert d["round_number"] == 1
        assert d["topic"] == "议题1"


class TestSkillRecord:
    def test_create(self, sample_agent, db_session):
        r = SkillRecord(
            agent_id=sample_agent.id,
            skill_name="code_review",
            input_json=json.dumps({"code": "print(1)"}),
            status="success",
        )
        db_session.add(r)
        db_session.commit()
        d = r.to_dict()
        assert d["skill_name"] == "code_review"
        assert d["status"] == "success"


class TestVectorMemoryEntry:
    def test_create(self, sample_agent, db_session):
        e = VectorMemoryEntry(
            agent_id=sample_agent.id,
            chunk_id="chunk_001",
            content="这是重要的记忆内容",
        )
        db_session.add(e)
        db_session.commit()
        d = e.to_dict()
        assert d["chunk_id"] == "chunk_001"
        assert d["content"] == "这是重要的记忆内容"


class TestAuditLog:
    def test_create_log(self, sample_agent, db_session):
        log = AuditLog(
            agent_id=sample_agent.id,
            action="tool_call",
            resource_type="web",
            details_json=json.dumps({"url": "https://example.com"}),
            ip_address="127.0.0.1",
        )
        db_session.add(log)
        db_session.commit()
        d = log.to_dict()
        assert d["action"] == "tool_call"
        assert d["ip_address"] == "127.0.0.1"
        assert d["details"]["url"] == "https://example.com"

    def test_audit_query(self, sample_agent, db_session):
        for action in ["tool_call", "config_change", "permission_denied"]:
            db_session.add(AuditLog(agent_id=sample_agent.id, action=action))
        db_session.commit()
        logs = db_session.query(AuditLog).all()
        assert len(logs) == 3


class TestTaskRecord:
    def test_create(self, sample_agent, db_session):
        tr = TaskRecord(agent_id=sample_agent.id, task_type="test", status="success")
        db_session.add(tr)
        db_session.commit()
        d = tr.to_dict() if hasattr(tr, 'to_dict') else {"status": tr.status, "task_type": tr.task_type}
        assert tr.status == "success"


class TestMemorySummary:
    def test_create_summary(self, sample_agent, db_session):
        ms = MemorySummary(agent_id=sample_agent.id, summary_text="摘要内容", message_count=10)
        db_session.add(ms)
        db_session.commit()
        assert ms.summary_text == "摘要内容"
        assert ms.message_count == 10
