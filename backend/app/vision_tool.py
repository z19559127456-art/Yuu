"""
Vision Tool — image analysis via OpenAI / Anthropic Vision APIs.
"""
import base64
import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VisionResult:
    success: bool
    analysis: str = ""
    output_type: str = "text"
    model_used: str = ""
    token_usage: dict = field(default_factory=dict)
    error: str = ""
    execution_time_ms: int = 0
    metadata: dict = field(default_factory=dict)


class VisionTool:
    """Vision API tool supporting OpenAI and Anthropic providers."""

    def __init__(
        self,
        api_key: str = "",
        provider: str = "openai",
        model: str = "",
        max_tokens: int = 4096,
    ):
        self.api_key = api_key
        self.provider = provider
        self.model = model or ("gpt-4o" if provider == "openai" else "claude-3-5-sonnet-20241022")
        self.max_tokens = max_tokens

    async def analyze(
        self,
        image_paths: list[str],
        prompt: str = "请详细描述这张图片的内容。",
        cancel_token: asyncio.Event | None = None,
    ) -> VisionResult:
        """Analyze one or more images via the configured vision model."""
        import time

        start = time.monotonic()

        if not image_paths:
            return VisionResult(
                success=False,
                error="未提供图片路径",
                execution_time_ms=int((time.monotonic() - start) * 1000),
            )

        if not self.api_key:
            return VisionResult(
                success=False,
                error=f"缺少 {self.provider} API Key",
                execution_time_ms=int((time.monotonic() - start) * 1000),
            )

        try:
            images_data = []
            for path in image_paths:
                if not os.path.isfile(path):
                    return VisionResult(
                        success=False,
                        error=f"文件不存在: {path}",
                        execution_time_ms=int((time.monotonic() - start) * 1000),
                    )
                with open(path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                images_data.append(encoded)

            if cancel_token and cancel_token.is_set():
                return VisionResult(
                    success=False,
                    error="操作已取消",
                    execution_time_ms=int((time.monotonic() - start) * 1000),
                )

            if self.provider == "openai":
                result = await self._analyze_openai(images_data, prompt)
            elif self.provider == "anthropic":
                result = await self._analyze_anthropic(images_data, prompt)
            else:
                result = VisionResult(
                    success=False,
                    error=f"不支持的 provider: {self.provider}",
                )

            result.execution_time_ms = int((time.monotonic() - start) * 1000)
            return result

        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            return VisionResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.monotonic() - start) * 1000),
            )

    async def _analyze_openai(self, images_data: list[str], prompt: str) -> VisionResult:
        """Analyze images using OpenAI GPT-4o Vision."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)

        content: list[dict] = [{"type": "text", "text": prompt}]
        for encoded in images_data:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{encoded}",
                    "detail": "auto",
                },
            })

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                max_tokens=self.max_tokens,
            )

            usage = response.usage
            return VisionResult(
                success=True,
                analysis=response.choices[0].message.content or "",
                model_used=self.model,
                token_usage={
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
            )
        except Exception as e:
            return VisionResult(
                success=False,
                error=f"OpenAI Vision 调用失败: {e}",
                model_used=self.model,
            )

    async def _analyze_anthropic(self, images_data: list[str], prompt: str) -> VisionResult:
        """Analyze images using Anthropic Claude Vision."""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)

        content: list[dict] = [{"type": "text", "text": prompt}]
        for encoded in images_data:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": encoded,
                },
            })

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": content}],
            )

            usage = response.usage
            return VisionResult(
                success=True,
                analysis="".join(block.text for block in response.content if block.type == "text"),
                model_used=self.model,
                token_usage={
                    "input_tokens": usage.input_tokens if usage else 0,
                    "output_tokens": usage.output_tokens if usage else 0,
                },
            )
        except Exception as e:
            return VisionResult(
                success=False,
                error=f"Anthropic Vision 调用失败: {e}",
                model_used=self.model,
            )

    @staticmethod
    def from_agent_config(agent, api_key: str = "") -> "VisionTool":
        """Create a VisionTool from an Agent's tools_config."""
        import json as _json
        cfg = _json.loads(agent.tools_config_json or "{}")
        vision_cfg = cfg.get("vision", {})
        return VisionTool(
            api_key=api_key,
            provider=vision_cfg.get("provider", agent.model_provider or "openai"),
            model=vision_cfg.get(
                "model",
                agent.model_name or "gpt-4o",
            ),
        )
