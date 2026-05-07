"""
Skill 插件管理 — 基类 / 注册中心 / 热重载
"""
import os
import sys
import json
import time
import logging
import importlib
import traceback
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class SkillResult:
    success: bool = True
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


class Skill:
    """所有技能的基类。"""

    name: str = "base_skill"
    description: str = ""
    version: str = "1.0.0"
    requires_llm: bool = False

    async def execute(self, **kwargs) -> SkillResult:
        """执行技能 — 子类必须实现。"""
        raise NotImplementedError

    def validate_params(self, **kwargs) -> Optional[str]:
        """参数校验，返回 None 表示通过，否则返回错误描述。"""
        return None


class SkillRegistry:
    """技能注册中心 — 管理所有可用技能。"""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._lock = Lock()

    # ------------------------------------------------------------------
    # 注册 / 查询
    # ------------------------------------------------------------------

    def register(self, skill: Skill):
        with self._lock:
            self._skills[skill.name] = skill
            logger.info("技能已注册: %s v%s", skill.name, skill.version)

    def unregister(self, name: str):
        with self._lock:
            self._skills.pop(name, None)

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "version": s.version,
                "requires_llm": s.requires_llm,
            }
            for s in self._skills.values()
        ]

    def contains(self, name: str) -> bool:
        return name in self._skills

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    async def execute(self, name: str, **kwargs) -> SkillResult:
        skill = self.get(name)
        if not skill:
            return SkillResult(success=False, error=f"技能 '{name}' 未找到")

        param_err = skill.validate_params(**kwargs)
        if param_err:
            return SkillResult(success=False, error=param_err)

        start = time.perf_counter()
        try:
            result = await skill.execute(**kwargs)
            result.duration_ms = (time.perf_counter() - start) * 1000
            return result
        except Exception as e:
            logger.exception("技能 '%s' 执行失败", name)
            return SkillResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

    # ------------------------------------------------------------------
    # 热重载 — 扫描 skills 目录下的 .py 文件，重新 import
    # ------------------------------------------------------------------

    def hot_reload(self, skills_dir: str | Path):
        """扫描 skills_dir 下的所有 .py 文件并重载。"""
        path = Path(skills_dir)
        if not path.is_dir():
            logger.warning("技能目录不存在: %s", path)
            return

        for fpath in sorted(path.glob("*.py")):
            if fpath.name.startswith("_"):
                continue
            mod_name = f"app.skills.{fpath.stem}"
            try:
                if mod_name in sys.modules:
                    importlib.reload(sys.modules[mod_name])
                else:
                    importlib.import_module(mod_name)
                logger.info("热重载技能模块: %s", mod_name)
            except Exception:
                logger.error("热重载失败 %s\n%s", mod_name, traceback.format_exc())

    def discover_and_register(self, skills_dir: str | Path, registry: "SkillRegistry"):
        """扫描目录并自动注册所有技能实例。"""
        path = Path(skills_dir)
        if not path.is_dir():
            logger.warning("技能目录不存在: %s", path)
            return

        for fpath in sorted(path.glob("*.py")):
            if fpath.name.startswith("_"):
                continue
            mod_name = f"app.skills.{fpath.stem}"
            try:
                mod = importlib.import_module(mod_name)
                self._register_from_module(mod, registry)
            except Exception:
                logger.error("加载技能模块失败 %s\n%s", mod_name, traceback.format_exc())

    @staticmethod
    def _register_from_module(mod, registry: "SkillRegistry"):
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, type) and issubclass(attr, Skill) and attr is not Skill:
                try:
                    instance = attr()
                    registry.register(instance)
                except Exception as e:
                    logger.warning("实例化技能 %s 失败: %s", attr_name, e)


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
registry = SkillRegistry()
