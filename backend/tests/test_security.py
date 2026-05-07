"""
Tests for Security module — PermissionChecker, AuditLogger, Sanitizer.
"""
import json
import pytest
from app.security import (
    PermissionChecker, AuditLogger, Sanitizer,
    PermissionResult,
)


class TestPermissionChecker:
    def test_check_tool_enabled(self, sample_agent):
        r = PermissionChecker.check_tool_enabled(sample_agent, "cli")
        assert r.allowed is True

    def test_check_tool_disabled(self, sample_agent):
        r = PermissionChecker.check_tool_enabled(sample_agent, "web")
        assert r.allowed is False
        assert "未启用" in r.reason

    def test_check_agent_active(self, sample_agent):
        r = PermissionChecker.check_agent_active(sample_agent)
        assert r.allowed is True

    def test_check_agent_inactive(self, db_session):
        from app.models import Agent
        agent = Agent(name="禁用", is_active=False)
        db_session.add(agent)
        db_session.commit()
        r = PermissionChecker.check_agent_active(agent)
        assert r.allowed is False
        assert "禁用" in r.reason

    def test_check_skill_allowed(self, sample_agent):
        r = PermissionChecker.check_skill_allowed(sample_agent, "code_review")
        assert r.allowed is True

    def test_check_skill_not_allowed(self, sample_agent):
        r = PermissionChecker.check_skill_allowed(sample_agent, "hacking")
        assert r.allowed is False
        assert "未授权" in r.reason

    def test_check_command_allowed_with_whitelist(self, sample_agent):
        r = PermissionChecker.check_command_allowed(sample_agent, "ls -la")
        assert r.allowed is True

    def test_check_command_not_in_whitelist(self, sample_agent):
        r = PermissionChecker.check_command_allowed(sample_agent, "ping 8.8.8.8")
        assert r.allowed is False

    def test_check_command_blocked(self, sample_agent):
        r = PermissionChecker.check_command_allowed(sample_agent, "rm file.txt")
        assert r.allowed is False

    def test_check_domain_allowed_no_restriction(self, db_session):
        """When no domains configured, all domains should be allowed."""
        from app.models import Agent
        agent = Agent(name="自由", tools_config_json=json.dumps({
            "web": {"enabled": True, "allowed_domains": [], "blocked_domains": []},
        }))
        db_session.add(agent)
        db_session.commit()
        r = PermissionChecker.check_domain_allowed(agent, "https://example.com")
        assert r.allowed is True

    def test_check_domain_blocked(self, db_session):
        from app.models import Agent
        agent = Agent(name="受限", tools_config_json=json.dumps({
            "web": {"enabled": True, "allowed_domains": [], "blocked_domains": ["evil.com"]},
        }))
        db_session.add(agent)
        db_session.commit()
        r = PermissionChecker.check_domain_allowed(agent, "evil.com")
        assert r.allowed is False

    def test_check_all_integrated(self, sample_agent):
        r = PermissionChecker.check_all(sample_agent, "cli")
        assert r.allowed is True

    def test_check_all_disabled_tool(self, sample_agent):
        r = PermissionChecker.check_all(sample_agent, "web")
        assert r.allowed is False

    def test_permission_result_dataclass(self):
        r = PermissionResult()
        assert r.allowed is True
        assert r.reason == ""
        d = r.to_dict()
        assert d["allowed"] is True


class TestAuditLogger:
    def test_log_creates_record(self, db_session):
        logger = AuditLogger(db_session)
        record = logger.log(
            action="tool_call",
            agent_id="agent-1",
            resource_type="web",
            resource_id="https://example.com",
            details={"url": "https://example.com"},
        )
        assert record.id is not None
        assert record.action == "tool_call"
        assert record.ip_address == ""

    def test_log_tool_call(self, db_session):
        logger = AuditLogger(db_session)
        record = logger.log_tool_call(
            agent_id="agent-1",
            tool_type="cli",
            tool_params={"command": "ls"},
            result_status="success",
        )
        assert record.action == "tool_call"
        assert record.resource_type == "cli"

    def test_log_permission_denied(self, db_session):
        logger = AuditLogger(db_session)
        record = logger.log_permission_denied(
            agent_id="agent-1",
            resource_type="web",
            reason="domain not allowed",
        )
        assert record.action == "permission_denied"
        assert "domain" in record.details_json

    def test_log_config_change(self, db_session):
        logger = AuditLogger(db_session)
        record = logger.log_config_change(
            agent_id="agent-1",
            changes={"temperature": 0.8},
        )
        assert record.action == "config_change"

    def test_query_by_action(self, db_session):
        logger = AuditLogger(db_session)
        logger.log(action="tool_call", agent_id="a1")
        logger.log(action="tool_call", agent_id="a2")
        logger.log(action="config_change", agent_id="a1")
        results = logger.query(action="tool_call")
        assert len(results) == 2

    def test_query_by_agent(self, db_session):
        logger = AuditLogger(db_session)
        logger.log(action="tool_call", agent_id="a1")
        logger.log(action="tool_call", agent_id="a2")
        results = logger.query(agent_id="a1")
        assert len(results) == 1
        assert results[0].agent_id == "a1"


class TestSanitizer:
    def test_sanitize_api_key(self):
        result = Sanitizer.sanitize_value("api_key", "sk-abcdefghijklmnopqrstuvwxyz")
        assert "****" in result
        assert "abcdef" not in result

    def test_sanitize_password(self):
        """Values > 8 chars get partial masking (first 4 + **** + last 4)."""
        result = Sanitizer.sanitize_value("password", "mysecret123")
        assert result == "myse****t123"

    def test_sanitize_short_value(self):
        result = Sanitizer.sanitize_value("token", "abc")
        assert result == "****"

    def test_partial_mask_long_key(self):
        result = Sanitizer.sanitize_value("api_key", "sk-abcdefghijklmnopqrstuvwxyz123")
        assert result.startswith("sk-a")
        assert "****" in result

    def test_sanitize_dict_recursive(self):
        data = {
            "name": "test",
            "api_key": "sk-1234567890abcdef1234567890abcdef",
            "nested": {
                "secret": "mysecret",
                "normal": "hello",
            },
            "items": [
                {"token": "abc123", "value": 42},
            ],
        }
        result = Sanitizer.sanitize_dict(data)
        assert result["name"] == "test"
        assert "****" in result["api_key"]
        assert "****" in result["nested"]["secret"]
        assert result["nested"]["normal"] == "hello"
        assert "****" in result["items"][0]["token"]
        assert result["items"][0]["value"] == 42

    def test_sanitize_depth_limit(self):
        deep = {}
        current = deep
        for i in range(15):
            current["nested"] = {}
            current = current["nested"]
        current["secret"] = "hidden"

        result = Sanitizer.sanitize_dict(deep, depth=0)
        # Should not crash, depth limit should prevent infinite recursion

    def test_sanitize_text_api_key_pattern(self):
        text = "api_key=sk-abcdefghijklmnopqrstuvwxyz123456"
        result = Sanitizer.sanitize_text(text)
        assert "****" in result
        assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in result

    def test_sanitize_text_sk_pattern(self):
        text = "key is sk-abcdefghijklmnopqrstuvwxyz1234567890"
        result = Sanitizer.sanitize_text(text)
        assert "sk-****" in result

    def test_non_sensitive_value_passes(self):
        result = Sanitizer.sanitize_value("name", "hello")
        assert result == "hello"
