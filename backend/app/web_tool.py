"""
Web Tool — Playwright-based browser automation with domain safety controls.
"""
import json
import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class WebToolResult:
    success: bool
    output: str = ""
    output_type: str = "text"  # text | html | screenshot | json
    screenshot_b64: str = ""
    page_url: str = ""
    page_title: str = ""
    execution_time_ms: int = 0
    error: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class WebAction:
    """A single browser action step."""
    action: str  # navigate | click | type | screenshot | extract | scroll | wait | evaluate
    params: dict = field(default_factory=dict)


class WebTool:
    """Playwright-based web automation tool with domain safety."""

    def __init__(
        self,
        max_pages: int = 10,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
        timeout_seconds: int = 60,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ):
        self.max_pages = max_pages
        self.allowed_domains = allowed_domains or []
        self.blocked_domains = blocked_domains or []
        self.timeout_seconds = timeout_seconds
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._browser = None
        self._context = None
        self._page_count = 0

    def _check_domain(self, url: str) -> tuple[bool, str]:
        """Validate URL against domain allowlist/blocklist."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower() or parsed.path.split("/")[0].lower()
        except Exception:
            return False, f"无法解析 URL: {url}"

        if self.blocked_domains:
            for blocked in self.blocked_domains:
                if blocked.lower() in domain:
                    return False, f"域名在黑名单中: {domain}"

        if self.allowed_domains:
            allowed = any(
                allowed_domain.lower() in domain
                for allowed_domain in self.allowed_domains
            )
            if not allowed:
                return False, f"域名不在白名单中: {domain}"

        return True, ""

    async def _ensure_browser(self):
        """Lazy-init Playwright browser."""
        if self._browser is not None:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "需要安装 playwright: pip install playwright && playwright install chromium"
            )

        self._pw = await async_playwright().__aenter__()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
        )
        self._context = await self._browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )

    async def execute(
        self,
        actions: list[dict],
        cancel_token: asyncio.Event | None = None,
        on_step=None,
    ) -> WebToolResult:
        """Execute a sequence of browser actions."""
        import time

        start = time.monotonic()

        try:
            await self._ensure_browser()
        except ImportError as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return WebToolResult(
                success=False,
                error=str(e),
                execution_time_ms=elapsed,
            )

        page = await self._context.new_page()
        self._page_count += 1

        if self._page_count > self.max_pages:
            await page.close()
            elapsed = int((time.monotonic() - start) * 1000)
            return WebToolResult(
                success=False,
                error=f"超过最大页面限制 ({self.max_pages})",
                execution_time_ms=elapsed,
            )

        try:
            result = WebToolResult(success=True)
            parsed_actions = [WebAction(**a) if isinstance(a, dict) else a for a in actions]

            for i, action in enumerate(parsed_actions):
                if cancel_token and cancel_token.is_set():
                    result.output += "\n[已取消]"
                    result.success = False
                    break

                step_result = await self._execute_action(page, action)
                if on_step:
                    on_step(i, action.action, step_result)

                if isinstance(step_result, dict):
                    if not step_result.get("success", True):
                        result.success = False
                        result.error = step_result.get("error", "")
                        result.output += f"\n[步骤{i}失败] {result.error}"
                        break
                    result.output += step_result.get("output", "")
                    if step_result.get("screenshot"):
                        result.screenshot_b64 = step_result["screenshot"]
                        result.output_type = "screenshot"
                    if step_result.get("html"):
                        result.output = step_result["html"]
                        result.output_type = "html"
                    if isinstance(step_result.get("json"), (dict, list)):
                        result.output = json.dumps(step_result["json"], ensure_ascii=False, indent=2)
                        result.output_type = "json"

            elapsed = int((time.monotonic() - start) * 1000)
            result.execution_time_ms = elapsed
            result.page_url = page.url
            result.page_title = await page.title()
            return result

        except asyncio.TimeoutError:
            elapsed = int((time.monotonic() - start) * 1000)
            return WebToolResult(
                success=False,
                error="操作超时",
                execution_time_ms=elapsed,
            )
        except Exception as e:
            logger.error(f"Web tool error: {e}")
            elapsed = int((time.monotonic() - start) * 1000)
            return WebToolResult(
                success=False,
                error=str(e),
                execution_time_ms=elapsed,
            )
        finally:
            await page.close()

    async def _execute_action(self, page, action: WebAction) -> dict:
        """Execute a single browser action."""
        try:
            if action.action == "navigate":
                url = action.params.get("url", "")
                allowed, reason = self._check_domain(url)
                if not allowed:
                    return {"success": False, "error": reason}

                wait_until = action.params.get("wait_until", "domcontentloaded")
                await page.goto(url, wait_until=wait_until, timeout=self.timeout_seconds * 1000)
                return {"success": True, "output": f"已导航至 {url}"}

            elif action.action == "click":
                selector = action.params.get("selector", "")
                if not selector:
                    return {"success": False, "error": "缺少 selector 参数"}
                await page.wait_for_selector(selector, timeout=self.timeout_seconds * 1000)
                await page.click(selector)
                return {"success": True, "output": f"已点击 {selector}"}

            elif action.action == "type":
                selector = action.params.get("selector", "")
                text = action.params.get("text", "")
                if not selector:
                    return {"success": False, "error": "缺少 selector 参数"}
                await page.wait_for_selector(selector, timeout=self.timeout_seconds * 1000)
                await page.fill(selector, text)
                return {"success": True, "output": f"已在 {selector} 输入文本"}

            elif action.action == "screenshot":
                full_page = action.params.get("full_page", False)
                selector = action.params.get("selector")
                if selector:
                    el = await page.wait_for_selector(selector, timeout=self.timeout_seconds * 1000)
                    screenshot = await el.screenshot(type="png")
                else:
                    screenshot = await page.screenshot(type="png", full_page=full_page)

                import base64
                return {
                    "success": True,
                    "output": "截图完成",
                    "screenshot": base64.b64encode(screenshot).decode("utf-8"),
                }

            elif action.action == "extract":
                selector = action.params.get("selector", "body")
                extract_type = action.params.get("extract_type", "text")

                await page.wait_for_selector(selector, timeout=self.timeout_seconds * 1000)

                if extract_type == "html":
                    html = await page.inner_html(selector)
                    return {"success": True, "output": "已提取HTML", "html": html}
                elif extract_type == "json":
                    raw = await page.inner_text(selector)
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        return {"success": False, "error": "内容不是有效JSON"}
                    return {"success": True, "output": "已提取JSON数据", "json": parsed}
                else:
                    text = await page.inner_text(selector)
                    return {"success": True, "output": text}

            elif action.action == "scroll":
                direction = action.params.get("direction", "down")
                amount = action.params.get("amount", 500)
                if direction == "down":
                    await page.evaluate(f"window.scrollBy(0, {amount})")
                elif direction == "up":
                    await page.evaluate(f"window.scrollBy(0, -{amount})")
                return {"success": True, "output": f"已滚动 {direction} {amount}px"}

            elif action.action == "wait":
                ms = action.params.get("ms", 1000)
                await asyncio.sleep(ms / 1000)
                return {"success": True, "output": f"已等待 {ms}ms"}

            elif action.action == "evaluate":
                script = action.params.get("script", "")
                if not script:
                    return {"success": False, "error": "缺少 script 参数"}
                result = await page.evaluate(script)
                output = str(result) if result is not None else "undefined"
                return {"success": True, "output": output}

            else:
                return {"success": False, "error": f"未知操作类型: {action.action}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close(self):
        """Clean up browser resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_pw"):
            await self._pw.__aexit__(None, None, None)
        self._browser = None
        self._context = None
        self._page_count = 0

    @staticmethod
    def from_agent_config(agent) -> "WebTool":
        """Create a WebTool from an Agent's tools_config."""
        import json as _json
        cfg = _json.loads(agent.tools_config_json or "{}")
        web = cfg.get("web", {})
        return WebTool(
            max_pages=web.get("max_pages", 10),
            allowed_domains=web.get("allowed_domains", []),
            blocked_domains=web.get("blocked_domains", []),
        )
