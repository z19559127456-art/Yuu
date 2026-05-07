"""
Tests for ws_handler pure helper functions — _extract_tool_calls, _send_json, etc.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from app.ws_handler import _extract_tool_calls, _get_api_keys, _send_json


class TestExtractToolCalls:
    def test_extract_single_tool_call(self):
        content = 'TOOL_CALL: cli({"command": "ls -la"})'
        calls = _extract_tool_calls(content)
        assert len(calls) == 1
        assert calls[0]["name"] == "cli"
        assert calls[0]["arguments"]["command"] == "ls -la"

    def test_extract_multiple_tool_calls(self):
        content = (
            'TOOL_CALL: cli({"command": "ls"})\n'
            'TOOL_CALL: web({"action": "navigate", "url": "https://example.com"})'
        )
        calls = _extract_tool_calls(content)
        assert len(calls) == 2
        assert calls[0]["name"] == "cli"
        assert calls[1]["name"] == "web"

    def test_extract_json_tool_calls(self):
        content = (
            '```json {"tool_calls": [{"name": "cli", "arguments": {"command": "ls"}}]} ```'
        )
        calls = _extract_tool_calls(content)
        assert len(calls) == 1
        assert calls[0]["name"] == "cli"

    def test_no_tool_calls_in_plain_text(self):
        content = "This is a regular response with no tool calls."
        calls = _extract_tool_calls(content)
        assert calls == []

    def test_empty_content(self):
        calls = _extract_tool_calls("")
        assert calls == []

    def test_invalid_json_in_tool_call(self):
        """Invalid JSON in tool call arguments should be ignored."""
        content = 'TOOL_CALL: cli({invalid json})'
        calls = _extract_tool_calls(content)
        assert calls == []

    def test_mixed_valid_and_invalid(self):
        content = (
            'TOOL_CALL: cli({invalid})\n'
            'TOOL_CALL: web({"action": "screenshot"})'
        )
        calls = _extract_tool_calls(content)
        assert len(calls) == 1
        assert calls[0]["name"] == "web"


class TestSendJson:
    def test_send_json_calls_ws_send(self):
        ws = MagicMock()
        data = {"type": "pong"}
        _send_json(ws, data)
        ws.send.assert_called_once()
        # Verify JSON was sent
        sent = json.loads(ws.send.call_args[0][0])
        assert sent["type"] == "pong"

    def test_send_json_with_chinese(self):
        ws = MagicMock()
        data = {"type": "error", "message": "出错了"}
        _send_json(ws, data)
        sent = json.loads(ws.send.call_args[0][0])
        assert sent["message"] == "出错了"


class TestGetApiKeys:
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-123', 'ANTHROPIC_API_KEY': 'sk-ant-test'})
    def test_reads_keys_from_env(self):
        keys = _get_api_keys()
        assert keys["openai"] == "sk-test-123"
        assert keys["anthropic"] == "sk-ant-test"

    @patch.dict('os.environ', {}, clear=True)
    def test_returns_empty_strings_when_no_keys(self):
        keys = _get_api_keys()
        assert keys["openai"] == ""
        assert keys["anthropic"] == ""
