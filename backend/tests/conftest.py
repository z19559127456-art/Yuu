"""
Pytest fixtures for all tests.
"""
import os
import sys
import json
import types
import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Ensure app module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.database import Base
from app.config import config


# ---------------------------------------------------------------------------
# 全局 mock SDK 模块注入 — 避免各测试文件重复注入导致冲突
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="session")
def _mock_external_sdk_modules():
    """会话级：为所有测试注入 mock 的 openai / anthropic / playwright / pyautogui 模块。"""
    saved = {}

    # --- openai ---
    if "openai" not in sys.modules:
        mock_openai = types.ModuleType("openai")
        mock_openai.AsyncOpenAI = MagicMock()
        mock_openai.AsyncOpenAI.return_value.chat.completions.create = AsyncMock()
        saved["openai"] = sys.modules.get("openai")
        sys.modules["openai"] = mock_openai

    # --- anthropic ---
    if "anthropic" not in sys.modules:
        mock_anthropic = types.ModuleType("anthropic")
        mock_anthropic.AsyncAnthropic = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value.messages.create = AsyncMock()
        mock_anthropic.AsyncAnthropic.return_value.messages.stream = MagicMock()
        saved["anthropic"] = sys.modules.get("anthropic")
        sys.modules["anthropic"] = mock_anthropic

    # --- playwright ---
    if "playwright" not in sys.modules:
        mock_playwright = types.ModuleType("playwright")
        mock_async_api = types.ModuleType("playwright.async_api")

        mock_page = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example Page")
        mock_page.goto = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake-png-data")
        mock_page.inner_text = AsyncMock(return_value="Hello World")
        mock_page.inner_html = AsyncMock(return_value="<div>Test</div>")
        mock_page.evaluate = AsyncMock(return_value=42)
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_pw_instance.__aenter__ = AsyncMock(return_value=mock_pw_instance)
        mock_pw_instance.__aexit__ = AsyncMock(return_value=None)

        mock_async_api.async_playwright = MagicMock(return_value=mock_pw_instance)
        mock_playwright.async_api = mock_async_api

        saved["playwright"] = sys.modules.get("playwright")
        saved["playwright.async_api"] = sys.modules.get("playwright.async_api")
        sys.modules["playwright"] = mock_playwright
        sys.modules["playwright.async_api"] = mock_async_api

    # --- pyautogui ---
    if "pyautogui" not in sys.modules:
        def _make_point(x=100, y=200):
            p = MagicMock()
            p.x = x
            p.y = y
            p.__iter__ = MagicMock(return_value=iter([x, y]))
            return p

        mock_pyautogui = types.ModuleType("pyautogui")
        mock_pyautogui.PAUSE = 0.5
        mock_pyautogui.FAILSAFE = True
        mock_pyautogui.position = MagicMock(return_value=_make_point(100, 200))
        mock_pyautogui.size = MagicMock(return_value=(1920, 1080))
        mock_pyautogui.moveTo = MagicMock()
        mock_pyautogui.click = MagicMock()
        mock_pyautogui.drag = MagicMock()
        mock_pyautogui.typewrite = MagicMock()
        mock_pyautogui.press = MagicMock()
        mock_pyautogui.hotkey = MagicMock()
        mock_pyautogui.scroll = MagicMock()
        mock_pyautogui.screenshot = MagicMock()
        mock_pyautogui.FailSafeException = type("FailSafeException", (Exception,), {})
        saved["pyautogui"] = sys.modules.get("pyautogui")
        sys.modules["pyautogui"] = mock_pyautogui

    # --- pygetwindow ---
    if "pygetwindow" not in sys.modules:
        mock_pygetwindow = types.ModuleType("pygetwindow")
        mock_pygetwindow.getActiveWindow = MagicMock()
        saved["pygetwindow"] = sys.modules.get("pygetwindow")
        sys.modules["pygetwindow"] = mock_pygetwindow

    yield

    # 恢复原始模块
    for mod_name, original in saved.items():
        if original is not None:
            sys.modules[mod_name] = original
        else:
            sys.modules.pop(mod_name, None)


# ---------------------------------------------------------------------------
# Database fixtures — in-memory SQLite per test
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Create a fresh in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_agent_dict():
    """A minimal Agent dict for creating test agents."""
    return {
        "name": "测试助手",
        "avatar": "",
        "role": "测试工程师",
        "system_prompt": "你是一个测试助手。",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
        "personality_json": json.dumps({"style": "严谨", "tone": "专业", "verbosity": "concise"}),
        "tools_config_json": json.dumps({
            "cli": {"enabled": True, "allowed_commands": ["ls", "cat", "pwd"], "blocked_commands": ["rm"]},
            "web": {"enabled": False, "max_pages": 10, "allowed_domains": [], "blocked_domains": []},
            "ui_automation": {"enabled": False},
            "vision": {"enabled": False},
        }),
        "skills_json": json.dumps(["code_review", "summarize"]),
        "is_active": True,
    }


@pytest.fixture
def sample_agent(db_session, sample_agent_dict):
    """Create and return a persisted Agent."""
    from app.models import Agent
    agent = Agent(**sample_agent_dict)
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def sample_conversation(db_session, sample_agent):
    """Create and return a persisted Conversation."""
    from app.models import Conversation
    conv = Conversation(agent_id=sample_agent.id, title="测试对话")
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)
    return conv


@pytest.fixture
def api_keys():
    """Return a minimal API keys dict."""
    return {"openai": "sk-test-fake-key-1234567890", "anthropic": "sk-ant-test-key"}
