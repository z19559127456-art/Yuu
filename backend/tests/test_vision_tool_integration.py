"""
Vision Tool 集成测试 — Mock API 调用测试图片分析、错误处理、取消机制。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import asyncio
import pytest
import tempfile
import types
from unittest.mock import AsyncMock, MagicMock, patch

from app.vision_tool import VisionTool, VisionResult


# ---------------------------------------------------------------------------
# 注入 mock openai / anthropic 模块
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _create_temp_png() -> str:
    """创建一个最小的临时 PNG 文件用于测试。"""
    import struct
    import zlib

    def _chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\xff")

    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(png)
    tmp.close()
    return tmp.name


def _get_openai_mock():
    """获取注入的 openai mock client。"""
    from openai import AsyncOpenAI  # type: ignore[import-untyped]
    return AsyncOpenAI


def _get_anthropic_mock():
    """获取注入的 anthropic mock client。"""
    from anthropic import AsyncAnthropic  # type: ignore[import-untyped]
    return AsyncAnthropic


# ---------------------------------------------------------------------------
# VisionTool.analyze() — 基础检查
# ---------------------------------------------------------------------------

class TestVisionToolAnalyze:

    @pytest.mark.asyncio
    async def test_empty_image_paths(self):
        tool = VisionTool(api_key="sk-test")
        result = await tool.analyze([])
        assert result.success is False
        assert "未提供图片路径" in result.error

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        tool = VisionTool(api_key="")
        result = await tool.analyze(["test.png"])
        assert result.success is False
        assert "缺少" in result.error and "API Key" in result.error

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        tool = VisionTool(api_key="sk-test")
        result = await tool.analyze(["/nonexistent/path/image.png"])
        assert result.success is False
        assert "文件不存在" in result.error

    @pytest.mark.asyncio
    async def test_cancel_token_set(self):
        png_path = _create_temp_png()
        try:
            tool = VisionTool(api_key="sk-test")
            cancel = asyncio.Event()
            cancel.set()
            result = await tool.analyze([png_path], cancel_token=cancel)
            assert result.success is False
            assert "已取消" in result.error
        finally:
            os.unlink(png_path)


# ---------------------------------------------------------------------------
# OpenAI Vision
# ---------------------------------------------------------------------------

class TestOpenAIVision:

    @pytest.mark.asyncio
    async def test_analyze_openai_success(self):
        png_path = _create_temp_png()
        try:
            tool = VisionTool(api_key="sk-test", provider="openai", model="gpt-4o")

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "图片描述：一只猫"
            mock_response.usage = MagicMock()
            mock_response.usage.prompt_tokens = 100
            mock_response.usage.completion_tokens = 50
            mock_response.usage.total_tokens = 150

            _get_openai_mock().return_value.chat.completions.create = AsyncMock(
                return_value=mock_response)

            result = await tool.analyze([png_path], prompt="描述这张图片")

            assert result.success is True
            assert "一只猫" in result.analysis
            assert result.model_used == "gpt-4o"
            assert result.token_usage["prompt_tokens"] == 100
            assert result.token_usage["completion_tokens"] == 50
            assert result.token_usage["total_tokens"] == 150
        finally:
            os.unlink(png_path)

    @pytest.mark.asyncio
    async def test_analyze_openai_multiple_images(self):
        png1 = _create_temp_png()
        png2 = _create_temp_png()
        try:
            tool = VisionTool(api_key="sk-test", provider="openai")

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "两张图片的对比分析"
            mock_response.usage = None

            mock_create = AsyncMock(return_value=mock_response)
            _get_openai_mock().return_value.chat.completions.create = mock_create

            result = await tool.analyze([png1, png2])

            assert result.success is True
            call_args = mock_create.call_args
            content = call_args.kwargs["messages"][0]["content"]
            image_parts = [c for c in content if c["type"] == "image_url"]
            assert len(image_parts) == 2
        finally:
            os.unlink(png1)
            os.unlink(png2)

    @pytest.mark.asyncio
    async def test_analyze_openai_api_error(self):
        png_path = _create_temp_png()
        try:
            tool = VisionTool(api_key="sk-test", provider="openai")

            _get_openai_mock().return_value.chat.completions.create = AsyncMock(
                side_effect=Exception("Rate limit exceeded"))

            result = await tool.analyze([png_path])

            assert result.success is False
            assert "Rate limit exceeded" in result.error
        finally:
            os.unlink(png_path)


# ---------------------------------------------------------------------------
# Anthropic Vision
# ---------------------------------------------------------------------------

class TestAnthropicVision:

    @pytest.mark.asyncio
    async def test_analyze_anthropic_success(self):
        png_path = _create_temp_png()
        try:
            tool = VisionTool(
                api_key="sk-ant-test",
                provider="anthropic",
                model="claude-sonnet-4-6",
            )

            mock_block = MagicMock()
            mock_block.type = "text"
            mock_block.text = "这是一张测试图片。"

            mock_response = MagicMock()
            mock_response.content = [mock_block]
            mock_response.usage = MagicMock()
            mock_response.usage.input_tokens = 80
            mock_response.usage.output_tokens = 20

            _get_anthropic_mock().return_value.messages.create = AsyncMock(
                return_value=mock_response)

            result = await tool.analyze([png_path], prompt="描述这张图")

            assert result.success is True
            assert "测试图片" in result.analysis
            assert result.model_used == "claude-sonnet-4-6"
            assert result.token_usage["input_tokens"] == 80
            assert result.token_usage["output_tokens"] == 20
        finally:
            os.unlink(png_path)

    @pytest.mark.asyncio
    async def test_analyze_anthropic_api_error(self):
        png_path = _create_temp_png()
        try:
            tool = VisionTool(api_key="sk-ant-test", provider="anthropic")

            _get_anthropic_mock().return_value.messages.create = AsyncMock(
                side_effect=Exception("Invalid API key"))

            result = await tool.analyze([png_path])

            assert result.success is False
            assert "Invalid API key" in result.error
        finally:
            os.unlink(png_path)


# ---------------------------------------------------------------------------
# Unknown Provider
# ---------------------------------------------------------------------------

class TestUnknownProvider:

    @pytest.mark.asyncio
    async def test_unknown_provider_error(self):
        png_path = _create_temp_png()
        try:
            tool = VisionTool(api_key="test", provider="unknown_provider")
            result = await tool.analyze([png_path])
            assert result.success is False
            assert "不支持的 provider" in result.error
        finally:
            os.unlink(png_path)


# ---------------------------------------------------------------------------
# from_agent_config
# ---------------------------------------------------------------------------

class TestFromAgentConfig:

    def test_creates_tool_with_openai_defaults(self, db_session):
        import json
        from app.models import Agent
        agent = Agent(
            name="VisionTest",
            system_prompt="",
            model_provider="openai",
            model_name="gpt-4o",
        )
        tool = VisionTool.from_agent_config(agent, api_key="sk-test")
        assert tool.provider == "openai"
        assert tool.model == "gpt-4o"
        assert tool.api_key == "sk-test"

    def test_creates_tool_from_vision_config(self, db_session):
        import json
        from app.models import Agent
        agent = Agent(
            name="VisionBot",
            system_prompt="",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            tools_config_json=json.dumps({
                "vision": {
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-6",
                },
            }),
        )
        tool = VisionTool.from_agent_config(agent, api_key="sk-ant-key")
        assert tool.provider == "anthropic"
        assert tool.model == "claude-sonnet-4-6"
        assert tool.api_key == "sk-ant-key"


# ---------------------------------------------------------------------------
# VisionResult dataclass
# ---------------------------------------------------------------------------

class TestVisionResult:

    def test_default_values(self):
        result = VisionResult(success=True)
        assert result.success is True
        assert result.analysis == ""
        assert result.output_type == "text"
        assert result.model_used == ""
        assert result.token_usage == {}
        assert result.error == ""

    def test_full_result(self):
        result = VisionResult(
            success=True,
            analysis="分析内容",
            model_used="gpt-4o",
            token_usage={"total_tokens": 100},
        )
        assert result.analysis == "分析内容"
        assert result.model_used == "gpt-4o"
