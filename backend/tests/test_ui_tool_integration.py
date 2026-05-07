"""
UI Tool 集成测试 — Mock PyAutoGUI 测试桌面自动化、安全控制、组合键拦截。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pytest
import types
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image
import io

from app.ui_tool import UITool, UIToolResult


# ---------------------------------------------------------------------------
# 注入 mock pyautogui / pygetwindow 模块
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_ui_modules(request):
    """为每个测试注入 mock 的 pyautogui 和 pygetwindow 模块。"""
    def _make_point(x=100, y=200):
        """创建一个模拟 pyautogui.Point，支持解包 (x, y) 和属性访问。"""
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

    mock_pygetwindow = types.ModuleType("pygetwindow")
    mock_pygetwindow.getActiveWindow = MagicMock()

    saved_pyautogui = sys.modules.get("pyautogui")
    saved_pygetwindow = sys.modules.get("pygetwindow")

    sys.modules["pyautogui"] = mock_pyautogui
    sys.modules["pygetwindow"] = mock_pygetwindow

    yield

    if saved_pyautogui is not None:
        sys.modules["pyautogui"] = saved_pyautogui
    else:
        sys.modules.pop("pyautogui", None)

    if saved_pygetwindow is not None:
        sys.modules["pygetwindow"] = saved_pygetwindow
    else:
        sys.modules.pop("pygetwindow", None)


def _get_pyautogui():
    """获取注入的 mock pyautogui 模块。"""
    import pyautogui  # type: ignore[import-untyped]
    return pyautogui


def _get_pygetwindow():
    """获取注入的 mock pygetwindow 模块。"""
    import pygetwindow  # type: ignore[import-untyped]
    return pygetwindow


# ---------------------------------------------------------------------------
# 基本操作
# ---------------------------------------------------------------------------

class TestUIToolBasic:

    @pytest.mark.asyncio
    async def test_pyautogui_not_installed(self):
        """PyAutoGUI 未安装时返回友好错误。"""
        import builtins
        original_import = builtins.__import__

        def _block_pyautogui(name, *args, **kwargs):
            if name == "pyautogui":
                raise ImportError("No module named 'pyautogui'")
            return original_import(name, *args, **kwargs)

        saved = sys.modules.pop("pyautogui", None)
        builtins.__import__ = _block_pyautogui
        try:
            tool = UITool()
            result = await tool.execute("mouse_move", {"x": 100, "y": 200})
            assert result.success is False
            assert "需要安装 pyautogui" in result.error
        finally:
            builtins.__import__ = original_import
            if saved is not None:
                sys.modules["pyautogui"] = saved

    @pytest.mark.asyncio
    async def test_cancel_token_set(self):
        """cancel_token 已设置时应立即返回取消。"""
        tool = UITool()
        cancel = asyncio.Event()
        cancel.set()

        result = await tool.execute("mouse_move", {"x": 100, "y": 200}, cancel_token=cancel)
        assert result.success is False
        assert "已取消" in result.output

    @pytest.mark.asyncio
    async def test_unknown_action(self):
        """未知操作类型应报错。"""
        tool = UITool()
        result = await tool.execute("launch_missiles", {})
        assert result.success is False
        assert "未知操作类型" in result.error


# ---------------------------------------------------------------------------
# 鼠标操作
# ---------------------------------------------------------------------------

class TestMouseActions:

    def _make_point(self, x=0, y=0):
        p = MagicMock()
        p.x = x
        p.y = y
        p.__iter__ = MagicMock(return_value=iter([x, y]))
        return p

    @pytest.mark.asyncio
    async def test_mouse_move_success(self):
        """鼠标移动应在距离限制内成功。"""
        _get_pyautogui().position = MagicMock(return_value=self._make_point(0, 0))
        tool = UITool()
        result = await tool.execute("mouse_move", {"x": 100, "y": 200, "duration": 0.3})
        assert result.success is True
        assert "鼠标移动" in result.output
        _get_pyautogui().moveTo.assert_called_with(100, 200, duration=0.3)

    @pytest.mark.asyncio
    async def test_mouse_move_too_far(self):
        """超过最大移动距离应被拒绝。"""
        tool = UITool()
        tool.max_mouse_distance = 100
        result = await tool.execute("mouse_move", {"x": 1000, "y": 1000})
        assert result.success is False
        assert "超过上限" in result.error

    @pytest.mark.asyncio
    async def test_mouse_click_with_coordinates(self):
        """带坐标的点击应调用 click(x, y)。"""
        tool = UITool()
        result = await tool.execute("mouse_click", {"x": 300, "y": 400, "button": "right", "clicks": 2})
        assert result.success is True
        _get_pyautogui().click.assert_called_with(300, 400, clicks=2, button="right")

    @pytest.mark.asyncio
    async def test_mouse_click_current_position(self):
        """不带坐标的点击应点击当前位置。"""
        tool = UITool()
        result = await tool.execute("mouse_click", {"button": "left"})
        assert result.success is True
        _get_pyautogui().click.assert_called_with(clicks=1, button="left")

    @pytest.mark.asyncio
    async def test_mouse_drag(self):
        """拖拽操作应依次调用 moveTo 和 drag。"""
        tool = UITool()
        result = await tool.execute("mouse_drag", {"x1": 100, "y1": 200, "x2": 300, "y2": 400})
        assert result.success is True
        pg = _get_pyautogui()
        pg.moveTo.assert_called_with(100, 200, duration=0.3)
        pg.drag.assert_called_with(200, 200, duration=1.0)


# ---------------------------------------------------------------------------
# 键盘操作
# ---------------------------------------------------------------------------

class TestKeyboardActions:

    @pytest.mark.asyncio
    async def test_type_text(self):
        """输入文本应调用 typewrite。"""
        tool = UITool()
        result = await tool.execute("type_text", {"text": "hello world", "interval": 0.05})
        assert result.success is True
        _get_pyautogui().typewrite.assert_called_with("hello world", interval=0.05)

    @pytest.mark.asyncio
    async def test_type_text_too_long(self):
        """超过 100 字符且确认模式开启时应拒绝。"""
        tool = UITool(require_confirmation=True)
        long_text = "x" * 150
        result = await tool.execute("type_text", {"text": long_text})
        assert result.success is False
        assert "文本过长" in result.error

    @pytest.mark.asyncio
    async def test_type_text_long_without_confirmation(self):
        """确认模式关闭时，长文本也应允许。"""
        tool = UITool(require_confirmation=False)
        long_text = "x" * 150
        result = await tool.execute("type_text", {"text": long_text})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_type_text_missing_text(self):
        """缺少 text 参数应报错。"""
        tool = UITool()
        result = await tool.execute("type_text", {})
        assert result.success is False
        assert "缺少 text 参数" in result.error

    @pytest.mark.asyncio
    async def test_press_key(self):
        """按键操作应调用 press。"""
        tool = UITool()
        result = await tool.execute("press_key", {"key": "enter", "presses": 3})
        assert result.success is True
        _get_pyautogui().press.assert_called_with("enter", presses=3, interval=0.1)

    @pytest.mark.asyncio
    async def test_press_key_missing_key(self):
        """缺少 key 参数应报错。"""
        tool = UITool()
        result = await tool.execute("press_key", {})
        assert result.success is False
        assert "缺少 key 参数" in result.error

    @pytest.mark.asyncio
    async def test_hotkey_success(self):
        """正常的组合键应正确执行。"""
        tool = UITool()
        result = await tool.execute("hotkey", {"keys": ["ctrl", "c"]})
        assert result.success is True
        _get_pyautogui().hotkey.assert_called_with("ctrl", "c")


# ---------------------------------------------------------------------------
# 组合键安全拦截
# ---------------------------------------------------------------------------

class TestHotkeyBlocking:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("keys", [
        ["ctrl", "alt", "delete"],
        ["ctrl", "shift", "escape"],
        ["alt", "f4"],
        ["win", "r"],
        ["win", "l"],
        ["command", "q"],
        ["command", "option", "escape"],
    ])
    async def test_blocked_combos(self, keys):
        """被禁止的组合键应被拦截。"""
        tool = UITool()
        result = await tool.execute("hotkey", {"keys": keys})
        assert result.success is False
        assert "禁止的组合键" in result.error

    @pytest.mark.asyncio
    async def test_empty_keys(self):
        """空 keys 应报错。"""
        tool = UITool()
        result = await tool.execute("hotkey", {"keys": []})
        assert result.success is False
        assert "缺少 keys 参数" in result.error


# ---------------------------------------------------------------------------
# 截图 / 屏幕信息
# ---------------------------------------------------------------------------

class TestScreenshot:

    @pytest.mark.asyncio
    async def test_screenshot_full(self):
        """全屏截图应返回 base64 数据。"""
        img = Image.new("RGB", (100, 50), color=(255, 0, 0))
        _get_pyautogui().screenshot = MagicMock(return_value=img)

        tool = UITool()
        result = await tool.execute("screenshot", {})

        assert result.success is True
        assert result.output_type == "screenshot"
        assert len(result.screenshot_b64) > 0

    @pytest.mark.asyncio
    async def test_screenshot_with_region(self):
        """区域截图应传入 region 元组。"""
        img = Image.new("RGB", (60, 30))
        _get_pyautogui().screenshot = MagicMock(return_value=img)

        tool = UITool()
        result = await tool.execute("screenshot", {"region": [10, 20, 60, 30]})

        assert result.success is True
        _get_pyautogui().screenshot.assert_called_with(region=(10, 20, 60, 30))

    @pytest.mark.asyncio
    async def test_screenshot_save_to_file(self, tmp_path):
        """指定 filename 时应保存到文件。"""
        img = Image.new("RGB", (10, 10))
        _get_pyautogui().screenshot = MagicMock(return_value=img)

        tool = UITool()
        fpath = tmp_path / "screenshot.png"
        result = await tool.execute("screenshot", {"filename": str(fpath)})

        assert result.success is True
        assert fpath.exists()


# ---------------------------------------------------------------------------
# 屏幕信息查询
# ---------------------------------------------------------------------------

class TestScreenInfo:

    @pytest.mark.asyncio
    async def test_get_position(self):
        """获取鼠标位置应返回当前坐标。"""
        tool = UITool()
        result = await tool.execute("get_position", {})
        assert result.success is True
        assert result.output_type == "position"
        assert result.mouse_position == (100, 200)

    @pytest.mark.asyncio
    async def test_get_screen_size(self):
        """获取屏幕尺寸应返回宽度和高度。"""
        tool = UITool()
        result = await tool.execute("get_screen_size", {})
        assert result.success is True
        assert result.screen_size == (1920, 1080)

    @pytest.mark.asyncio
    async def test_get_active_window(self):
        """获取活动窗口应返回窗口标题。"""
        mock_win = MagicMock()
        mock_win.title = "Visual Studio Code"
        _get_pygetwindow().getActiveWindow = MagicMock(return_value=mock_win)

        tool = UITool()
        result = await tool.execute("get_active_window", {})

        assert result.success is True
        assert result.active_window == "Visual Studio Code"


# ---------------------------------------------------------------------------
# 弹窗 / 滚动
# ---------------------------------------------------------------------------

class TestAlertAndScroll:

    @pytest.mark.asyncio
    async def test_alert_accept(self):
        """确认弹窗应按下 enter 键。"""
        tool = UITool()
        result = await tool.execute("alert_accept", {})
        assert result.success is True
        _get_pyautogui().press.assert_called_with("enter")

    @pytest.mark.asyncio
    async def test_alert_dismiss(self):
        """关闭弹窗应按下 escape 键。"""
        tool = UITool()
        result = await tool.execute("alert_dismiss", {})
        assert result.success is True
        _get_pyautogui().press.assert_called_with("escape")

    @pytest.mark.asyncio
    async def test_scroll_default(self):
        """默认滚动应在当前位置。"""
        tool = UITool()
        result = await tool.execute("scroll", {})
        assert result.success is True
        _get_pyautogui().scroll.assert_called_with(3)

    @pytest.mark.asyncio
    async def test_scroll_at_position(self):
        """指定位置滚动应传坐标。"""
        tool = UITool()
        result = await tool.execute("scroll", {"clicks": -5, "x": 500, "y": 300})
        assert result.success is True
        _get_pyautogui().scroll.assert_called_with(-5, 500, 300)


# ---------------------------------------------------------------------------
# FailSafe 保护
# ---------------------------------------------------------------------------

class TestFailSafe:

    @pytest.mark.asyncio
    async def test_failsafe_triggered(self):
        """触发 FailSafe 时应返回安全错误。"""
        def _make_point(x=0, y=0):
            p = MagicMock()
            p.x = x
            p.y = y
            p.__iter__ = MagicMock(return_value=iter([x, y]))
            return p

        pg = _get_pyautogui()
        FailSafeException = pg.FailSafeException
        pg.position = MagicMock(return_value=_make_point(0, 0))
        pg.moveTo = MagicMock(side_effect=FailSafeException("安全触发"))

        tool = UITool()
        result = await tool.execute("mouse_move", {"x": 0, "y": 0})

        assert result.success is False
        assert "安全保护触发" in result.error


# ---------------------------------------------------------------------------
# 操作历史
# ---------------------------------------------------------------------------

class TestActionHistory:

    @pytest.mark.asyncio
    async def test_action_history_recorded(self):
        """每次操作应被记录到历史。"""
        tool = UITool()
        await tool.execute("press_key", {"key": "a"})
        await tool.execute("press_key", {"key": "b"})

        history = tool.get_action_history()
        assert len(history) == 2
        assert history[0]["action"] == "press_key"
        assert history[1]["action"] == "press_key"

    @pytest.mark.asyncio
    async def test_clear_history(self):
        """clear_history 应清空所有记录。"""
        tool = UITool()
        await tool.execute("press_key", {"key": "a"})
        tool.clear_history()
        assert len(tool.get_action_history()) == 0


# ---------------------------------------------------------------------------
# from_agent_config
# ---------------------------------------------------------------------------

class TestFromAgentConfig:

    def test_creates_tool_with_confirm_enabled(self, db_session):
        import json
        from app.models import Agent
        agent = Agent(
            name="UITest",
            system_prompt="",
            tools_config_json=json.dumps({
                "ui_automation": {"enabled": True, "require_confirmation": True}
            }),
        )
        tool = UITool.from_agent_config(agent)
        assert tool.require_confirmation is True

    def test_creates_tool_from_config(self, db_session):
        import json
        from app.models import Agent
        # from_agent_config 在未显式配置 require_confirmation 时默认 True
        agent = Agent(
            name="UITest2",
            system_prompt="",
            tools_config_json=json.dumps({"ui_automation": {"enabled": False}}),
        )
        tool = UITool.from_agent_config(agent)
        # require_confirmation 的默认值是 True
        assert tool.require_confirmation is True


# ---------------------------------------------------------------------------
# UIToolResult dataclass
# ---------------------------------------------------------------------------

class TestUIToolResult:

    def test_defaults(self):
        r = UIToolResult(success=True)
        assert r.success is True
        assert r.output == ""
        assert r.output_type == "text"
        assert r.mouse_position == (0, 0)
        assert r.screen_size == (0, 0)

    def test_full_result(self):
        r = UIToolResult(
            success=True,
            output="完成",
            output_type="screenshot",
            screenshot_b64="abc123",
            mouse_position=(500, 300),
            screen_size=(1920, 1080),
            active_window="Chrome",
        )
        assert r.screenshot_b64 == "abc123"
        assert r.mouse_position == (500, 300)
        assert r.active_window == "Chrome"
