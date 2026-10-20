"""复用前次七节模板及官方渲染器生成当前报告，不修改历史报告。"""
from __future__ import annotations

import ast
import difflib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / "review-2026-10-16"
DEST = ROOT / "docs/reviews/2026-10-19"
SKILL = Path.home() / ".config/opencode/skills/code-review"


def main():
    issues = json.loads((HERE / "findings.json").read_text(encoding="utf-8"))["issues"]
    detail_html, detail_md = [], []
    for issue in issues:
        compile(ast.parse(issue["code_after"]), "<unapplied-review-fragment>", "exec")
        difference = "\n".join(difflib.unified_diff(
            issue["code_before"].splitlines(), issue["code_after"].splitlines(),
            fromfile="原代码摘录", tofile="修复方向（未应用）", lineterm=""))
        source = "../../../" + issue["file"].removeprefix("src/")
        title = f"{issue['id']} · {issue['check_item']}"
        location = f"{issue['file']}:{issue['line']}"
        priority = "P1" if issue["severity"] == "major" else "P2"
        detail_html.append(
            '<div class="issue-item"><h3>' + html.escape(title) + '</h3><p><a href="'
            + html.escape(source, quote=True) + '">' + html.escape(location) + '</a></p><p>'
            + html.escape(f"{priority}；规则{issue['rule_id']}；{issue['description']}")
            + '</p><pre class="code-block">' + html.escape(difference)
            + '</pre><p>修复说明：' + html.escape(issue["fix_explain"]) + '</p></div>')
        detail_md.append(
            f"### {title}\n\n- 位置：[{location}]({source})\n- 规则：{issue['rule_id']}\n"
            f"- 严重等级：{issue['severity']} / {priority}\n\n{issue['description']}\n\n"
            f"**原代码／修复后设计示意（未应用）：**\n\n```diff\n{difference}\n```\n\n"
            f"**修复说明：** {issue['fix_explain']}\n")

    template = (OLD / "report_template.html").read_text(encoding="utf-8")
    heading = '<h2 class="section-title"><span class="num">§{}</span>'
    begin, end = template.index(heading.format(6)), template.index(heading.format(7))
    template = template[:begin] + heading.format(6) + "问题详情与修复方向</h2>\n" + "\n".join(detail_html) + template[end:]
    template = template.replace("存在 P0 阻塞。", "新增5项问题（P1三项、P2两项），7个离线反例复现。")
    template = template.replace("模板评分不是公司演练评分或验收结论。", "模板评分仅按已检出项扣分，不代表覆盖率、合入批准、公司评分或验收。")
    template = template.replace("{{CL_LABEL}}", "不适用；本地复审结论为Request changes")
    template = template.replace("待入口核实后分解，不按问题数估算", "尚未估时；先修判定与证据，再核对真机")
    # 图例明确P级别，保留官方图表和九维度数据结构。
    template = template.replace("['Critical', 'Major', 'Minor', 'Q/Praise']", "['P0 Critical', 'P1 Major', 'P2 Minor', 'P3 Question']")
    (HERE / "report_template.html").write_text(template, encoding="utf-8")

    md = (OLD / "report_template.md").read_text(encoding="utf-8")
    begin, end = md.index("## §6"), md.index("## §7")
    md = md[:begin] + "## §6 问题详情\n\n" + "\n".join(detail_md) + md[end:]
    md = md.replace("存在 P0 阻塞。模板分数不是演练成绩。", "新增5项问题（P1三项、P2两项）。模板分数不代表合入批准或演练成绩。")
    md = md.replace("{{CL_LABEL}}", "不适用；本地复审结论为Request changes")
    md = md.replace("工时待车端入口确认后评估。", "工时尚未评估；优先修复判定和证据缺陷，再核对真机。")
    (HERE / "report_template.md").write_text(md, encoding="utf-8")
    DEST.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        sys.executable, "-B", str(SKILL / "scripts/generate_report.py"),
        "--findings", str(HERE / "findings.json"), "--metadata", str(HERE / "metadata.json"),
        "--template-html", str(HERE / "report_template.html"), "--template-md", str(HERE / "report_template.md"),
        "--output-html", str(DEST / "code-review.html"), "--output-md", str(DEST / "code-review.md"),
    ], check=True)
    report = (DEST / "code-review.html").read_text(encoding="utf-8")
    assert re.findall(r'<h2 class="section-title"><span class="num">§(\d)</span>', report) == list("1234567")
    assert "{{" not in report
    assert all(issue["id"] in report for issue in issues)
    check = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/self_check.py"),
                            str(DEST / "code-review.html")], capture_output=True, text=True)
    (HERE / "report-self-check.txt").write_text(check.stdout + check.stderr, encoding="utf-8")
    print(check.stdout)
    check.check_returncode()
    print("七节完整；修复片段仅通过Python语法检查，未应用或集成验证。")


if __name__ == "__main__":
    main()
