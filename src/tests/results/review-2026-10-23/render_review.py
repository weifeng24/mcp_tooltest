"""复用既有七节模板，以Skill官方渲染器生成报告并静态校验。"""
import ast
import difflib
import html
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / "review-2026-10-19"
DEST = ROOT / "docs/reviews/2026-10-23"
SKILL = Path.home() / ".config/opencode/skills/code-review"


def main():
    issues = json.loads((HERE / "findings.json").read_text())["issues"]
    details_html, details_md = [], []
    for issue in issues:
        compile(ast.parse("def suggested_fragment():\n" + textwrap.indent(issue["code_after"], "    ")),
                "<unapplied-review-fragment>", "exec")
        diff = "\n".join(difflib.unified_diff(issue["code_before"].splitlines(), issue["code_after"].splitlines(),
                                            fromfile="原代码摘录", tofile="修复建议（未应用）", lineterm=""))
        source = "../../../" + issue["file"].removeprefix("src/")
        title = issue["id"] + " · " + issue["check_item"]
        location = f"{issue['file']}:{issue['line']}"
        details_html.append('<div class="issue-item"><h3>' + html.escape(title) + '</h3><p><a href="'
                            + html.escape(source, quote=True) + '">' + html.escape(location) + '</a></p><p>'
                            + html.escape(issue["description"]) + '</p><pre class="code-block">'
                            + html.escape(diff) + '</pre><p>修复说明：' + html.escape(issue["fix_explain"]) + '</p></div>')
        details_md.append(f"### {title}\n\n- 位置：[{location}]({source})\n- 规则：{issue['rule_id']}\n"
                          f"- 严重等级：{issue['severity']}\n\n{issue['description']}\n\n"
                          f"**原代码／修复后（未应用）：**\n\n```diff\n{diff}\n```\n\n**修复说明：** {issue['fix_explain']}\n")
    template = (OLD / "report_template.html").read_text()
    heading = '<h2 class="section-title"><span class="num">§{}</span>'
    begin, end = template.index(heading.format(6)), template.index(heading.format(7))
    template = template[:begin] + heading.format(6) + "问题详情与修复方向</h2>\n" + "\n".join(details_html) + template[end:]
    template = template.replace("新增5项问题（P1三项、P2两项），7个离线反例复现。", "新增2项问题（P1一项、P2一项），4个离线反例复现；旧7项修复复核通过。")
    (HERE / "report_template.html").write_text(template)
    template_md = (OLD / "report_template.md").read_text()
    begin, end = template_md.index("## §6"), template_md.index("## §7")
    template_md = template_md[:begin] + "## §6 问题详情\n\n" + "\n".join(details_md) + template_md[end:]
    template_md = template_md.replace("新增5项问题（P1三项、P2两项）。", "新增2项问题（P1一项、P2一项），4个离线反例复现。")
    (HERE / "report_template.md").write_text(template_md)
    DEST.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-B", str(SKILL / "scripts/generate_report.py"),
                    "--findings", str(HERE / "findings.json"), "--metadata", str(HERE / "metadata.json"),
                    "--template-html", str(HERE / "report_template.html"), "--template-md", str(HERE / "report_template.md"),
                    "--output-html", str(DEST / "code-review.html"), "--output-md", str(DEST / "code-review.md")], check=True)
    report = (DEST / "code-review.html").read_text()
    assert re.findall(r'<h2 class="section-title"><span class="num">§(\d)</span>', report) == list("1234567")
    assert "{{" not in report and all(issue["id"] in report for issue in issues)
    check = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/self_check.py"), str(DEST / "code-review.html")],
                           capture_output=True, text=True)
    (HERE / "report-self-check.txt").write_text(check.stdout + check.stderr)
    print(check.stdout)
    check.check_returncode()


if __name__ == "__main__":
    main()
