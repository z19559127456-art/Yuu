"""
CLI Tool — safe command execution with whitelist/blacklist, sandbox, and streaming.
"""
import asyncio
import re
import shlex
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    allowed: bool
    reason: str = ""


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    output_type: str = "text"
    stderr: str = ""
    execution_time_ms: int = 0
    metadata: dict = field(default_factory=dict)


# Built-in dangerous patterns
BLOCKED_PATTERNS = [
    r"rm\s+-rf",
    r"del\s+/[fFsS]",
    r"format\s+[A-Za-z]:",
    r"shutdown",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\};\s*:",  # fork bomb
    r"base64.*\|.*bash",
    r"curl.*\|.*sh",
    r"wget.*\|.*sh",
    r"powershell.*-nop.*-c",
    r"Invoke-Expression",
    r"iex\s*\(",
    r"reg\s+add",
    r"reg\s+delete",
    r"net\s+user",
    r"netsh\s+firewall",
    r"sc\s+config",
    r"schtasks",
    r"sudo",
]

SENSITIVE_DIRECTORIES = [
    r"C:\\Windows",
    r"C:\\Program Files",
    r"C:\\Program Files \(x86\)",
]


class CLITool:
    """Safe command execution tool with configurable permissions."""

    def __init__(
        self,
        allowed_commands: list[str] | None = None,
        blocked_commands: list[str] | None = None,
        allowed_directories: list[str] | None = None,
        blocked_directories: list[str] | None = None,
        working_directory: str = "",
        timeout_seconds: int = 30,
    ):
        self.allowed_commands = allowed_commands or []
        self.blocked_commands = blocked_commands or []
        self.allowed_directories = allowed_directories or []
        self.blocked_directories = blocked_directories or []
        self.working_directory = working_directory
        self.timeout_seconds = timeout_seconds

    async def execute(
        self,
        command: str,
        cancel_token: asyncio.Event | None = None,
        on_stdout=None,
        on_stderr=None,
    ) -> ToolResult:
        """Execute a command with safety checks."""
        import time

        # 1. Safety check
        safety = self._check_safety(command)
        if not safety.allowed:
            return ToolResult(
                success=False,
                output="",
                output_type="error",
                stderr=safety.reason,
            )

        # 2. Execute via asyncio subprocess
        start = time.monotonic()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory or None,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                output_type="error",
                stderr=str(e),
            )

        stdout_chunks = []
        stderr_chunks = []

        async def read_stream(stream, chunks, callback):
            while True:
                chunk = await stream.read(4096)
                if not chunk:
                    break
                decoded = chunk.decode("utf-8", errors="replace")
                chunks.append(decoded)
                if callback:
                    callback(decoded)

        async def cancel_monitor():
            if cancel_token is None:
                return
            await cancel_token.wait()
            try:
                process.terminate()
                await asyncio.sleep(1)
                if process.returncode is None:
                    process.kill()
            except Exception:
                pass

        tasks = [
            read_stream(process.stdout, stdout_chunks, on_stdout),
            read_stream(process.stderr, stderr_chunks, on_stderr),
        ]
        if cancel_token is not None:
            tasks.append(cancel_monitor())

        await asyncio.gather(*tasks, return_exceptions=True)

        try:
            await asyncio.wait_for(process.wait(), timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            elapsed = int((time.monotonic() - start) * 1000)
            return ToolResult(
                success=False,
                output="".join(stdout_chunks),
                output_type="text",
                stderr="[超时] 命令执行超过限制时间",
                execution_time_ms=elapsed,
            )

        elapsed = int((time.monotonic() - start) * 1000)
        return ToolResult(
            success=process.returncode == 0,
            output="".join(stdout_chunks),
            output_type="text",
            stderr="".join(stderr_chunks),
            execution_time_ms=elapsed,
        )

    def _check_safety(self, command: str) -> SafetyResult:
        """Check command against whitelist/blacklist and directory restrictions."""
        # Check blocked patterns
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return SafetyResult(allowed=False, reason=f"命令被禁止（匹配危险模式）")

        # Check blocked commands
        try:
            cmd_parts = shlex.split(command)
        except ValueError:
            return SafetyResult(allowed=False, reason="无法解析命令")
        if not cmd_parts:
            return SafetyResult(allowed=False, reason="空命令")

        base_cmd = cmd_parts[0].lower()

        if self.blocked_commands:
            for blocked in self.blocked_commands:
                if blocked.lower() in command.lower():
                    return SafetyResult(allowed=False, reason=f"命令在黑名单中: {blocked}")

        if self.allowed_commands:
            if base_cmd not in [c.lower() for c in self.allowed_commands]:
                return SafetyResult(allowed=False, reason=f"命令不在白名单中: {base_cmd}")

        # Check directory restrictions
        if self.working_directory:
            wd_lower = self.working_directory.lower()

            for blocked_dir in self.blocked_directories:
                if wd_lower.startswith(blocked_dir.lower()):
                    return SafetyResult(allowed=False, reason="目录被禁止访问")

            if self.allowed_directories:
                allowed = any(
                    wd_lower.startswith(d.lower())
                    for d in self.allowed_directories
                )
                if not allowed:
                    return SafetyResult(allowed=False, reason="目录不在白名单中")

        return SafetyResult(allowed=True)
