"""
UI Tool — PyAutoGUI-based desktop automation with safety confirmations.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class UIToolResult:
    success: bool
    output: str = ""
    output_type: str = "text"  # text | screenshot | position
    screenshot_b64: str = ""
    mouse_position: tuple[int, int] = (0, 0)
    screen_size: tuple[int, int] = (0, 0)
    active_window: str = ""
    execution_time_ms: int = 0
    error: str = ""
    metadata: dict = field(default_factory=dict)


class UITool:
    """Desktop automation tool wrapping PyAutoGUI with safety controls."""

    def __init__(
        self,
        require_confirmation: bool = True,
        pause_between_actions: float = 0.5,
        max_mouse_distance: int = 2000,
        timeout_seconds: int = 30,
    ):
        self.require_confirmation = require_confirmation
        self.pause_between_actions = pause_between_actions
        self.max_mouse_distance = max_mouse_distance
        self.timeout_seconds = timeout_seconds
        self._action_history: list[dict] = []

    async def execute(
        self,
        action: str,
        params: dict | None = None,
        cancel_token: asyncio.Event | None = None,
    ) -> UIToolResult:
        """
        Execute a single UI automation action.

        Supported actions:
        - mouse_move: x, y, duration
        - mouse_click: x, y, button, clicks
        - mouse_drag: x1, y1, x2, y2, duration
        - type_text: text, interval
        - press_key: key, presses
        - hotkey: keys (list)
        - screenshot: region (x,y,w,h), filename
        - get_position: (no params)
        - get_screen_size: (no params)
        - get_active_window: (no params)
        - scroll: clicks, x, y
        - alert_accept / alert_dismiss: (no params)
        """
        import time

        params = params or {}
        start = time.monotonic()

        try:
            import pyautogui
        except ImportError:
            elapsed = int((time.monotonic() - start) * 1000)
            return UIToolResult(
                success=False,
                error="需要安装 pyautogui: pip install pyautogui",
                execution_time_ms=elapsed,
            )

        pyautogui.PAUSE = self.pause_between_actions
        pyautogui.FAILSAFE = True

        if cancel_token and cancel_token.is_set():
            return UIToolResult(
                success=False,
                output="操作已取消",
                execution_time_ms=int((time.monotonic() - start) * 1000),
            )

        try:
            result = await asyncio.to_thread(
                self._execute_sync, pyautogui, action, params
            )
            result.execution_time_ms = int((time.monotonic() - start) * 1000)
            self._action_history.append({
                "action": action,
                "params": params,
                "result": result.success,
                "time_ms": result.execution_time_ms,
            })
            return result
        except pyautogui.FailSafeException:
            elapsed = int((time.monotonic() - start) * 1000)
            return UIToolResult(
                success=False,
                error="安全保护触发：鼠标移至屏幕角落 (FailSafe)",
                execution_time_ms=elapsed,
            )
        except Exception as e:
            logger.error(f"UI tool error: {e}")
            elapsed = int((time.monotonic() - start) * 1000)
            return UIToolResult(
                success=False,
                error=str(e),
                execution_time_ms=elapsed,
            )

    def _execute_sync(self, pyautogui, action: str, params: dict) -> UIToolResult:
        """Synchronous action execution — runs in a thread via asyncio.to_thread."""
        result = UIToolResult(success=True)

        if action == "mouse_move":
            x, y = params.get("x", 0), params.get("y", 0)
            duration = params.get("duration", 0.5)
            current_x, current_y = pyautogui.position()
            distance = ((x - current_x) ** 2 + (y - current_y) ** 2) ** 0.5
            if distance > self.max_mouse_distance:
                return UIToolResult(
                    success=False,
                    error=f"鼠标移动距离 ({int(distance)}px) 超过上限 ({self.max_mouse_distance}px)",
                )
            pyautogui.moveTo(x, y, duration=duration)
            result.output = f"鼠标移动至 ({x}, {y})"
            result.mouse_position = (x, y)
            result.output_type = "position"

        elif action == "mouse_click":
            x = params.get("x")
            y = params.get("y")
            button = params.get("button", "left")
            clicks = params.get("clicks", 1)
            if x is not None and y is not None:
                pyautogui.click(x, y, clicks=clicks, button=button)
                result.output = f"点击 ({x}, {y}) 按钮={button} 次数={clicks}"
            else:
                pyautogui.click(clicks=clicks, button=button)
                pos = pyautogui.position()
                result.output = f"点击当前位置 ({pos.x}, {pos.y}) 按钮={button} 次数={clicks}"
            result.mouse_position = pyautogui.position()

        elif action == "mouse_drag":
            x1, y1 = params.get("x1", 0), params.get("y1", 0)
            x2, y2 = params.get("x2", 0), params.get("y2", 0)
            duration = params.get("duration", 1.0)
            pyautogui.moveTo(x1, y1, duration=0.3)
            pyautogui.drag(x2 - x1, y2 - y1, duration=duration)
            result.output = f"拖拽 ({x1},{y1}) → ({x2},{y2})"
            result.mouse_position = (x2, y2)

        elif action == "type_text":
            text = params.get("text", "")
            if not text:
                return UIToolResult(success=False, error="缺少 text 参数")
            interval = params.get("interval", 0.05)
            if self.require_confirmation and len(text) > 100:
                return UIToolResult(
                    success=False,
                    error=f"文本过长 ({len(text)} 字符)，需要确认模式已开启",
                )
            pyautogui.typewrite(text, interval=interval)
            result.output = f"已输入文本 ({len(text)} 字符)"

        elif action == "press_key":
            key = params.get("key", "")
            if not key:
                return UIToolResult(success=False, error="缺少 key 参数")
            presses = params.get("presses", 1)
            pyautogui.press(key, presses=presses, interval=0.1)
            result.output = f"按键 {key} x{presses}"

        elif action == "hotkey":
            keys = params.get("keys", [])
            if not keys:
                return UIToolResult(success=False, error="缺少 keys 参数")

            blocked_combos = [
                ("ctrl", "alt", "delete"),
                ("ctrl", "shift", "escape"),
                ("alt", "f4"),
                ("win", "r"),
                ("win", "l"),
                ("command", "q"),
                ("command", "option", "escape"),
            ]
            for combo in blocked_combos:
                if all(k.lower() in [k2.lower() for k2 in keys] for k in combo):
                    return UIToolResult(success=False, error=f"禁止的组合键: {'+'.join(combo)}")

            pyautogui.hotkey(*keys)
            result.output = f"组合键 {'+'.join(keys)}"

        elif action == "screenshot":
            region = params.get("region")
            filename = params.get("filename")
            import base64
            import io
            img = pyautogui.screenshot(region=tuple(region) if region else None)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            result.screenshot_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            result.output_type = "screenshot"
            result.output = f"截图完成 ({img.width}x{img.height})"
            if filename:
                img.save(filename)
                result.output += f" → 已保存至 {filename}"

        elif action == "get_position":
            pos = pyautogui.position()
            result.mouse_position = (pos.x, pos.y)
            result.output_type = "position"
            result.output = f"鼠标位置: ({pos.x}, {pos.y})"

        elif action == "get_screen_size":
            w, h = pyautogui.size()
            result.screen_size = (w, h)
            result.output = f"屏幕尺寸: {w}x{h}"

        elif action == "get_active_window":
            try:
                import pygetwindow
            except ImportError:
                return UIToolResult(
                    success=False,
                    error="需要安装 pygetwindow: pip install pygetwindow",
                )
            win = pygetwindow.getActiveWindow()
            if win:
                result.active_window = win.title or ""
                result.output = f"当前窗口: {win.title}"
            else:
                result.output = "无法获取当前窗口信息"

        elif action == "scroll":
            clicks = params.get("clicks", 3)
            x = params.get("x")
            y = params.get("y")
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x, y)
            else:
                pyautogui.scroll(clicks)
            result.output = f"滚动 {clicks} 格"

        elif action == "alert_accept":
            pyautogui.press("enter")
            result.output = "已确认弹窗"

        elif action == "alert_dismiss":
            pyautogui.press("escape")
            result.output = "已关闭弹窗"

        else:
            return UIToolResult(success=False, error=f"未知操作类型: {action}")

        return result

    def get_action_history(self) -> list[dict]:
        """Return the history of executed actions."""
        return self._action_history.copy()

    def clear_history(self):
        """Clear action history."""
        self._action_history.clear()

    @staticmethod
    def from_agent_config(agent) -> "UITool":
        """Create a UITool from an Agent's tools_config."""
        import json as _json
        cfg = _json.loads(agent.tools_config_json or "{}")
        ui_cfg = cfg.get("ui_automation", {})
        return UITool(
            require_confirmation=ui_cfg.get("require_confirmation", True),
        )
