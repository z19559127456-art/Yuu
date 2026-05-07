"""
安全模块 — 权限检查 / 审计日志 / 数据脱敏
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import AuditLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 脱敏模式 — 匹配常见敏感字段路径
SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(api[_-]?key|apikey|secret|password|token|credential|auth)"),
    re.compile(r"(?i)(sk-[a-zA-Z0-9]{20,}|fk[a-zA-Z0-9]{20,})"),  # OpenAI/Anthropic key
]

# 资源类型到所需工具权限的映射
RESOURCE_PERMISSION_MAP: dict[str, str] = {
    "web": "web",
    "ui": "ui_automation",
    "vision": "vision",
    "cli": "cli",
    "skill": "",           # 技能权限单独检查
    "agent": "",
    "config": "",
    "group": "",
    "memory": "",
}


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class PermissionResult:
    allowed: bool = True
    reason: str = ""

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reason": self.reason}


# ---------------------------------------------------------------------------
# 权限检查
# ---------------------------------------------------------------------------

class PermissionChecker:
    """
    权限检查器 — 验证 Agent 是否有权执行特定操作。

    检查链路：
    1. Agent tools_config 中对应工具是否启用
    2. 域名/命令白名单（如有）
    3. 安全策略文件（如存在）
    """

    @staticmethod
    def check_tool_enabled(agent: Any, tool_type: str) -> PermissionResult:
        """
        检查 Agent 的 tools_config 中指定工具是否启用。
        tool_type: cli / web / ui_automation / vision
        """
        try:
            tools_config = json.loads(getattr(agent, "tools_config_json", "{}") or "{}")
        except (json.JSONDecodeError, TypeError):
            tools_config = {}

        tool_cfg = tools_config.get(tool_type, {})
        if not tool_cfg.get("enabled", False):
            return PermissionResult(
                allowed=False,
                reason=f"Agent '{agent.name}' 未启用 {tool_type} 工具权限",
            )

        return PermissionResult()

    @staticmethod
    def check_domain_allowed(agent: Any, domain: str) -> PermissionResult:
        """检查域名是否在 Web 工具的白名单中。"""
        try:
            tools_config = json.loads(getattr(agent, "tools_config_json", "{}") or "{}")
        except (json.JSONDecodeError, TypeError):
            tools_config = {}

        web_cfg = tools_config.get("web", {})
        allowed = web_cfg.get("allowed_domains", [])
        blocked = web_cfg.get("blocked_domains", [])

        if allowed and domain not in allowed:
            return PermissionResult(
                allowed=False,
                reason=f"域名 '{domain}' 不在 Agent '{agent.name}' 的允许列表中",
            )

        if domain in blocked:
            return PermissionResult(
                allowed=False,
                reason=f"域名 '{domain}' 在 Agent '{agent.name}' 的阻止列表中",
            )

        return PermissionResult()

    @staticmethod
    def check_command_allowed(agent: Any, command: str) -> PermissionResult:
        """检查命令是否在 CLI 工具的白名单/黑名单中。"""
        try:
            tools_config = json.loads(getattr(agent, "tools_config_json", "{}") or "{}")
        except (json.JSONDecodeError, TypeError):
            tools_config = {}

        cli_cfg = tools_config.get("cli", {})
        allowed = cli_cfg.get("allowed_commands", [])
        blocked = cli_cfg.get("blocked_commands", [])

        if allowed:
            matched = any(cmd in command for cmd in allowed)
            if not matched:
                return PermissionResult(
                    allowed=False,
                    reason=f"命令不在允许列表中: {command[:100]}",
                )

        if blocked:
            matched = any(cmd in command for cmd in blocked)
            if matched:
                return PermissionResult(
                    allowed=False,
                    reason=f"命令在阻止列表中: {command[:100]}",
                )

        return PermissionResult()

    @staticmethod
    def check_agent_active(agent: Any) -> PermissionResult:
        """检查 Agent 是否处于活跃状态。"""
        if not getattr(agent, "is_active", True):
            return PermissionResult(
                allowed=False,
                reason=f"Agent '{agent.name}' 已被禁用",
            )
        return PermissionResult()

    @staticmethod
    def check_skill_allowed(agent: Any, skill_name: str) -> PermissionResult:
        """检查 Agent 是否有权调用指定技能。"""
        try:
            skills = json.loads(getattr(agent, "skills_json", "[]") or "[]")
        except (json.JSONDecodeError, TypeError):
            skills = []

        if skills and skill_name not in skills:
            return PermissionResult(
                allowed=False,
                reason=f"Agent '{agent.name}' 未授权使用技能 '{skill_name}'",
            )

        return PermissionResult()

    @staticmethod
    def check_all(agent: Any, resource_type: str, resource_id: str = "", **extra) -> PermissionResult:
        """综合权限检查 — 按资源类型执行一组检查。"""
        # Agent 活跃性
        r = PermissionChecker.check_agent_active(agent)
        if not r.allowed:
            return r

        # 工具权限
        perm_key = RESOURCE_PERMISSION_MAP.get(resource_type, "")
        if perm_key:
            r = PermissionChecker.check_tool_enabled(agent, perm_key)
            if not r.allowed:
                return r

        # 额外检查由调用方在 extra 中指定
        return PermissionResult()


# ---------------------------------------------------------------------------
# 审计日志
# ---------------------------------------------------------------------------

class AuditLogger:
    """
    审计日志写入器 — 记录安全敏感操作到 AuditLog 表。
    """

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        agent_id: str = "",
        resource_type: str = "",
        resource_id: str = "",
        details: Optional[dict] = None,
        ip_address: str = "",
    ) -> AuditLog:
        """
        写入审计日志。

        action 取值:
          - tool_call      工具调用
          - config_change  配置变更
          - skill_invoke   技能调用
          - permission_denied  权限拒绝
          - agent_create   创建 Agent
          - agent_delete   删除 Agent
          - group_action   群组操作
          - data_export    数据导出
          - login          登录
        """
        record = AuditLog(
            agent_id=agent_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=json.dumps(Sanitizer.sanitize_dict(details or {}), ensure_ascii=False),
            ip_address=ip_address,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        logger.info("审计日志: %s | %s | %s", action, resource_type, resource_id)
        return record

    def log_tool_call(
        self,
        agent_id: str,
        tool_type: str,
        tool_params: dict,
        result_status: str = "success",
        ip_address: str = "",
    ) -> AuditLog:
        """快捷记录工具调用。"""
        return self.log(
            action="tool_call",
            agent_id=agent_id,
            resource_type=tool_type,
            details={
                "params": tool_params,
                "status": result_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            ip_address=ip_address,
        )

    def log_permission_denied(
        self,
        agent_id: str,
        resource_type: str,
        reason: str,
        ip_address: str = "",
    ) -> AuditLog:
        """快捷记录权限拒绝。"""
        return self.log(
            action="permission_denied",
            agent_id=agent_id,
            resource_type=resource_type,
            details={"reason": reason},
            ip_address=ip_address,
        )

    def log_config_change(
        self,
        agent_id: str,
        changes: dict,
        ip_address: str = "",
    ) -> AuditLog:
        """快捷记录配置变更。"""
        return self.log(
            action="config_change",
            agent_id=agent_id,
            resource_type="config",
            details={"changes": changes},
            ip_address=ip_address,
        )

    def query(
        self,
        agent_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[AuditLog]:
        """查询审计日志。"""
        q = self.db.query(AuditLog)
        if agent_id:
            q = q.filter(AuditLog.agent_id == agent_id)
        if action:
            q = q.filter(AuditLog.action == action)
        if resource_type:
            q = q.filter(AuditLog.resource_type == resource_type)
        return q.order_by(AuditLog.created_at.desc()).limit(limit).all()


# ---------------------------------------------------------------------------
# 数据脱敏
# ---------------------------------------------------------------------------

class Sanitizer:
    """数据脱敏工具 — 清洗敏感信息。"""

    # 敏感字段名（大小写不敏感）
    SENSITIVE_FIELDS: set[str] = {
        "api_key", "api_key", "apikey", "secret", "password",
        "token", "credential", "auth", "private_key", "access_key",
        "secret_key", "session_key",
    }

    # 替换值
    MASK = "****"

    @staticmethod
    def sanitize_value(key: str, value: Any) -> Any:
        """对单个值进行脱敏。"""
        if not isinstance(value, str):
            return value

        if key.lower() in Sanitizer.SENSITIVE_FIELDS:
            if len(value) <= 8:
                return Sanitizer.MASK
            return value[:4] + Sanitizer.MASK + value[-4:]

        # API Key 格式自动检测
        for pattern in SENSITIVE_PATTERNS[1:]:
            if pattern.search(value):
                return value[:8] + Sanitizer.MASK + value[-4:]

        return value

    @staticmethod
    def sanitize_dict(data: dict, depth: int = 0) -> dict:
        """递归脱敏字典中的所有敏感字段。"""
        if depth > 10:
            return {"__truncated__": True}

        result = {}
        for key, value in data.items():
            # 键名匹配敏感词
            if Sanitizer._is_sensitive_key(key):
                result[key] = Sanitizer.sanitize_value(key, value)
            elif isinstance(value, dict):
                result[key] = Sanitizer.sanitize_dict(value, depth + 1)
            elif isinstance(value, list):
                result[key] = [
                    Sanitizer.sanitize_dict(item, depth + 1)
                    if isinstance(item, dict)
                    else Sanitizer.sanitize_value(key, item)
                    for item in value
                ]
            else:
                result[key] = value
        return result

    @staticmethod
    def sanitize_text(text: str) -> str:
        """脱敏文本中的密钥字符串。"""
        result = text
        # 替换常见的密钥格式
        result = re.sub(
            r'(?i)(api[_-]?key|apikey|secret|password|token)[=:]\s*["\']?\S+["\']?',
            r'\1=****',
            result,
        )
        # 替换 sk- / fk- 开头的密钥
        result = re.sub(r'(sk-[a-zA-Z0-9]{20,})', 'sk-****', result)
        return result

    @staticmethod
    def _is_sensitive_key(key: str) -> bool:
        return key.lower() in Sanitizer.SENSITIVE_FIELDS
