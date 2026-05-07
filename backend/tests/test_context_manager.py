"""
Tests for ContextManager — system prompt building and message assembly.
"""
import json
import pytest
from app.context_manager import ContextManager
from app.models import Agent, Message, MemorySummary


class TestBuildSystemPrompt:
    def test_basic_system_prompt(self, sample_agent, db_session, api_keys):
        mgr = ContextManager(db=db_session, api_keys=api_keys)
        prompt = mgr._build_system_prompt(sample_agent)
        assert "测试助手" in prompt
        assert "请用中文回复" in prompt

    def test_personality_injection(self, db_session, api_keys):
        agent = Agent(
            name="助手",
            system_prompt="你是一个助手",
            personality_json=json.dumps({"style": "幽默", "tone": "轻松"}),
        )
        db_session.add(agent)
        db_session.commit()
        mgr = ContextManager(db=db_session, api_keys=api_keys)
        prompt = mgr._build_system_prompt(agent)
        assert "幽默" in prompt
        assert "轻松" in prompt

    def test_tools_config_injection(self, db_session, api_keys):
        agent = Agent(
            name="助手",
            system_prompt="",
            tools_config_json=json.dumps({"cli": {"enabled": True}, "web": {"enabled": False}}),
        )
        db_session.add(agent)
        db_session.commit()
        mgr = ContextManager(db=db_session, api_keys=api_keys)
        prompt = mgr._build_system_prompt(agent)
        assert "cli" in prompt
        assert "web" not in prompt  # disabled

    def test_skills_injection(self, db_session, api_keys):
        agent = Agent(
            name="助手",
            system_prompt="",
            skills_json=json.dumps(["code_review", "summarize"]),
        )
        db_session.add(agent)
        db_session.commit()
        mgr = ContextManager(db=db_session, api_keys=api_keys)
        prompt = mgr._build_system_prompt(agent)
        assert "code_review" in prompt

    def test_empty_configs(self, db_session, api_keys):
        agent = Agent(name="助手", system_prompt="")
        db_session.add(agent)
        db_session.commit()
        mgr = ContextManager(db=db_session, api_keys=api_keys)
        prompt = mgr._build_system_prompt(agent)
        # Should not crash even with empty configs
        assert "助手" in prompt or "你是一个有用的AI助手" in prompt

    def test_invalid_json_graceful(self, db_session, api_keys):
        agent = Agent(
            name="助手",
            personality_json="{invalid}",
            tools_config_json="{invalid}",
            skills_json="{invalid}",
        )
        db_session.add(agent)
        db_session.commit()
        mgr = ContextManager(db=db_session, api_keys=api_keys)
        # Should not crash with broken JSON
        prompt = mgr._build_system_prompt(agent)
        assert isinstance(prompt, str)


class TestBuildMessages:
    def test_basic_message_structure(self, sample_agent, sample_conversation, db_session, api_keys):
        mgr = ContextManager(db=db_session, api_keys=api_keys)
        messages = mgr.build_messages(sample_agent, sample_conversation.id, "你好")
        assert len(messages) >= 2  # system + user
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "你好"

    def test_with_history(self, sample_agent, sample_conversation, db_session, api_keys):
        for role, content in [("user", "第一条"), ("assistant", "回复1"), ("user", "第二条")]:
            db_session.add(Message(conversation_id=sample_conversation.id, role=role, content=content))
        db_session.commit()

        mgr = ContextManager(db=db_session, api_keys=api_keys)
        messages = mgr.build_messages(sample_agent, sample_conversation.id, "新消息")
        # Should include history (user/assistant roles only)
        history_roles = [m["role"] for m in messages[1:-1]]
        assert "user" in history_roles
        assert "assistant" in history_roles

    def test_with_memory_summaries(self, sample_agent, sample_conversation, db_session, api_keys):
        # Add memory summary
        ms = MemorySummary(agent_id=sample_agent.id, summary_text="之前讨论过AI话题", message_count=10)
        db_session.add(ms)
        db_session.commit()

        mgr = ContextManager(db=db_session, api_keys=api_keys)
        messages = mgr.build_messages(sample_agent, sample_conversation.id, "继续")
        # Check that summary is injected
        summary_found = any("AI话题" in m["content"] for m in messages if m["role"] == "system")
        assert summary_found

    def test_max_turns_limit(self, sample_agent, sample_conversation, db_session, api_keys):
        for i in range(60):
            role = "user" if i % 2 == 0 else "assistant"
            db_session.add(Message(conversation_id=sample_conversation.id, role=role, content=f"msg_{i}"))
        db_session.commit()

        mgr = ContextManager(db=db_session, api_keys=api_keys)
        messages = mgr.build_messages(sample_agent, sample_conversation.id, "新消息", max_turns=10)
        # Should only include last 10 turns + system + current user
        history_count = len([m for m in messages if m["role"] in ("user", "assistant") and m["content"] != "新消息"])
        assert history_count <= 10
