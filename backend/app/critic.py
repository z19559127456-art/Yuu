"""
Critic — validates worker output quality, scores, and provides revision feedback.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.llm_client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """你是一个质量评审专家。请评审以下子任务的执行结果。

子任务标题：{标题}
子任务描述：{描述}

执行结果：
{输出}

请从以下维度评审（每项 1-10 分）：
1. **完整性（completeness）** — 结果是否全面覆盖了子任务要求？
2. **正确性（correctness）** — 结果是否准确、无错误？
3. **清晰度（clarity）** — 结果是否结构清晰、易于理解？
4. **可执行性（actionability）** — 结果是否能直接用于下一步？

以 JSON 格式返回：
{{
  "passed": true/false,
  "score": {{ "completeness": 0, "correctness": 0, "clarity": 0, "actionability": 0 }},
  "summary": "总体评价",
  "issues": ["问题1", "问题2"],
  "suggestions": ["改进建议1", "改进建议2"],
  "verdict": "approved / minor_revision / major_revision / rejected"
}}

评分规则：
- approved: 所有维度 >= 7 分
- minor_revision: 有维度 5-6 分，需小改
- major_revision: 有维度 3-4 分，需大改
- rejected: 有维度 < 3 分，完全不可接受
"""


@dataclass
class ReviewScore:
    completeness: float = 0
    correctness: float = 0
    clarity: float = 0
    actionability: float = 0

    @property
    def average(self) -> float:
        return (self.completeness + self.correctness + self.clarity + self.actionability) / 4.0


@dataclass
class ReviewResult:
    passed: bool = False
    score: ReviewScore = field(default_factory=ReviewScore)
    summary: str = ""
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    verdict: str = "rejected"

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": {
                "completeness": self.score.completeness,
                "correctness": self.score.correctness,
                "clarity": self.score.clarity,
                "actionability": self.score.actionability,
            },
            "summary": self.summary,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "verdict": self.verdict,
        }


class Critic:
    """Validates subtask output quality using an LLM judge."""

    def __init__(self, db: Session, api_keys: dict):
        self.db = db
        self.api_keys = api_keys

    async def review(
        self,
        provider: str,
        model: str,
        title: str,
        description: str,
        output: str,
    ) -> ReviewResult:
        """Review a subtask execution result."""
        llm = LLMClient(LLMConfig(
            provider=provider,
            model=model,
            temperature=0.2,
            max_tokens=2048,
            api_key=self.api_keys.get(provider, ""),
        ))

        prompt = CRITIC_PROMPT.format(
            标题=title,
            描述=description,
            输出=output,
        )

        messages = [
            {"role": "system", "content": "你是一个质量评审专家。只输出 JSON，不要包含其他内容。"},
            {"role": "user", "content": prompt},
        ]

        try:
            raw = await llm.complete(messages)
            return self._parse_review(raw)
        except Exception as e:
            logger.error("Critic review failed: %s", e)
            return ReviewResult(
                passed=False,
                summary=f"评审过程出错: {e}",
                verdict="major_revision",
            )

    def should_retry(self, result: ReviewResult, max_retries: int = 2) -> bool:
        """Determine if the subtask should be retried based on review."""
        if result.verdict in ("approved", "minor_revision"):
            return False
        # major_revision / rejected → retry
        return True

    def _parse_review(self, raw: str) -> ReviewResult:
        text = raw.strip()
        if text.startswith("```"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse critic JSON: %s", raw[:100])
            return ReviewResult(passed=False, summary="评审输出解析失败", verdict="major_revision")

        score_data = data.get("score", {})
        score = ReviewScore(
            completeness=score_data.get("completeness", 0),
            correctness=score_data.get("correctness", 0),
            clarity=score_data.get("clarity", 0),
            actionability=score_data.get("actionability", 0),
        )

        return ReviewResult(
            passed=data.get("passed", False),
            score=score,
            summary=data.get("summary", ""),
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            verdict=data.get("verdict", "rejected"),
        )
