"""
LLM Client — unified interface for OpenAI, Anthropic, and future providers.
"""
import json
import asyncio
import logging
from queue import Queue
from threading import Thread
from typing import AsyncGenerator, Generator, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: str = ""
    api_base_url: str = ""


class LLMClient:
    """Unified LLM client — factory that selects the right backend."""

    def __init__(self, config: LLMConfig):
        self.config = config

    async def complete(self, messages: list[dict]) -> str:
        """Non-streaming completion. Returns the full response text."""
        result = ""
        async for chunk in self.stream(messages):
            result += chunk
        return result

    def stream_sync(self, messages: list[dict]) -> Generator[str, None, None]:
        """Synchronous streaming — drives async iteration via a daemon thread.
        Suitable for sync contexts like Flask-Sock handlers.
        """
        q: Queue = Queue(maxsize=64)

        async def _produce():
            try:
                async for chunk in self.stream(messages):
                    q.put(("chunk", chunk))
                q.put(("done", None))
            except Exception as e:
                logger.error(f"Sync stream produce error: {e}")
                q.put(("error", e))

        def _run():
            asyncio.run(_produce())

        t = Thread(target=_run, daemon=True)
        t.start()

        while True:
            msg_type, payload = q.get()
            if msg_type == "chunk":
                yield payload
            elif msg_type == "done":
                break
            elif msg_type == "error":
                yield f"\n\n[流式生成错误: {payload}]"
                break

    async def stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Streaming completion. Yields text chunks as they arrive."""
        if self.config.provider == "anthropic":
            async for chunk in self._stream_anthropic(messages):
                yield chunk
        else:
            # openai, custom, or any OpenAI-compatible provider
            async for chunk in self._stream_openai(messages):
                yield chunk

    async def _stream_openai(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        from openai import AsyncOpenAI

        kwargs = {"api_key": self.config.api_key}
        if self.config.api_base_url:
            kwargs["base_url"] = self.config.api_base_url
        client = AsyncOpenAI(**kwargs)
        try:
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield f"\n\n[错误: {e}]"

    async def _stream_anthropic(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        from anthropic import AsyncAnthropic

        kwargs = {"api_key": self.config.api_key}
        if self.config.api_base_url:
            kwargs["base_url"] = self.config.api_base_url
        client = AsyncAnthropic(**kwargs)
        try:
            # Convert OpenAI-style messages to Anthropic format
            system_msg = None
            anthropic_messages = []
            for m in messages:
                if m["role"] == "system":
                    system_msg = m["content"]
                elif m["role"] == "user":
                    anthropic_messages.append({"role": "user", "content": m["content"]})
                elif m["role"] == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": m["content"]})

            async with client.messages.stream(
                model=self.config.model,
                messages=anthropic_messages,
                system=system_msg,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            yield f"\n\n[错误: {e}]"


def llm_client_from_agent(agent, api_keys: dict) -> LLMClient:
    """Create an LLMClient from an Agent model instance.

    Uses the agent's own api_key if set, otherwise falls back to the server
    environment variable for the selected provider.
    """
    provider = agent.model_provider or "openai"
    api_key = agent.api_key or api_keys.get(provider, "")
    api_base_url = (agent.api_base_url or "").strip()

    # Auto-append /v1 for OpenAI-compatible APIs if missing
    if api_base_url and provider != "anthropic" and not api_base_url.rstrip("/").endswith("/v1"):
        api_base_url = api_base_url.rstrip("/") + "/v1"

    return LLMClient(LLMConfig(
        provider=provider,
        model=agent.model_name or "gpt-4o",
        temperature=agent.temperature or 0.7,
        max_tokens=agent.max_tokens or 4096,
        api_key=api_key,
        api_base_url=api_base_url,
    ))
