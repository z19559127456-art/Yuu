"""
内置技能：文本总结
"""
import re
from app.skill_manager import Skill, SkillResult


class SummarizeSkill(Skill):
    name = "summarize"
    description = "对文本内容进行总结、提取关键信息"
    version = "1.0.0"
    requires_llm = False

    FORMAT_OPTIONS = ("paragraph", "bullet", "json")

    def validate_params(self, text: str = "", **kwargs) -> str | None:
        if not text.strip():
            return "text 参数不能为空"
        fmt = kwargs.get("format", "paragraph")
        if fmt not in self.FORMAT_OPTIONS:
            return f"不支持的格式: {fmt}，可选: {', '.join(self.FORMAT_OPTIONS)}"
        return None

    async def execute(
        self,
        text: str = "",
        max_length: int = 200,
        format: str = "paragraph",
        **kwargs,
    ) -> SkillResult:
        if not text.strip():
            return SkillResult(success=False, error="文本内容为空")

        # 简单的提取式总结
        sentences = self._split_sentences(text)
        word_count = len(text.split())

        if len(sentences) <= 3:
            # 太短就直接返回原文精简
            summary = text.strip()[:max_length]
        else:
            # 提取关键句：统计词频，选 Top N 句子中最相关的
            important = self._extract_important_sentences(sentences, max_sentences=5)
            summary = " ".join(important)

        if len(summary) > max_length:
            summary = summary[:max_length].rsplit("。", 1)[0] + "。"

        if format == "bullet":
            bullet_items = [s.strip() for s in self._split_sentences(summary) if len(s.strip()) > 5]
            formatted = "\n".join(f"- {s}" for s in bullet_items[:6])
        elif format == "json":
            formatted = json.dumps({
                "summary": summary[:max_length],
                "sentence_count": len(sentences),
                "word_count": word_count,
            }, ensure_ascii=False)
        else:
            formatted = summary

        return SkillResult(
            output=formatted,
            metadata={
                "original_length": len(text),
                "original_words": word_count,
                "sentence_count": len(sentences),
                "summary_length": len(summary),
            },
        )

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        text = re.sub(r"\s+", " ", text).strip()
        raw = re.split(r"(?<=[。！？.!?])\s*", text)
        return [s.strip() for s in raw if s.strip()]

    @staticmethod
    def _extract_important_sentences(sentences: list[str], max_sentences: int) -> list[str]:
        # 基于词频的简单打分：高频词所在的句子更可能重要
        word_freq: dict[str, int] = {}
        for sent in sentences:
            for w in sent.split():
                w = w.strip("，。,.").lower()
                if len(w) > 1:
                    word_freq[w] = word_freq.get(w, 0) + 1

        scored = []
        for sent in sentences:
            score = sum(word_freq.get(w.strip("，。,.").lower(), 0) for w in sent.split())
            scored.append((score, sent))

        scored.sort(key=lambda x: -x[0])
        important = [s for _, s in scored[:max_sentences]]

        # 保留首句
        if sentences and sentences[0] not in important:
            important.insert(0, sentences[0])
            important = important[:max_sentences]

        return important


# 避免 __init__.py 中引用 json 报 circular import
import json  # noqa: E402
