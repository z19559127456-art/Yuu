"""
LLM Client 集成测试 — 使用 mock API 测试流式输出、错误处理和工厂函数。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm_client import LLMClient, LLMConfig, llm_client_from_agent
from app.models import Agent


# ---------------------------------------------------------------------------
# Mock 工具 — 注入假的 openai / anthropic 模块到 sys.modules
# ---------------------------------------------------------------------------

class _FakeDelta:
    """模拟 OpenAI delta 对象（content 属性直接可设）。"""
    def __init__(self, content: str | None = None):
        self.content = content


class _FakeChoice:
    """模拟 OpenAI choice 对象。"""
    def __init__(self, delta: _FakeDelta | None = None):
        self.delta = delta or _FakeDelta()


class _FakeChunk:
    """模拟 OpenAI streaming chunk 对象。"""
    def __init__(self, text: str | None = None, *, empty_choices: bool = False):
        if empty_choices:
            self.choices = []
        else:
            self.choices = [_FakeChoice(_FakeDelta(text))]


class MockAsyncStream:
    """真正的 async iterator — 不依赖 MagicMock，直接实现 __aiter__/__anext__。

    OpenAI SDK 的 Stream 对象通过 async for 迭代，要求返回的对象本身
    实现 __aiter__ (return self) + __anext__ (async, yield items)。
    """
    def __init__(self, items: list):
        self._items = items
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._idx]
        self._idx += 1
        return item


def _setup_openai_mock(chunks: list, side_effect=None):
    """配置 openai.AsyncOpenAI mock，使其返回指定的 stream chunks。"""
    from openai import AsyncOpenAI  # type: ignore[import-untyped]

    mock_create = AsyncMock(side_effect=side_effect)
    if side_effect is None:
        mock_create.return_value = MockAsyncStream(chunks)

    AsyncOpenAI.return_value.chat.completions.create = mock_create
    return AsyncOpenAI


def _setup_anthropic_mock(texts: list[str], side_effect=None):
    """配置 anthropic.AsyncAnthropic mock。"""
    from anthropic import AsyncAnthropic  # type: ignore[import-untyped]

    mock_client = MagicMock()

    if side_effect is None:
        async def _mock_text_stream():
            for t in texts:
                yield t

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=MagicMock(
            text_stream=_mock_text_stream(),
        ))
        mock_client.messages.stream.return_value = mock_stream_ctx
    else:
        mock_client.messages.stream = MagicMock(side_effect=side_effect)

    AsyncAnthropic.return_value = mock_client
    return AsyncAnthropic, mock_client


# ---------------------------------------------------------------------------
# LLMClient.complete()
# ---------------------------------------------------------------------------

class TestLLMClientComplete:

    @pytest.mark.asyncio
    async def test_complete_openai_mocked(self):
        """complete() 应返回连接所有 stream chunk 的完整文本。"""
        config = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test")
        client = LLMClient(config)

        _setup_openai_mock([_FakeChunk("Hello"), _FakeChunk(" World"), _FakeChunk("!")])

        result = await client.complete([{"role": "user", "content": "Hi"}])
        assert result == "Hello World!"

    @pytest.mark.asyncio
    async def test_complete_empty_response(self):
        """空响应应返回空字符串。"""
        config = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test")
        client = LLMClient(config)

        _setup_openai_mock([])

        result = await client.complete([{"role": "user", "content": "Hi"}])
        assert result == ""

    @pytest.mark.asyncio
    async def test_complete_unknown_provider_falls_back_to_openai(self):
        """未知 provider 会被路由到 OpenAI 兼容路径（当前代码的逻辑）。"""
        config = LLMConfig(provider="unknown_provider", api_key="sk-test")
        client = LLMClient(config)

        _setup_openai_mock([_FakeChunk("fallback")])

        result = await client.complete([{"role": "user", "content": "Hi"}])
        # 未知 provider 走 OpenAI 路径，应返回 mock 内容
        assert result == "fallback"


# ---------------------------------------------------------------------------
# LLMClient.stream()
# ---------------------------------------------------------------------------

class TestLLMClientStream:

    @pytest.mark.asyncio
    async def test_stream_openai_yields_chunks(self):
        """stream() 应逐个产出文本块。"""
        config = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test")
        client = LLMClient(config)

        _setup_openai_mock([_FakeChunk("A"), _FakeChunk("B"), _FakeChunk("C")])

        received = []
        async for chunk in client.stream([{"role": "user", "content": "Hi"}]):
            received.append(chunk)

        assert received == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_stream_skips_none_delta(self):
        """delta.content 为 None 时应跳过（不产出空字符串）。"""
        config = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test")
        client = LLMClient(config)

        chunk_no_delta = _FakeChunk(empty_choices=True)
        chunk_no_content = _FakeChunk(text=None)
        chunk_valid = _FakeChunk("OK")

        _setup_openai_mock([chunk_no_delta, chunk_no_content, chunk_valid])

        received = []
        async for chunk in client.stream([{"role": "user", "content": "Hi"}]):
            received.append(chunk)

        assert received == ["OK"]

    @pytest.mark.asyncio
    async def test_stream_openai_error_handling(self):
        """OpenAI API 错误时应在产出错误消息后正常结束。"""
        config = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test")
        client = LLMClient(config)

        _setup_openai_mock([], side_effect=Exception("API rate limit"))

        received = []
        async for chunk in client.stream([{"role": "user", "content": "Hi"}]):
            received.append(chunk)

        assert any("错误" in c for c in received)
        assert any("API rate limit" in c for c in received)

    @pytest.mark.asyncio
    async def test_stream_anthropic_mocked(self):
        """Anthropic provider 应正确转换消息格式并产出文本。"""
        config = LLMConfig(provider="anthropic", model="claude-sonnet-4-6", api_key="sk-ant-test")
        client = LLMClient(config)

        _, mock_client = _setup_anthropic_mock(["Hello", " from", " Claude"])

        received = []
        async for chunk in client.stream([
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]):
            received.append(chunk)

        assert "".join(received) == "Hello from Claude"
        call_args = mock_client.messages.stream.call_args
        assert call_args.kwargs["system"] == "You are helpful."
        assert len(call_args.kwargs["messages"]) == 1

    @pytest.mark.asyncio
    async def test_stream_anthropic_error_handling(self):
        """Anthropic API 错误时应产出错误消息。"""
        config = LLMConfig(provider="anthropic", model="claude-sonnet-4-6", api_key="sk-ant-test")
        client = LLMClient(config)

        _setup_anthropic_mock([], side_effect=Exception("Auth error"))

        received = []
        async for chunk in client.stream([{"role": "user", "content": "Hi"}]):
            received.append(chunk)

        assert any("错误" in c for c in received)
        assert any("Auth error" in c for c in received)


# ---------------------------------------------------------------------------
# LLMClient.stream_sync()
# ---------------------------------------------------------------------------

class TestLLMClientStreamSync:

    def test_stream_sync_yields_all_chunks(self):
        """同步流应产出所有块并通过 queue 正确传递。"""
        config = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test")
        client = LLMClient(config)

        _setup_openai_mock([_FakeChunk("Part1"), _FakeChunk("Part2")])

        received = list(client.stream_sync([{"role": "user", "content": "Hi"}]))
        assert received == ["Part1", "Part2"]

    def test_stream_sync_error_handling(self):
        """API 错误时同步流应产出错误标记。"""
        config = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test")
        client = LLMClient(config)

        _setup_openai_mock([], side_effect=Exception("Connection timeout"))

        received = list(client.stream_sync([{"role": "user", "content": "Hi"}]))
        # stream_sync 将 API 错误作为流内容传递（由 _stream_openai 的异常处理产出）
        assert any("错误" in c and "Connection timeout" in c for c in received)


# ---------------------------------------------------------------------------
# llm_client_from_agent()
# ---------------------------------------------------------------------------

class TestLLMClientFromAgent:

    def test_factory_creates_openai_client(self, db_session, sample_agent_dict):
        """工厂函数应从 Agent 模型创建正确配置的 client。"""
        agent = Agent(**sample_agent_dict)
        api_keys = {"openai": "sk-test-123", "anthropic": "sk-ant-test"}

        client = llm_client_from_agent(agent, api_keys)

        assert client.config.provider == "openai"
        assert client.config.model == "gpt-4o"
        assert client.config.temperature == 0.7
        assert client.config.max_tokens == 4096
        assert client.config.api_key == "sk-test-123"

    def test_factory_defaults(self, db_session):
        """缺失字段应使用合理的默认值。"""
        agent = Agent(name="Minimal", system_prompt="Be helpful.")
        api_keys = {}

        client = llm_client_from_agent(agent, api_keys)

        assert client.config.provider == "openai"
        assert client.config.model == "gpt-4o"
        assert client.config.temperature == 0.7
        assert client.config.api_key == ""

    def test_factory_anthropic_agent(self, db_session):
        """Anthropic provider 的 Agent 应正确配置。"""
        agent = Agent(
            name="Claude助手",
            system_prompt="You are Claude.",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            temperature=0.3,
        )
        api_keys = {"anthropic": "sk-ant-key"}

        client = llm_client_from_agent(agent, api_keys)

        assert client.config.provider == "anthropic"
        assert client.config.model == "claude-opus-4-7"
        assert client.config.temperature == 0.3
        assert client.config.api_key == "sk-ant-key"


# ---------------------------------------------------------------------------
# LLMConfig
# ---------------------------------------------------------------------------

class TestLLMConfig:

    def test_default_values(self):
        cfg = LLMConfig()
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 4096
        assert cfg.api_key == ""

    def test_custom_values(self):
        cfg = LLMConfig(
            provider="anthropic",
            model="claude-haiku-4-5",
            temperature=0.3,
            max_tokens=1000,
            api_key="sk-custom",
        )
        assert cfg.provider == "anthropic"
        assert cfg.model == "claude-haiku-4-5"
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 1000
        assert cfg.api_key == "sk-custom"
