"""
三层防死循环检测 — 环路检测 / Token 预算 / 超时保护
"""
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class DeadlockReport:
    """死锁检测报告"""
    triggered: bool = False
    level: int = 0          # 1=环路, 2=预算, 3=超时
    reason: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "triggered": self.triggered,
            "level": self.level,
            "reason": self.reason,
            "details": self.details,
        }


@dataclass
class LoopRecord:
    """单次调用记录，用于环路检测"""
    caller_id: str          # agent_id 或 skill_name
    action: str             # 执行的动作描述
    timestamp: float = 0.0


# ---------------------------------------------------------------------------
# Level 1 — 环路检测
# ---------------------------------------------------------------------------

class LoopDetector:
    """
    Level 1: 检测重复调用环路。

    基于滑动窗口：记录最近 N 次调用，若重复模式出现超过阈值则触发。
    """

    def __init__(self, max_window: int = 50, repeat_threshold: int = 5):
        self._max_window = max_window
        self._repeat_threshold = repeat_threshold
        self._records: dict[str, list[LoopRecord]] = defaultdict(list)

    def record(self, caller_id: str, action: str):
        """记录一次调用。"""
        self._records[caller_id].append(LoopRecord(
            caller_id=caller_id,
            action=action,
            timestamp=time.time(),
        ))
        # 裁剪窗口
        records = self._records[caller_id]
        if len(records) > self._max_window:
            self._records[caller_id] = records[-self._max_window:]

    def check(self, caller_id: str) -> DeadlockReport:
        """
        检查指定 caller 是否存在环路。
        检测逻辑：最后 N 条记录中，相同 action 重复出现 >= threshold 次。
        """
        records = self._records.get(caller_id, [])
        if len(records) < self._repeat_threshold:
            return DeadlockReport()

        # 取最近 repeat_threshold 条
        recent = records[-self._repeat_threshold:]

        # 检查是否所有 recent 条目的 action 都相同
        actions = [r.action for r in recent]
        if len(set(actions)) == 1 and len(actions) >= self._repeat_threshold:
            return DeadlockReport(
                triggered=True,
                level=1,
                reason=f"检测到调用环路: {caller_id} 连续 {self._repeat_threshold} 次执行相同操作 '{actions[0]}'",
                details={"caller_id": caller_id, "action": actions[0], "count": len(actions)},
            )

        # 检查整体频率：窗口内同一 action 占比过高
        action_counts: dict[str, int] = defaultdict(int)
        for r in records:
            action_counts[r.action] += 1

        for action, count in action_counts.items():
            if count >= self._repeat_threshold * 2:
                return DeadlockReport(
                    triggered=True,
                    level=1,
                    reason=f"检测到高频重复操作: {caller_id} 执行 '{action}' 共 {count} 次",
                    details={"caller_id": caller_id, "action": action, "count": count},
                )

        return DeadlockReport()

    def clear(self, caller_id: Optional[str] = None):
        """清除指定或全部记录。"""
        if caller_id:
            self._records.pop(caller_id, None)
        else:
            self._records.clear()


# ---------------------------------------------------------------------------
# Level 2 — Token / 轮次预算
# ---------------------------------------------------------------------------

class BudgetDetector:
    """
    Level 2: Token 预算和轮次上限检测。

    限制：
    - max_turns: 最大对话/讨论轮次
    - max_tokens: 最大总 token 消耗
    - max_duration_seconds: 最大总执行时间
    """

    def __init__(
        self,
        max_turns: int = 100,
        max_tokens: int = 1_000_000,
        max_duration_seconds: int = 3600,
    ):
        self._max_turns = max_turns
        self._max_tokens = max_tokens
        self._max_duration = max_duration_seconds

        self._session_turns: dict[str, int] = defaultdict(int)
        self._session_tokens: dict[str, int] = defaultdict(int)
        self._session_start: dict[str, float] = {}

    def start_session(self, session_id: str):
        """开始新的会话跟踪。"""
        self._session_turns[session_id] = 0
        self._session_tokens[session_id] = 0
        self._session_start[session_id] = time.time()

    def record_turn(self, session_id: str, tokens: int = 0):
        """记录一轮对话/执行。"""
        self._session_turns[session_id] += 1
        self._session_tokens[session_id] += tokens

    def check(self, session_id: str) -> DeadlockReport:
        """检查预算是否超限。"""
        # 轮次检查
        turns = self._session_turns.get(session_id, 0)
        if turns > self._max_turns:
            return DeadlockReport(
                triggered=True,
                level=2,
                reason=f"超出轮次上限: {turns}/{self._max_turns}",
                details={"session_id": session_id, "turns": turns, "max_turns": self._max_turns},
            )

        # Token 检查
        tokens = self._session_tokens.get(session_id, 0)
        if tokens > self._max_tokens:
            return DeadlockReport(
                triggered=True,
                level=2,
                reason=f"超出 Token 预算: {tokens}/{self._max_tokens}",
                details={"session_id": session_id, "tokens": tokens, "max_tokens": self._max_tokens},
            )

        # 时间检查
        start = self._session_start.get(session_id)
        if start:
            elapsed = time.time() - start
            if elapsed > self._max_duration:
                return DeadlockReport(
                    triggered=True,
                    level=2,
                    reason=f"超出执行时长上限: {elapsed:.0f}s/{self._max_duration}s",
                    details={"session_id": session_id, "elapsed": elapsed, "max_duration": self._max_duration},
                )

        return DeadlockReport()

    def clear(self, session_id: Optional[str] = None):
        """清除指定或全部预算数据。"""
        if session_id:
            self._session_turns.pop(session_id, None)
            self._session_tokens.pop(session_id, None)
            self._session_start.pop(session_id, None)
        else:
            self._session_turns.clear()
            self._session_tokens.clear()
            self._session_start.clear()


