"""
内置技能：代码审查
"""
import re
from app.skill_manager import Skill, SkillResult


class CodeReviewSkill(Skill):
    name = "code_review"
    description = "审查代码质量、安全性和最佳实践"
    version = "1.0.0"
    requires_llm = False

    # 常见问题模式
    PATTERNS = {
        "danger": [
            (r"eval\s*\(", "使用 eval() 可能有安全风险"),
            (r"exec\s*\(", "使用 exec() 可能有安全风险"),
            (r"os\.system\s*\(", "使用 os.system() 可能存在命令注入风险"),
            (r"subprocess\.call.*shell=True", "shell=True 存在命令注入风险"),
            (r"pickle\.loads?", "反序列化不可信数据存在安全风险"),
            (r"sqlite3\.execute\s*\(\s*f['\"]", "SQL 拼接可能存在注入风险"),
            (r"debug\s*=\s*True", "生产环境不应开启 debug 模式"),
        ],
        "warning": [
            (r"print\s*\(", "考虑使用 logger 替代 print"),
            (r"except\s*:", "裸 except 会捕获所有异常，建议指定异常类型"),
            (r"raise\s+Exception", "宜使用更具体的异常类型"),
            (r"\bpass\b", "存在空的 pass 语句，可能未完成实现"),
            (r"global\s+\w+", "尽量少用全局变量"),
            (r"import\s+\*", "通配符导入可能导致命名冲突"),
            (r"\btodo\b", "存在 TODO 标记"),
        ],
        "info": [
            (r"#\s*(xxx|fixme)", "存在待处理的标记"),
            (r"len\(.*\)\s*[=!]=\s*0", "可用 if container: 替代长度检查"),
            (r"type\(.*\)\s*[=!]=\s*\w+", "建议使用 isinstance()"),
        ],
    }

    def validate_params(self, code: str = "", file_path: str = "", **kwargs) -> str | None:
        if not code and not file_path:
            return "code 或 file_path 至少需要提供一个"
        return None

    async def execute(self, code: str = "", file_path: str = "", language: str = "", **kwargs) -> SkillResult:
        if file_path and not code:
            try:
                with open(file_path, encoding="utf-8") as f:
                    code = f.read()
            except Exception as e:
                return SkillResult(success=False, error=f"读取文件失败: {e}")

        if not code.strip():
            return SkillResult(success=False, error="代码内容为空")

        findings = []
        lines = code.split("\n")

        for severity, patterns in self.PATTERNS.items():
            for pattern, msg in patterns:
                for match in re.finditer(pattern, code, re.IGNORECASE):
                    # 计算行号
                    line_no = code[:match.start()].count("\n") + 1
                    findings.append({
                        "severity": severity,
                        "line": line_no,
                        "message": msg,
                        "match": match.group().strip()[:60],
                    })

        line_count = len(lines)
        summary = {
            "total_lines": line_count,
            "danger_count": sum(1 for f in findings if f["severity"] == "danger"),
            "warning_count": sum(1 for f in findings if f["severity"] == "warning"),
            "info_count": sum(1 for f in findings if f["severity"] == "info"),
        }

        output = (
            f"## 代码审查结果\n"
            f"- 文件: {file_path or '直接输入'}\n"
            f"- 语言: {language or '自动检测'}\n"
            f"- 总行数: {line_count}\n"
            f"- 严重问题: {summary['danger_count']} | 警告: {summary['warning_count']} | 提示: {summary['info_count']}\n\n"
        )

        if findings:
            output += "### 发现的问题\n\n"
            for f in sorted(findings, key=lambda x: ({"danger": 0, "warning": 1, "info": 2}[x["severity"]], x["line"])):
                label = {"danger": "🔴", "warning": "🟡", "info": "🔵"}.get(f["severity"], "⚪")
                output += f"- {label} 第 {f['line']} 行: {f['message']} (`{f['match']}`)\n"
        else:
            output += "✅ 未发现明显问题。\n"

        return SkillResult(output=output, metadata={"summary": summary, "findings": findings})
