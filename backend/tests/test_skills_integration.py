"""
技能模块集成测试 — 测试 CodeReviewSkill 和 SummarizeSkill 的完整执行流程。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import os
import tempfile
import pytest

from app.skill_manager import SkillRegistry, SkillResult


# ---------------------------------------------------------------------------
# CodeReviewSkill
# ---------------------------------------------------------------------------

class TestCodeReviewSkill:

    @pytest.fixture
    def registry(self):
        r = SkillRegistry()
        from app.skills.code_review import CodeReviewSkill
        r.register(CodeReviewSkill())
        return r

    @pytest.mark.asyncio
    async def test_detect_danger_patterns(self, registry):
        """应检测到危险代码模式。"""
        code = """
import os
os.system("rm -rf /")
eval("print('hello')")
        """
        result = await registry.execute("code_review", code=code, language="python")

        assert result.success is True
        assert result.metadata["summary"]["danger_count"] >= 2
        os_system_found = any("os.system" in f["message"] for f in result.metadata["findings"])
        eval_found = any("eval()" in f["message"] for f in result.metadata["findings"])
        assert os_system_found or eval_found

    @pytest.mark.asyncio
    async def test_detect_warning_patterns(self, registry):
        """应检测到警告级别的模式。"""
        code = """
try:
    do_something()
except:
    pass
        """
        result = await registry.execute("code_review", code=code, language="python")

        assert result.success is True
        warnings = result.metadata["summary"]["warning_count"]
        assert warnings >= 1
        # 检查是否报告了裸 except
        bare_except = any("裸 except" in f["message"] for f in result.metadata["findings"])
        assert bare_except

    @pytest.mark.asyncio
    async def test_detect_info_patterns(self, registry):
        """应检测到信息级别的模式。"""
        code = '''
# TODO: implement this
if len(items) != 0:
    print("has items")
        '''
        result = await registry.execute("code_review", code=code, language="python")

        assert result.success is True
        info_count = result.metadata["summary"]["info_count"]
        assert info_count >= 1

    @pytest.mark.asyncio
    async def test_clean_code_no_findings(self, registry):
        """干净的代码不应有问题。"""
        code = """def add(a: int, b: int) -> int:
    return a + b
"""
        result = await registry.execute("code_review", code=code, language="python")

        assert result.success is True
        summary = result.metadata["summary"]
        assert summary["danger_count"] == 0
        assert summary["warning_count"] == 0

    @pytest.mark.asyncio
    async def test_empty_code_error(self, registry):
        """空代码应返回错误。"""
        result = await registry.execute("code_review", code="   ", language="")

        assert result.success is False
        assert "内容为空" in result.error

    @pytest.mark.asyncio
    async def test_missing_code_and_file(self, registry):
        """缺少 code 和 file_path 应通过参数校验报错。"""
        result = await registry.execute("code_review", language="python")

        assert result.success is False
        assert "至少需要提供一个" in result.error

    @pytest.mark.asyncio
    async def test_read_from_file(self, registry):
        """应从文件读取代码。"""
        code = "# TODO: fix this\ndef foo():\n    pass\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            fpath = f.name

        try:
            result = await registry.execute("code_review", file_path=fpath, language="python")

            assert result.success is True
            # 应检测到 TODO
            todo_found = any("TODO" in f["message"] for f in result.metadata["findings"])
            assert todo_found
        finally:
            os.unlink(fpath)

    @pytest.mark.asyncio
    async def test_file_not_found(self, registry):
        """文件不存在时应报错。"""
        result = await registry.execute("code_review", file_path="/nonexistent/file.py")

        assert result.success is False
        assert "文件" in result.error

    @pytest.mark.asyncio
    async def test_output_format(self, registry):
        """输出应包含结构化的审查结果。"""
        code = "eval('1+1')\n"
        result = await registry.execute("code_review", code=code, language="python")

        assert "## 代码审查结果" in result.output
        assert "总行数" in result.output
        assert "严重问题" in result.output

    @pytest.mark.asyncio
    async def test_line_numbers_are_correct(self, registry):
        """报告的行号应与源代码行号一致。"""
        code = """
def foo():
    pass

