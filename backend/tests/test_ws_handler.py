"""
Integration tests for ws_handler — handle_message routing, tool execution, error handling.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ws_handler import (
    handle_message,
    handle_websocket,
    _send_json,
    _get_api_keys,
    _run_async,
    _extract_tool_calls,
    _execute_single_tool,
    _execute_tool_calls,
)
from app.models import (
    Agent, Conversation, Message, TaskExecution,
    GroupConversation, GroupParticipant, Plan,
)


def _safe_sent(ws):
    """Helper: return parsed JSON from the first ws.send call, or None."""
    if not ws.send.called:
        return None
    return json.loads(ws.send.call_args[0][0])


def _all_sent(ws):
    """Helper: return all parsed JSON messages sent over the mock ws."""
    result = []
    for call in ws.send.call_args_list:
        try:
            result.append(json.loads(call[0][0]))
        except json.JSONDecodeError:
            result.append(call[0][0])
    return result


# ---------------------------------------------------------------------------
# handle_message — every known message type
# ---------------------------------------------------------------------------

class TestHandleMessage:
    """Route-to-handler dispatch tests. Each covers one msg_type path."""

    def test_ping(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "ping"}, db_session)
        assert _safe_sent(ws)["type"] == "pong"

    # ---- Agent CRUD ----

    def test_get_agents_empty(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "get_agents"}, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "agent_list"
        assert msg["agents"] == []

    def test_get_agents_with_data(self, db_session, sample_agent):
        ws = MagicMock()
        handle_message(ws, {"type": "get_agents"}, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "agent_list"
        assert len(msg["agents"]) == 1
        assert msg["agents"][0]["name"] == "测试助手"

    def test_create_agent(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "create_agent",
            "name": "新Agent",
            "role": "测试",
            "system_prompt": "你是一个测试Agent。",
            "model_provider": "openai",
            "model_name": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 2048,
        }, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "agent_created"
        assert msg["agent"]["name"] == "新Agent"
        assert msg["agent"]["role"] == "测试"

        # verify agent is persisted
        agent = db_session.query(Agent).filter(Agent.name == "新Agent").first()
        assert agent is not None

    def test_update_agent(self, db_session, sample_agent):
        ws = MagicMock()
        handle_message(ws, {
            "type": "update_agent",
            "agent_id": sample_agent.id,
            "name": "改名助手",
            "temperature": 0.3,
        }, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "agent_updated"
        assert msg["agent"]["name"] == "改名助手"
        assert msg["agent"]["temperature"] == 0.3

    def test_update_agent_not_found(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "update_agent",
            "agent_id": "nonexistent",
            "name": "X",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_delete_agent(self, db_session, sample_agent):
        ws = MagicMock()
        handle_message(ws, {
            "type": "delete_agent",
            "agent_id": sample_agent.id,
        }, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "agent_deleted"
        assert msg["agent_id"] == sample_agent.id

    def test_delete_agent_not_found(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "delete_agent", "agent_id": "nonexistent"}, db_session)
        assert _safe_sent(ws)["type"] == "error"

    # ---- Conversation CRUD ----

    def test_get_conversations(self, db_session, sample_conversation):
        ws = MagicMock()
        handle_message(ws, {
            "type": "get_conversations",
            "agent_id": sample_conversation.agent_id,
        }, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "conversation_list"
        assert len(msg["conversations"]) == 1

    def test_get_conversations_missing_agent_id(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "get_conversations"}, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_get_messages(self, db_session, sample_conversation):
        from app.models import Message
        msg_obj = Message(
            conversation_id=sample_conversation.id,
            role="user",
            content="你好",
        )
        db_session.add(msg_obj)
        db_session.commit()

        ws = MagicMock()
        handle_message(ws, {
            "type": "get_messages",
            "conversation_id": sample_conversation.id,
        }, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "message_list"
        assert len(msg["messages"]) == 1

    def test_get_messages_missing_id(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "get_messages"}, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_create_conversation(self, db_session, sample_agent):
        ws = MagicMock()
        handle_message(ws, {
            "type": "create_conversation",
            "agent_id": sample_agent.id,
        }, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "conversation_created"
        assert msg["conversation"]["agent_id"] == sample_agent.id

    def test_create_conversation_missing_agent_id(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "create_conversation"}, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_create_conversation_agent_not_found(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "create_conversation",
            "agent_id": "nonexistent",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_delete_conversation(self, db_session, sample_conversation):
        ws = MagicMock()
        handle_message(ws, {
            "type": "delete_conversation",
            "conversation_id": sample_conversation.id,
        }, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "conversation_deleted"
        assert msg["conversation_id"] == sample_conversation.id

    def test_delete_conversation_not_found(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "delete_conversation",
            "conversation_id": "nonexistent",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    # ---- Send Message (LLM) ----

    @patch("app.ws_handler.ContextManager")
    @patch("app.ws_handler.llm_client_from_agent")
    def test_send_message_creates_user_and_assistant_msgs(
        self, mock_llm_factory, mock_ctx_mgr, db_session, sample_conversation
    ):
        """send_message should persist both user and assistant messages and call LLM."""
        from app.llm_client import LLMClient

        # Mock ContextManager.build_messages
        mock_ctx = MagicMock()
        mock_ctx.build_messages.return_value = [{"role": "system", "content": "System"}, {"role": "user", "content": "你好"}]
        mock_ctx_mgr.return_value = mock_ctx

        # Mock LLM client — stream a simple response
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.stream_sync.return_value = iter(["Hello", " World"])
        mock_llm_factory.return_value = mock_llm

        ws = MagicMock()
        handle_message(ws, {
            "type": "send_message",
            "conversation_id": sample_conversation.id,
            "content": "你好",
        }, db_session)

        all_msgs = _all_sent(ws)
        types = [m["type"] for m in all_msgs]

        # Should have: new_message (user), new_message (assistant placeholder),
        #              message_update (×2), message_final
        assert "new_message" in types
        assert "message_update" in types
        assert "message_final" in types

        # Check user message was persisted
        user_msgs = [m for m in all_msgs if m["type"] == "new_message"]
        assert len(user_msgs) >= 2  # user + assistant placeholder
        assert user_msgs[0]["message"]["role"] == "user"

        # Check final message is the assistant's
        final = [m for m in all_msgs if m["type"] == "message_final"][-1]
        assert final["message"]["role"] == "assistant"
        assert "Hello World" in final["message"]["content"]

    @patch("app.ws_handler.ContextManager")
    @patch("app.ws_handler.llm_client_from_agent")
    def test_send_message_with_tool_calls(
        self, mock_llm_factory, mock_ctx_mgr, db_session, sample_conversation
    ):
        """send_message should detect and execute tool calls from LLM response."""
        from app.llm_client import LLMClient

        mock_ctx = MagicMock()
        mock_ctx.build_messages.return_value = [{"role": "user", "content": "列出文件"}]
        mock_ctx_mgr.return_value = mock_ctx

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.stream_sync.return_value = iter([
            'TOOL_CALL: cli({"command": "ls"})'
        ])
        mock_llm_factory.return_value = mock_llm

        ws = MagicMock()
        handle_message(ws, {
            "type": "send_message",
            "conversation_id": sample_conversation.id,
            "content": "列出文件",
        }, db_session)

        all_msgs = _all_sent(ws)
        types = [m["type"] for m in all_msgs]
        assert "tool_executing" in types
        assert "tool_result" in types

    def test_send_message_missing_fields(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "send_message"}, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_send_message_invalid_conversation(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "send_message",
            "conversation_id": "nonexistent",
            "content": "Hello",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    @patch("app.ws_handler.ContextManager")
    @patch("app.ws_handler.llm_client_from_agent")
    def test_send_message_llm_error_handled(
        self, mock_llm_factory, mock_ctx_mgr, db_session, sample_conversation
    ):
        """send_message should handle LLM exceptions gracefully."""
        from app.llm_client import LLMClient

        mock_ctx = MagicMock()
        mock_ctx.build_messages.return_value = [{"role": "user", "content": "hello"}]
        mock_ctx_mgr.return_value = mock_ctx

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.stream_sync.side_effect = RuntimeError("API error")
        mock_llm_factory.return_value = mock_llm

        ws = MagicMock()
        handle_message(ws, {
            "type": "send_message",
            "conversation_id": sample_conversation.id,
            "content": "hello",
        }, db_session)

        final = [m for m in _all_sent(ws) if m["type"] == "message_final"]
        assert len(final) > 0
        assert "生成失败" in final[-1]["message"]["content"]

    @patch("app.ws_handler.ContextManager")
    @patch("app.ws_handler.llm_client_from_agent")
    def test_send_message_updates_title_from_first_message(
        self, mock_llm_factory, mock_ctx_mgr, db_session, sample_conversation
    ):
        """First user message should update the conversation title."""
        from app.llm_client import LLMClient

        mock_ctx = MagicMock()
        mock_ctx.build_messages.return_value = [{"role": "system", "content": ""}, {"role": "user", "content": "帮我写个Python脚本分析日志"}]
        mock_ctx_mgr.return_value = mock_ctx

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.stream_sync.return_value = iter(["好的"])
        mock_llm_factory.return_value = mock_llm

        ws = MagicMock()
        handle_message(ws, {
            "type": "send_message",
            "conversation_id": sample_conversation.id,
            "content": "帮我写个Python脚本分析日志",
        }, db_session)

        # Verify conversation title was updated (truncated to 50 chars + '…')
        db_session.refresh(sample_conversation)
        assert sample_conversation.title.startswith("帮我写个Python脚本分析日志")

    # ---- Tool Calls ----

    def test_tool_call_cli(self, db_session, sample_conversation):
        ws = MagicMock()
        handle_message(ws, {
            "type": "tool_call",
            "conversation_id": sample_conversation.id,
            "tool_name": "cli",
            "arguments": {"command": "echo hello"},
        }, db_session)
        all_msgs = _all_sent(ws)
        types = [m["type"] for m in all_msgs]
        assert "tool_executing" in types
        assert "tool_result" in types

    def test_tool_call_unknown_tool(self, db_session, sample_conversation):
        ws = MagicMock()
        handle_message(ws, {
            "type": "tool_call",
            "conversation_id": sample_conversation.id,
            "tool_name": "unknown_tool_xyz",
            "arguments": {},
        }, db_session)
        result_msg = [m for m in _all_sent(ws) if m["type"] == "tool_result"][-1]
        assert result_msg["status"] == "error"
        assert "Unknown tool" in result_msg["error"]

    def test_tool_call_invalid_conversation(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "tool_call",
            "conversation_id": "nonexistent",
            "tool_name": "cli",
            "arguments": {},
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    # ---- Plans ----

    def test_create_plan(self, db_session, sample_conversation):
        ws = MagicMock()
        with patch("app.ws_handler.Planner") as mock_planner_cls, \
             patch("app.ws_handler.Orchestrator") as mock_orch_cls:
            mock_planner = MagicMock()
            mock_planner.create_plan = MagicMock()
            # Make create_plan a coroutine
            import asyncio
            async def _create_plan(*args, **kwargs):
                plan = Plan(
                    id="plan-1",
                    agent_id=sample_conversation.agent_id,
                    conversation_id=sample_conversation.id,
                    title="测试计划",
                    description="计划描述",
                    status="pending",
                )
                return plan
            mock_planner.create_plan = _create_plan
            mock_planner_cls.return_value = mock_planner

            mock_orch = MagicMock()
            mock_orch.run_pwc_cycle = MagicMock()
            async def _run_cycle():
                pass
            mock_orch.run_pwc_cycle = _run_cycle
            mock_orch_cls.return_value = mock_orch

            handle_message(ws, {
                "type": "create_plan",
                "conversation_id": sample_conversation.id,
                "goal": "完成测试",
                "context": "测试上下文",
            }, db_session)

        types = [m["type"] for m in _all_sent(ws)]
        assert "plan_created" in types
        assert "plan_updated" in types

    def test_create_plan_invalid_conversation(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "create_plan",
            "conversation_id": "nonexistent",
            "goal": "test",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_create_plan_error_handling(self, db_session, sample_conversation):
        ws = MagicMock()
        with patch("app.ws_handler.Planner") as mock_planner_cls:
            mock_planner_cls.side_effect = RuntimeError("Planner init failed")
            handle_message(ws, {
                "type": "create_plan",
                "conversation_id": sample_conversation.id,
                "goal": "test",
            }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_get_plans(self, db_session, sample_conversation):
        ws = MagicMock()
        handle_message(ws, {
            "type": "get_plans",
            "conversation_id": sample_conversation.id,
        }, db_session)
        assert _safe_sent(ws)["type"] == "plan_list"

    def test_get_plans_no_filter(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "get_plans"}, db_session)
        assert _safe_sent(ws)["type"] == "plan_list"

    # ---- Group Chat ----

    def test_get_groups(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "get_groups"}, db_session)
        assert _safe_sent(ws)["type"] == "group_list"

    def test_create_group(self, db_session, sample_agent):
        ws = MagicMock()
        handle_message(ws, {
            "type": "create_group",
            "title": "测试群",
            "topic": "测试话题",
            "mode": "discussion",
            "participant_ids": [sample_agent.id],
        }, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "group_created"
        assert msg["group"]["title"] == "测试群"

    def test_group_send(self, db_session, sample_agent):
        from app.models import GroupConversation, GroupParticipant
        group = GroupConversation(title="测试群", topic="test", mode="discussion")
        db_session.add(group)
        db_session.flush()
        db_session.add(GroupParticipant(group_id=group.id, agent_id=sample_agent.id))
        db_session.commit()

        ws = MagicMock()
        with patch("app.ws_handler.GroupChatBus") as mock_bus_cls:
            mock_bus = MagicMock()
            async def _broadcast(*args, **kwargs):
                pass
            mock_bus.broadcast = _broadcast
            mock_bus_cls.return_value = mock_bus

            handle_message(ws, {
                "type": "group_send",
                "group_id": group.id,
                "content": "大家好",
            }, db_session)

        assert _safe_sent(ws)["type"] == "group_message"

    def test_group_send_not_found(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "group_send",
            "group_id": "nonexistent",
            "content": "test",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    # ---- Memory Query ----

    def test_memory_query(self, db_session, sample_agent):
        ws = MagicMock()
        with patch("app.ws_handler.VectorMemory") as mock_vm_cls:
            mock_vm = MagicMock()
            async def _search(*args, **kwargs):
                return [{"content": "记忆片段", "score": 0.9}]
            mock_vm.search = _search
            mock_vm_cls.return_value = mock_vm

            handle_message(ws, {
                "type": "memory_query",
                "agent_id": sample_agent.id,
                "query": "测试查询",
                "k": 3,
            }, db_session)

        msg = _safe_sent(ws)
        assert msg["type"] == "memory_result"
        assert len(msg["results"]) == 1

    def test_memory_query_agent_not_found(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "memory_query",
            "agent_id": "nonexistent",
            "query": "test",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_memory_query_fallback_on_error(self, db_session, sample_agent):
        ws = MagicMock()
        with patch("app.ws_handler.VectorMemory") as mock_vm_cls:
            mock_vm = MagicMock()
            async def _search_error(*args, **kwargs):
                raise RuntimeError("ChromaDB unavailable")
            mock_vm.search = _search_error
            mock_vm_cls.return_value = mock_vm

            handle_message(ws, {
                "type": "memory_query",
                "agent_id": sample_agent.id,
                "query": "test",
            }, db_session)

        msg = _safe_sent(ws)
        assert msg["type"] == "memory_result"
        assert msg["results"] == []  # Fallback returns empty list

    # ---- Message Operations ----

    def test_edit_message(self, db_session, sample_conversation):
        msg_obj = Message(
            conversation_id=sample_conversation.id,
            role="user",
            content="原始内容",
        )
        db_session.add(msg_obj)
        db_session.commit()

        ws = MagicMock()
        handle_message(ws, {
            "type": "edit_message",
            "message_id": msg_obj.id,
            "content": "修改后的内容",
        }, db_session)

        resp = _safe_sent(ws)
        assert resp["type"] == "message_edited"
        assert resp["message"]["content"] == "修改后的内容"
        assert resp["message"]["is_edited"] is True

    def test_edit_message_not_found(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "edit_message",
            "message_id": "nonexistent",
            "content": "new",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_recall_message(self, db_session, sample_conversation):
        msg_obj = Message(
            conversation_id=sample_conversation.id,
            role="user",
            content="要撤回的消息",
        )
        db_session.add(msg_obj)
        db_session.commit()

        ws = MagicMock()
        handle_message(ws, {
            "type": "recall_message",
            "message_id": msg_obj.id,
        }, db_session)

        resp = _safe_sent(ws)
        assert resp["type"] == "message_recalled"
        assert resp["message"]["content"] == "[消息已撤回]"
        assert resp["message"]["status"] == "cancelled"

    def test_recall_message_not_found(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "recall_message",
            "message_id": "nonexistent",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    def test_reference_message(self, db_session, sample_conversation):
        msg_obj = Message(
            conversation_id=sample_conversation.id,
            role="user",
            content="被引用的消息",
        )
        db_session.add(msg_obj)
        db_session.commit()

        ws = MagicMock()
        handle_message(ws, {
            "type": "reference_message",
            "conversation_id": sample_conversation.id,
            "message_id": msg_obj.id,
            "content": "这是引用回复",
        }, db_session)

        resp = _safe_sent(ws)
        assert resp["type"] == "new_message"
        assert resp["message"]["content"] == "这是引用回复"
        assert resp["message"]["reply_to"] == msg_obj.id

    def test_reference_message_invalid_conversation(self, db_session):
        ws = MagicMock()
        handle_message(ws, {
            "type": "reference_message",
            "conversation_id": "nonexistent",
            "message_id": "msg-1",
            "content": "reply",
        }, db_session)
        assert _safe_sent(ws)["type"] == "error"

    # ---- History ----

    def test_get_history(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "get_history"}, db_session)
        assert _safe_sent(ws)["type"] == "history_list"

    def test_get_history_with_conversation(self, db_session, sample_conversation):
        ws = MagicMock()
        handle_message(ws, {
            "type": "get_history",
            "conversation_id": sample_conversation.id,
        }, db_session)
        assert _safe_sent(ws)["type"] == "history_list"

    # ---- Unknown type ----

    def test_unknown_message_type(self, db_session):
        ws = MagicMock()
        handle_message(ws, {"type": "nonexistent_type_xyz"}, db_session)
        msg = _safe_sent(ws)
        assert msg["type"] == "error"
        assert "Unknown message type" in msg["message"]


# ---------------------------------------------------------------------------
# _execute_single_tool — each tool type
# ---------------------------------------------------------------------------

class TestExecuteSingleTool:
    def test_cli_tool_echo(self):
        result = _execute_single_tool(
            "cli", {"command": "echo hello"}, {}, {},
        )
        assert result["success"] is True
        assert "hello" in result["output"]

    def test_cli_tool_failure(self):
        result = _execute_single_tool(
            "cli", {"command": "nonexistent_command_xyz_123"}, {}, {},
        )
        assert result["success"] is False
        assert result["error"] != ""

    def test_unknown_tool(self):
        result = _execute_single_tool(
            "unknown_xyz", {}, {}, {},
        )
        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    def test_tool_exception_handled(self):
        with patch("app.ws_handler.CLITool") as mock_cli:
            mock_cli.side_effect = ValueError("Init error")
            result = _execute_single_tool(
                "cli", {"command": "ls"}, {}, {},
            )
            assert result["success"] is False
            assert "Init error" in result["error"]

    def test_cli_tool_respects_blocked_commands(self):
        """Command matching built-in blocked patterns or blocklist should be rejected."""
        result = _execute_single_tool(
            "cli",
            {"command": "rm -rf /"},
            {"cli": {"allowed_commands": [], "blocked_commands": ["rm"]}},
            {},
        )
        assert result["success"] is False
        # Either blocked by pattern or blocked by command list — both mean blocked
        assert result["error"] != ""

    @patch("app.ws_handler.UITool")
    def test_ui_tool_mocked(self, mock_ui_cls):
        mock_ui = MagicMock()
        mock_ui.execute = MagicMock()
        async def _exec(*args, **kwargs):
            return MagicMock(success=True, output="clicked at (100,200)", error="")
        mock_ui.execute = _exec
        mock_ui_cls.return_value = mock_ui

        result = _execute_single_tool(
            "ui", {"action": "click", "params": {"x": 100, "y": 200}}, {}, {},
        )
        assert result["success"] is True

    @patch("app.ws_handler.VisionTool")
    def test_vision_tool_mocked(self, mock_vision_cls):
        mock_vision = MagicMock()
        async def _analyze(*args, **kwargs):
            return MagicMock(success=True, analysis="一张截图描述", error="")
        mock_vision.analyze = _analyze
        mock_vision_cls.return_value = mock_vision

        result = _execute_single_tool(
            "vision",
            {"image_source": "screenshot", "prompt": "描述图片"},
            {},
            {"openai": "sk-fake"},
        )
        assert result["success"] is True
        assert result["output"] == "一张截图描述"


# ---------------------------------------------------------------------------
# _execute_tool_calls
# ---------------------------------------------------------------------------

class TestExecuteToolCalls:
    def test_executes_each_call_and_logs(self, db_session, sample_agent):
        ws = MagicMock()
        tool_calls = [
            {"name": "cli", "arguments": {"command": "echo hello"}},
            {"name": "cli", "arguments": {"command": "echo world"}},
        ]

        _execute_tool_calls(
            ws, db_session,
            agent=sample_agent,
            conversation_id="conv-1",
            assistant_msg=MagicMock(id="msg-1"),
            tool_calls=tool_calls,
        )

        all_msgs = _all_sent(ws)
        tool_exec = [m for m in all_msgs if m["type"] == "tool_executing"]
        tool_res = [m for m in all_msgs if m["type"] == "tool_result"]
        assert len(tool_exec) == 2
        assert len(tool_res) == 2

        # Verify TaskExecution records were created
        records = db_session.query(TaskExecution).all()
        assert len(records) == 2

    def test_handles_mixed_tool_results(self, db_session, sample_agent):
        ws = MagicMock()
        tool_calls = [
            {"name": "unknown_tool", "arguments": {}},
            {"name": "cli", "arguments": {"command": "ls"}},
        ]

        _execute_tool_calls(
            ws, db_session,
            agent=sample_agent,
            conversation_id="conv-1",
            assistant_msg=MagicMock(id="msg-2"),
            tool_calls=tool_calls,
        )

        all_msgs = _all_sent(ws)
        tool_res = [m for m in all_msgs if m["type"] == "tool_result"]
        assert len(tool_res) == 2
        statuses = [r["status"] for r in tool_res]
        assert "error" in statuses  # unknown tool
        assert "success" in statuses  # cli tool


# ---------------------------------------------------------------------------
# handle_websocket — loop integration
# ---------------------------------------------------------------------------

class TestHandleWebsocket:
    def test_receives_and_dispatches(self, db_session):
        """Simulate WebSocket receive loop with one valid message."""
        ws = MagicMock()
        ws.receive.side_effect = [
            json.dumps({"type": "ping"}),
            None,  # signals end of connection
        ]

        with patch("app.ws_handler.SessionLocal", return_value=db_session):
            handle_websocket(ws)

        # Should have sent a pong response
        ws.send.assert_called()
        sent = json.loads(ws.send.call_args[0][0])
        assert sent["type"] == "pong"

    def test_handles_invalid_json(self, db_session):
        ws = MagicMock()
        ws.receive.side_effect = [
            "not valid json{{{",
            None,
        ]

        with patch("app.ws_handler.SessionLocal", return_value=db_session):
            handle_websocket(ws)

        sent = _safe_sent(ws)
        assert sent["type"] == "error"
        assert "Invalid JSON" in sent["message"]

    def test_handles_error_in_handler(self, db_session):
        """If handle_message raises, the loop should catch and send error."""
        ws = MagicMock()
        ws.receive.side_effect = [
            json.dumps({"type": "send_message", "content": ""}),
            None,
        ]

        with patch("app.ws_handler.SessionLocal", return_value=db_session):
            handle_websocket(ws)

        sent = _safe_sent(ws)
        assert sent["type"] == "error"

    def test_multiple_messages(self, db_session, sample_agent):
        ws = MagicMock()
        ws.receive.side_effect = [
            json.dumps({"type": "ping"}),
            json.dumps({"type": "get_agents"}),
            None,
        ]

        with patch("app.ws_handler.SessionLocal", return_value=db_session):
            handle_websocket(ws)

        all_msgs = _all_sent(ws)
        types = [m["type"] for m in all_msgs]
        assert "pong" in types
        assert "agent_list" in types

    def test_close_connection_on_none(self, db_session):
        """When receive returns None, the loop should exit cleanly."""
        ws = MagicMock()
        ws.receive.return_value = None

        with patch("app.ws_handler.SessionLocal", return_value=db_session):
            handle_websocket(ws)

        # No messages should be sent
        ws.send.assert_not_called()


# ---------------------------------------------------------------------------
# _run_async
# ---------------------------------------------------------------------------

class TestRunAsync:
    def test_runs_coroutine(self):
        import asyncio
        async def _hello():
            return "hello"
        result = _run_async(_hello())
        assert result == "hello"

    def test_runs_with_args(self):
        import asyncio
        async def _add(a, b):
            return a + b
        result = _run_async(_add(3, 4))
        assert result == 7

    def test_propagates_exceptions(self):
        import asyncio
        async def _fail():
            raise ValueError("test error")
        with pytest.raises(ValueError, match="test error"):
            _run_async(_fail())
