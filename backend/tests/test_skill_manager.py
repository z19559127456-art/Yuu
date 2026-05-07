"""
Tests for Skill Manager — registry, execution, hot reload, skill base class.
"""
import pytest
from app.skill_manager import Skill, SkillResult, SkillRegistry, registry


class TestSkillBase:
    def test_base_execute_raises(self):
        skill = Skill()
        import asyncio
        with pytest.raises(NotImplementedError):
            asyncio.run(skill.execute())

    def test_validate_params_default(self):
        skill = Skill()
        result = skill.validate_params(key="value")
        assert result is None

    def test_skill_attributes(self):
        skill = Skill()
        assert skill.name == "base_skill"
        assert skill.version == "1.0.0"
        assert skill.description == ""
        assert skill.requires_llm is False


class TestSkillResult:
    def test_success_default(self):
        r = SkillResult()
        assert r.success is True
        assert r.output == ""
        assert r.error == ""

    def test_custom_result(self):
        r = SkillResult(success=False, error="something wrong", duration_ms=150.0)
        assert r.success is False
        assert r.error == "something wrong"
        assert r.duration_ms == 150.0


class TestSkillRegistry:
    def test_register_and_get(self):
        reg = SkillRegistry()
        skill = Skill()
        skill.name = "test_skill"
        reg.register(skill)
        assert reg.contains("test_skill")
        retrieved = reg.get("test_skill")
        assert retrieved is skill

    def test_unregister(self):
        reg = SkillRegistry()
        skill = Skill()
        skill.name = "temp_skill"
        reg.register(skill)
        reg.unregister("temp_skill")
        assert not reg.contains("temp_skill")

    def test_get_nonexistent(self):
        reg = SkillRegistry()
        assert reg.get("nonexistent") is None

    def test_list_skills(self):
        reg = SkillRegistry()
        s1 = Skill()
        s1.name = "skill_a"
        s1.description = "Skill A"
        s1.version = "1.0"
        s2 = Skill()
        s2.name = "skill_b"
        s2.description = "Skill B"
        s2.requires_llm = True
        reg.register(s1)
        reg.register(s2)
        skills = reg.list_skills()
        assert len(skills) == 2
        names = [s["name"] for s in skills]
        assert "skill_a" in names
        assert "skill_b" in names

    def test_execute_success(self):
        reg = SkillRegistry()
        class HelloSkill(Skill):
            name = "hello"
            async def execute(self, **kwargs):
                return SkillResult(success=True, output=f"Hello, {kwargs.get('target', 'world')}!")
        reg.register(HelloSkill())
        import asyncio
        result = asyncio.run(reg.execute("hello", target="测试"))
        assert result.success is True
        assert "测试" in result.output

    def test_execute_not_found(self):
        reg = SkillRegistry()
        import asyncio
        result = asyncio.run(reg.execute("nonexistent"))
        assert result.success is False
        assert "未找到" in result.error

    def test_execute_validation_error(self):
        reg = SkillRegistry()
        class StrictSkill(Skill):
            name = "strict"
            def validate_params(self, **kwargs):
                if "name" not in kwargs:
                    return "缺少 name 参数"
                return None
            async def execute(self, **kwargs):
                return SkillResult(success=True, output="ok")
        reg.register(StrictSkill())
        import asyncio
        result = asyncio.run(reg.execute("strict"))
        assert result.success is False
        assert "name" in result.error

    def test_execute_exception_handling(self):
        reg = SkillRegistry()
        class BrokenSkill(Skill):
            name = "broken"
            async def execute(self, **kwargs):
                raise ValueError("something broke")
        reg.register(BrokenSkill())
        import asyncio
        result = asyncio.run(reg.execute("broken"))
        assert result.success is False
        assert "ValueError" in result.error

    def test_thread_safety(self):
        """Register from multiple threads should not crash."""
        import threading
        reg = SkillRegistry()
        def register_skill(n):
            s = Skill()
            s.name = f"thread_skill_{n}"
            reg.register(s)
        threads = [threading.Thread(target=register_skill, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(reg.list_skills()) == 10

    def test_global_registry_singleton(self):
        assert registry is not None
        assert isinstance(registry, SkillRegistry)

    def test_discover_and_register_nonexistent_dir(self):
        reg = SkillRegistry()
        # Should not crash
        reg.discover_and_register("/nonexistent_dir", reg)

    def test_hot_reload_nonexistent_dir(self):
        reg = SkillRegistry()
        # Should not crash
        reg.hot_reload("/nonexistent_dir")