# ---------------------------------------------------------------------------
# Level 3 — 超时 / 无响应检测
# ---------------------------------------------------------------------------

class StallDetector:
    """
    Level 3: 检测无响应（stall）超时。

    如果在规定时间内没有收到任何心跳或进度更新，则触发。
    """

    def __init__(self, stall_timeout: float = 120.0, heartbeat_interval: float = 30.0):
        self._stall_timeout = stall_timeout
        self._heartbeat_interval = heartbeat_interval
        self._last_activity: dict[str, float] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def mark_activity(self, session_id: str):
        """标记活动时间戳。"""
        self._last_activity[session_id] = time.time()

    def start_monitoring(self, session_id: str):
        """开始监控指定会话。"""
        self.mark_activity(session_id)

    def stop_monitoring(self, session_id: Optional[str] = None):
        """停止监控。"""
        if session_id:
            self._last_activity.pop(session_id, None)
        else:
            self._last_activity.clear()

    def check(self, session_id: str) -> DeadlockReport:
        """检查指定会话是否超时无响应。"""
        last = self._last_activity.get(session_id)
        if last is None:
            return DeadlockReport()

        elapsed = time.time() - last
        if elapsed > self._stall_timeout:
            return DeadlockReport(
                triggered=True,
                level=3,
                reason=f"检测到无响应超时: {elapsed:.0f}s 无活动 (阈值 {self._stall_timeout}s)",
                details={"session_id": session_id, "elapsed": elapsed, "timeout": self._stall_timeout},
            )

        return DeadlockReport()

    async def start_background_check(self, session_id: str, interval: float = 10.0):
        """启动后台定期检查。"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._check_loop(session_id, interval))

    async def stop_background_check(self):
        """停止后台检查。"""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _check_loop(self, session_id: str, interval: float):
        while self._running:
            await asyncio.sleep(interval)
            report = self.check(session_id)
            if report.triggered:
                logger.warning("Stall 检测触发: %s", report.reason)
                # 触发回调由调用方处理


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------

class DeadlockDetector:
    """
    三层防死循环检测 — 统一入口。

    按顺序依次检查 Level 1 → Level 2 → Level 3，
    任意一层触发即返回。
    """

    def __init__(
        self,
        loop_window: int = 50,
        repeat_threshold: int = 5,
        max_turns: int = 100,
        max_tokens: int = 1_000_000,
        max_duration: int = 3600,
        stall_timeout: float = 120.0,
    ):
        self.loop = LoopDetector(max_window=loop_window, repeat_threshold=repeat_threshold)
        self.budget = BudgetDetector(
            max_turns=max_turns,
            max_tokens=max_tokens,
            max_duration_seconds=max_duration,
        )
        self.stall = StallDetector(stall_timeout=stall_timeout)

    def check_all(self, caller_id: str, session_id: str) -> DeadlockReport:
        """按 Level 1→2→3 顺序检查。"""
        # Level 1
        report = self.loop.check(caller_id)
        if report.triggered:
            return report

        # Level 2
        report = self.budget.check(session_id)
        if report.triggered:
            return report

        # Level 3
        report = self.stall.check(session_id)
        if report.triggered:
            return report

        return DeadlockReport()

    def clear_all(self, session_id: Optional[str] = None, caller_id: Optional[str] = None):
        """清除全部状态。"""
        self.loop.clear(caller_id)
        self.budget.clear(session_id)
        self.stall.stop_monitoring(session_id)
