"""
内置技能包 — 所有技能模块在此注册
"""
from app.skill_manager import registry, Skill
from app.skills.code_review import CodeReviewSkill
from app.skills.summarize import SummarizeSkill

# 自动注册内置技能
registry.register(CodeReviewSkill())
registry.register(SummarizeSkill())

__all__ = ["registry", "Skill", "CodeReviewSkill", "SummarizeSkill"]
