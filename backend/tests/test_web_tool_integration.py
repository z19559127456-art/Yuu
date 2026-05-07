"""
Web Tool 集成测试 — Mock Playwright 测试域名安全、操作执行、错误处理。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pytest
import types
from unittest.mock import AsyncMock, MagicMock, patch

from app.web_tool import WebTool, WebToolResult, WebAction


# ---------------------------------------------------------------------------
# 注入 mock playwright 模块
# ---------------------------------------------------------------------------

def _create_mock_page() -> AsyncMock:
    """创建并返回一个预配置的 mock Playwright Page 对象。"""
    page = AsyncMock()
    page.url = "https://example.com"
    page.title = AsyncMock(return_value="Example Page")
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"fake-png-data")
    page.inner_text = AsyncMock(return_value="Hello World")
    page.inner_html = AsyncMock(return_value="<div>Test</div>")
    page.evaluate = AsyncMock(return_value=42)
    page.close = AsyncMock()
    return page


@pytest.fixture(autouse=True)
def _mock_playwright_modules(request):
    """为每个测试注入 mock 的 playwright 模块。"""
    mock_async_api = types.ModuleType("playwright.async_api")
    mock_playwright = types.ModuleType("playwright")

    mock_page = _create_mock_page()
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

    saved_playwright = sys.modules.get("playwright")
    saved_async_api = sys.modules.get("playwright.async_api")

    sys.modules["playwright"] = mock_playwright
    sys.modules["playwright.async_api"] = mock_async_api

    yield

    if saved_playwright is not None:
        sys.modules["playwright"] = saved_playwright
    else:
        sys.modules.pop("playwright", None)

    if saved_async_api is not None:
        sys.modules["playwright.async_api"] = saved_async_api
    else:
        sys.modules.pop("playwright.async_api", None)


# ---------------------------------------------------------------------------
# 域名安全检查
# ---------------------------------------------------------------------------

class TestDomainSafety:

    def test_allowed_domain_passes(self):
        tool = WebTool(allowed_domains=["example.com", "test.org"])
        ok, reason = tool._check_domain("https://example.com/page")
        assert ok is True
        assert reason == ""

    def test_blocked_domain_rejected(self):
        tool = WebTool(blocked_domains=["evil.com"])
        ok, reason = tool._check_domain("https://evil.com/phishing")
        assert ok is False
        assert "黑名单" in reason

    def test_not_in_allowlist_rejected(self):
        tool = WebTool(allowed_domains=["safe.com"])
        ok, reason = tool._check_domain("https://other.com")
        assert ok is False
        assert "白名单" in reason

    def test_subdomain_matches(self):
        tool = WebTool(allowed_domains=["example.com"])
        ok, _ = tool._check_domain("https://sub.example.com/path")
        assert ok is True

    def test_blocklist_takes_priority(self):
        tool = WebTool(
            allowed_domains=["example.com"],
            blocked_domains=["evil.example.com"],
        )
        ok, reason = tool._check_domain("https://evil.example.com/x")
        assert ok is False
        assert "黑名单" in reason

    def test_none_url_handled(self):
        """空 URL 或无协议 URL 应被正确处理（不被允许进入）。"""
        tool = WebTool(allowed_domains=["example.com"])
        ok, _ = tool._check_domain("")
        # 空字符串没有匹配的域名，应拒绝
        assert ok is False

    def test_no_restrictions_allows_all(self):
        tool = WebTool()
        ok, _ = tool._check_domain("https://any-domain.com")
        assert ok is True


# ---------------------------------------------------------------------------
# 操作执行（模拟 Playwright）
# ---------------------------------------------------------------------------

def _get_mock_page():
    """获取注入的 mock playwright 模块中的当前 mock page。"""
    pw_mod = sys.modules["playwright.async_api"]
    pw_instance = pw_mod.async_playwright()
    browser = pw_instance.chromium.launch.return_value
    context = browser.new_context.return_value
    return context.new_page.return_value


def _reset_web_tool_state():
    """重置 WebTool 的静态/实例状态，确保每个测试干净运行。"""
    pass


# ---------------------------------------------------------------------------
# 操作执行（模拟 Playwright）
# ---------------------------------------------------------------------------

class TestWebToolExecute:

    @pytest.mark.asyncio
    async def test_execute_navigate_success(self):
        """导航到允许的域名应成功。"""
        tool = WebTool(allowed_domains=["example.com"])
        page = _get_mock_page()

        result = await tool.execute([{"action": "navigate", "params": {"url": "https://example.com"}}])

        assert result.success is True
        assert "已导航" in result.output
        page.goto.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_navigate_blocked_domain(self):
        """导航到黑名单域名应被拒绝（无需启动浏览器）。"""
        tool = WebTool(blocked_domains=["evil.com"])

        result = await tool.execute([{"action": "navigate", "params": {"url": "https://evil.com"}}])

        assert result.success is False
        assert "黑名单" in result.error

    @pytest.mark.asyncio
    async def test_execute_click(self):
        """点击操作应等待选择器后点击。"""
        tool = WebTool()
        page = _get_mock_page()

        result = await tool.execute([{"action": "click", "params": {"selector": "#btn"}}])

        assert result.success is True
        page.wait_for_selector.assert_called_with("#btn", timeout=60000)
        page.click.assert_called_with("#btn")

    @pytest.mark.asyncio
    async def test_execute_click_missing_selector(self):
        """缺少 selector 参数应报错。"""
        tool = WebTool()

        result = await tool.execute([{"action": "click", "params": {}}])

        assert result.success is False
        assert "selector" in result.error

    @pytest.mark.asyncio
    async def test_execute_type_text(self):
        """输入文本操作应正确调用 fill。"""
        tool = WebTool()
        page = _get_mock_page()

        result = await tool.execute([{
            "action": "type",
            "params": {"selector": "#input", "text": "hello"}
        }])

        assert result.success is True
        page.fill.assert_called_with("#input", "hello")

    @pytest.mark.asyncio
    async def test_execute_screenshot(self):
        """截图操作应返回 base64 编码的图片。"""
        tool = WebTool()
        _get_mock_page().screenshot = AsyncMock(return_value=b"fake-png-data")

        result = await tool.execute([{"action": "screenshot", "params": {}}])

        assert result.success is True
        assert result.output_type == "screenshot"
        assert len(result.screenshot_b64) > 0

    @pytest.mark.asyncio
    async def test_execute_screenshot_with_selector(self):
        """按选择器截图应定位元素后截图。"""
        mock_element = AsyncMock()
        mock_element.screenshot = AsyncMock(return_value=b"element-png")
        _get_mock_page().wait_for_selector = AsyncMock(return_value=mock_element)
        tool = WebTool()

        result = await tool.execute([{"action": "screenshot", "params": {"selector": "#target"}}])

        assert result.success is True
        mock_element.screenshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_extract_text(self):
        """提取文本操作应返回 inner_text。"""
        _get_mock_page().inner_text = AsyncMock(return_value="Hello World")
        tool = WebTool()

        result = await tool.execute([{"action": "extract", "params": {"selector": "body"}}])

        assert result.success is True
        assert "Hello World" in result.output

    @pytest.mark.asyncio
    async def test_execute_extract_html(self):
        """提取 HTML 操作应返回 inner_html。"""
        _get_mock_page().inner_html = AsyncMock(return_value="<div>Test</div>")
        tool = WebTool()

        result = await tool.execute([{"action": "extract", "params": {"selector": "body", "extract_type": "html"}}])

        assert result.success is True
        assert result.output_type == "html"
        assert "<div>Test</div>" in result.output

    @pytest.mark.asyncio
    async def test_execute_scroll(self):
        """滚动操作应调用 evaluate 执行 JS。"""
        tool = WebTool()
        page = _get_mock_page()

        result = await tool.execute([{"action": "scroll", "params": {"direction": "down", "amount": 300}}])

        assert result.success is True
        page.evaluate.assert_called_with("window.scrollBy(0, 300)")

    @pytest.mark.asyncio
    async def test_execute_wait(self):
        """等待操作应暂停指定毫秒数。"""
        tool = WebTool()

        with patch("asyncio.sleep") as mock_sleep:
            result = await tool.execute([{"action": "wait", "params": {"ms": 500}}])
            mock_sleep.assert_called_with(0.5)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_evaluate(self):
        """evaluate 操作应执行 JS 并返回结果。"""
        _get_mock_page().evaluate = AsyncMock(return_value=42)
        tool = WebTool()

        result = await tool.execute([{"action": "evaluate", "params": {"script": "1 + 1"}}])

        assert result.success is True
        assert "42" in result.output

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        """未知操作类型应报错。"""
        tool = WebTool()

        result = await tool.execute([{"action": "fly_to_moon", "params": {}}])

        assert result.success is False
        assert "未知操作类型" in result.error

    @pytest.mark.asyncio
    async def test_execute_max_pages_limit(self):
        """超过最大页面数应拒绝。"""
        tool = WebTool(max_pages=0)

        result = await tool.execute([{"action": "navigate", "params": {"url": "https://example.com"}}])

        assert result.success is False
        assert "最大页面限制" in result.error

    @pytest.mark.asyncio
    async def test_execute_playwright_not_installed(self):
        """Playwright 未安装时应返回友好错误。"""
        # 彻底移除 mock playwright 模块，让 import 语句失败
        # 因为真正的 playwright 已安装，需要手动 hook import
        import builtins
        original_import = builtins.__import__

        def _block_playwright(name, *args, **kwargs):
            if name.startswith("playwright"):
                raise ImportError("No module named 'playwright'")
            return original_import(name, *args, **kwargs)

        saved_playwright = sys.modules.pop("playwright", None)
        saved_async_api = sys.modules.pop("playwright.async_api", None)

        builtins.__import__ = _block_playwright
        try:
            tool = WebTool()
            result = await tool.execute([{"action": "navigate", "params": {"url": "https://example.com"}}])

            assert result.success is False
            assert "需要安装 playwright" in result.error
        finally:
            builtins.__import__ = original_import
            if saved_playwright is not None:
                sys.modules["playwright"] = saved_playwright
            if saved_async_api is not None:
                sys.modules["playwright.async_api"] = saved_async_api

    @pytest.mark.asyncio
    async def test_execute_cancel_token(self):
        """传入 cancel_token 应在检查点停止执行。"""
        tool = WebTool()
        cancel = asyncio.Event()
        cancel.set()

        result = await tool.execute(
            [{"action": "navigate", "params": {"url": "https://example.com"}}],
            cancel_token=cancel,
        )

        assert result.success is False
        assert "已取消" in result.output

    @pytest.mark.asyncio
    async def test_execute_action_timeout(self):
        """单个操作超时应捕获并报告错误。"""
        _get_mock_page().goto = AsyncMock(side_effect=asyncio.TimeoutError("操作超时"))
        tool = WebTool()

        result = await tool.execute([{"action": "navigate", "params": {"url": "https://example.com"}}])

        assert result.success is False
        assert "操作超时" in result.error

    @pytest.mark.asyncio
    async def test_execute_multi_step(self):
        """多步操作应顺序执行。"""
        tool = WebTool()
        page = _get_mock_page()

        result = await tool.execute([
            {"action": "navigate", "params": {"url": "https://example.com"}},
            {"action": "click", "params": {"selector": "#btn"}},
            {"action": "screenshot", "params": {}},
        ])

        assert result.success is True
        assert page.goto.call_count == 1
        assert page.click.call_count == 1
        assert page.screenshot.call_count == 1


# ---------------------------------------------------------------------------
# from_agent_config
# ---------------------------------------------------------------------------

class TestFromAgentConfig:

    def test_creates_tool_from_agent(self, db_session):
        from app.models import Agent
        agent = Agent(
            name="TestAgent",
            system_prompt="Be helpful.",
            tools_config_json='{"web": {"max_pages": 5, "allowed_domains": ["test.com"], "blocked_domains": ["bad.com"]}}',
        )
        tool = WebTool.from_agent_config(agent)

        assert tool.max_pages == 5
        assert tool.allowed_domains == ["test.com"]
        assert tool.blocked_domains == ["bad.com"]

    def test_empty_config_defaults(self, db_session):
        from app.models import Agent
        agent = Agent(name="Test", system_prompt="", tools_config_json="{}")
        tool = WebTool.from_agent_config(agent)

        assert tool.max_pages == 10
        assert tool.allowed_domains == []
        assert tool.blocked_domains == []


# ---------------------------------------------------------------------------
# WebAction / WebToolResult
# ---------------------------------------------------------------------------

class TestDataClasses:

    def test_web_action_creation(self):
        action = WebAction(action="navigate", params={"url": "https://x.com"})
        assert action.action == "navigate"
        assert action.params["url"] == "https://x.com"

    def test_web_tool_result_defaults(self):
        result = WebToolResult(success=True, output="done")
        assert result.success is True
        assert result.output == "done"
        assert result.output_type == "text"
        assert result.screenshot_b64 == ""
        assert result.page_url == ""