eval("bad")
"""
        result = await registry.execute("code_review", code=code, language="python")

        eval_finding = next(
            (f for f in result.metadata["findings"] if "eval()" in f["message"]),
            None,
        )
        assert eval_finding is not None
        assert eval_finding["line"] == 5


# ---------------------------------------------------------------------------
# SummarizeSkill
# ---------------------------------------------------------------------------

class TestSummarizeSkill:

    @pytest.fixture
    def registry(self):
        r = SkillRegistry()
        from app.skills.summarize import SummarizeSkill
        r.register(SummarizeSkill())
        return r

    @pytest.mark.asyncio
    async def test_summarize_short_text(self, registry):
        """短文本（<=3句）应返回原文精简。"""
        result = await registry.execute("summarize", text="这是一段简短的文本。")

        assert result.success is True
        assert "简短的文本" in result.output

    @pytest.mark.asyncio
    async def test_summarize_long_text(self, registry):
        """长文本应提取关键句并总结。"""
        text = (
            "人工智能发展迅速。当前深度学习模型在很多领域取得了突破性进展。"
            "自然语言处理是AI的一个重要分支。计算机视觉也取得了长足进步。"
            "强化学习在游戏和机器人领域表现出色。未来AI将继续影响各行各业。"
        )
        result = await registry.execute("summarize", text=text, max_length=500)

        assert result.success is True
        assert len(result.output) > 0
        assert result.metadata["sentence_count"] >= 4

    @pytest.mark.asyncio
    async def test_summarize_empty_text(self, registry):
        """空文本应返回错误。"""
        result = await registry.execute("summarize", text="   ")

        assert result.success is False
        assert "不能为空" in result.error

    @pytest.mark.asyncio
    async def test_validate_empty_text(self, registry):
        """参数校验应拒绝空文本。"""
        result = await registry.execute("summarize", text="")

        assert result.success is False
        assert "text" in result.error.lower() or "不能为空" in result.error

    @pytest.mark.asyncio
    async def test_bullet_format(self, registry):
        """bullet 格式应输出 Markdown 列表。"""
        text = "第一点很重要。第二点也很关键。第三点值得注意。第四点同样有价值。"
        result = await registry.execute("summarize", text=text, format="bullet")

        assert result.success is True
        lines = result.output.strip().split("\n")
        assert any(line.startswith("- ") for line in lines)

    @pytest.mark.asyncio
    async def test_json_format(self, registry):
        """json 格式应输出有效的 JSON。"""
        text = "这是一个测试文本。用于验证JSON格式输出。包含多个句子。"
        result = await registry.execute("summarize", text=text, format="json")

        assert result.success is True
        data = json.loads(result.output)
        assert "summary" in data
        assert "sentence_count" in data
        assert "word_count" in data

    @pytest.mark.asyncio
    async def test_invalid_format(self, registry):
        """不支持的格式应通过参数校验报错。"""
        result = await registry.execute("summarize", text="test", format="excel")

        assert result.success is False
        assert "不支持的格式" in result.error

    @pytest.mark.asyncio
    async def test_max_length_truncation(self, registry):
        """超过 max_length 的总结应被截断。"""
        text = "。".join(f"这是第{i}个句子" for i in range(20))
        result = await registry.execute("summarize", text=text, max_length=50)

        assert result.success is True
        assert len(result.output) <= 60  # 允许少量超出（截止到句号）

    @pytest.mark.asyncio
    async def test_metadata_fields(self, registry):
        """metadata 应包含长度统计信息。"""
        text = "Hello World. This is a test. Goodbye."
        result = await registry.execute("summarize", text=text)

        assert result.success is True
        assert result.metadata["original_length"] == len(text)
        assert result.metadata["original_words"] >= 5
        assert result.metadata["sentence_count"] >= 3
        assert "summary_length" in result.metadata

    @pytest.mark.asyncio
    async def test_preserves_first_sentence(self, registry):
        """总结应保留首句。"""
        text = (
            "人工智能是计算机科学的重要分支。"
            "它涉及机器学习、深度学习等多个子领域。"
            "近年来，大型语言模型受到了广泛关注。"
            "这些模型在文本生成和自然语言理解方面表现优异。"
        )
        result = await registry.execute("summarize", text=text, max_length=500)

        assert result.success is True
        # 首句关键词应出现在总结中
        assert "人工智能" in result.output


# ---------------------------------------------------------------------------
# 未注册技能
# ---------------------------------------------------------------------------

class TestUnknownSkill:

    @pytest.mark.asyncio
    async def test_unknown_skill_error(self):
        """调用未注册的技能应返回错误。"""
        registry = SkillRegistry()
        result = await registry.execute("nonexistent_skill", text="test")

        assert result.success is False
        assert "未找到" in result.error


# ---------------------------------------------------------------------------
# SkillResult
# ---------------------------------------------------------------------------

class TestSkillResult:

    def test_default_values(self):
        r = SkillResult()
        assert r.success is True
        assert r.output == ""
        assert r.error == ""
        assert r.duration_ms == 0.0

    def test_error_result(self):
        r = SkillResult(success=False, error="something wrong")
        assert r.success is False
        assert r.error == "something wrong"
