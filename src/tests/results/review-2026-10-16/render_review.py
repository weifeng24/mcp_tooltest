"""使用 Code Review 官方渲染器及原模板生成七节审查报告。

仅适配原模板的章节布局并补充问题 diff，不修改业务代码或全局 Skill。
"""
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
SKILL = Path.home() / ".config/opencode/skills/code-review"
DEST = ROOT / "docs/reviews/2026-10-16"


def main():
    findings = json.loads((HERE / "findings.json").read_text(encoding="utf-8"))
    issues = findings["issues"]
    for issue in issues:
        compile(ast.parse(issue["code_after"]), "<review-design-fragment>", "exec")

    template = (SKILL / "assets/report_template.html").read_text(encoding="utf-8")
    markers = [template.index(f"<!-- §{i}") for i in range(1, 6)]
    footer = template.index('<div class="footer">')
    closing = template.rfind("</div>", markers[4], footer)
    prefix = template[:markers[0]]
    summary_start = template.index('<div class="summary">', markers[0])
    section1 = template[markers[0]:summary_start].replace("执行摘要", "项目概览")
    notice = (
        '<p><strong>审查结论：Request changes。</strong>存在 P0 阻塞。'
        '模板评分不是公司演练评分或验收结论。修复后代码均为未应用的设计片段，'
        '只做了语法核对，不代表完整补丁已验证。'
        '<a href="requirements-review.md">任务与设计对照审查</a></p>'
    )
    section1 += notice
    section2 = template[summary_start:markers[2]].replace("数据可视化", "总体评分与雷达图")
    pie = re.search(r'  <div class="chart-box"><h3>问题严重等级分布</h3>.*?</div>', section2).group(0)
    section2 = section2.replace(pie, "")
    section3 = template[markers[2]:markers[3]]
    section3 += '<p>N/A：维度二无多线程共享锁模型；维度八不涉及 AIDL/Binder 实现，adb 子进程契约在维度四检查。雷达图 N/A 的零位仅作显示，不计入评分。</p>'
    heading = '<h2 class="section-title"><span class="num">§{number}</span>{title}</h2>\n'
    section4 = heading.format(number=4, title="严重等级分布") + '<div class="charts">' + pie + '</div>\n'
    section5 = template[markers[3]:markers[4]].replace("§4", "§5")
    details_html = []
    details_md = []
    for issue in issues:
        before, after = issue["code_before"], issue["code_after"]
        difference = "\n".join(difflib.unified_diff(before.splitlines(), after.splitlines(),
                                                     fromfile="原代码摘录", tofile="修复设计示意（未应用）", lineterm=""))
        source = "../../../" + issue["file"].removeprefix("src/")
        title = f"{issue['id']} · {issue['check_item']}"
        location = f"{issue['file']}:{issue['line']}"
        details_html.append(
            '<div class="issue-item"><h3>' + html.escape(title) + '</h3><p><a href="'
            + html.escape(source, quote=True) + '">' + html.escape(location) + '</a></p><p>'
            + html.escape(issue["description"]) + '</p><pre class="code-block">'
            + html.escape(difference) + '</pre><p>修复说明：' + html.escape(issue["fix_explain"]) + '</p></div>'
        )
        details_md.append(
            f"### {title}\n\n- 位置：[{location}]({source})\n- 规则：{issue['rule_id']}\n"
            f"- 严重等级：{issue['severity']}\n\n{issue['description']}\n\n"
            f"**原代码／修复后设计示意（未应用）：**\n\n```diff\n{difference}\n```\n\n"
            f"**修复说明：** {issue['fix_explain']}\n"
        )
    section6 = heading.format(number=6, title="问题详情与修复方向") + "\n".join(details_html)
    section7 = template[markers[4]:closing].replace("§5", "§7")
    for priority in ("CRITICAL", "MAJOR", "MINOR"):
        section7 = section7.replace("{{ETA_" + priority + "}}", "待入口核实后分解，不按问题数估算")
    section2 = section2.replace('<h2 class="section-title"><span class="num">§2</span>总体评分与雷达图</h2>', '')
    final_template = prefix + section1 + heading.format(number=2, title="总体评分与雷达图") + section2
    final_template += section3 + section4 + section5 + section6 + section7 + template[closing:]
    (HERE / "report_template.html").write_text(final_template, encoding="utf-8")

    base_md = (SKILL / "assets/report_template.md").read_text(encoding="utf-8")
    intro = base_md.split("## §2")[0]
    intro = intro.replace("## §1 执行摘要", "## §1 项目概览")
    intro = intro.replace("**综合评分:", "## §2 总体评分\n\n**综合评分:")
    intro += "\n**Request changes：存在 P0 阻塞。模板分数不是演练成绩。** 修复片段未应用，仅核对语法。需求与验收覆盖见 [主审查报告](requirements-review.md)。\n"
    markdown = intro + "\n## §3 各维度评分\n\n{{DIMENSION_TABLE_MD}}\n\n"
    markdown += "维度二、八为 N/A：无共享锁模型，不实现 Android AIDL/Binder；adb 调用契约另查。\n"
    markdown += "\n## §4 严重等级分布\n\nP0={{COUNT_CRITICAL}}；P1={{COUNT_MAJOR}}；P2={{COUNT_MINOR}}；P3={{COUNT_QUESTION}}。图表见 HTML。\n"
    markdown += "\n## §5 问题汇总\n\n| # | 严重 | 规则 | 维度 | 检查项 | 位置 | 修复建议 |\n|---|---|---|---|---|---|---|\n{{ISSUE_TABLE_MD}}\n"
    markdown += "\n## §6 问题详情\n\n" + "\n".join(details_md)
    markdown += "\n## §7 整改顺序\n\n### P0\n{{ROADMAP_CRITICAL_MD}}\n\n### P1\n{{ROADMAP_MAJOR_MD}}\n\n### P2\n{{ROADMAP_MINOR_MD}}\n\n工时待车端入口确认后评估。修复后重跑反例及回归，当前没有问题已被修复的结论。\n"
    (HERE / "report_template.md").write_text(markdown, encoding="utf-8")
    proc = subprocess.run([
        sys.executable, str(SKILL / "scripts/generate_report.py"),
        "--findings", str(HERE / "findings.json"), "--metadata", str(HERE / "metadata.json"),
        "--template-html", str(HERE / "report_template.html"),
        "--template-md", str(HERE / "report_template.md"),
        "--output-html", str(DEST / "code-review.html"),
        "--output-md", str(DEST / "code-review.md")], check=True, capture_output=True, text=True)
    print(proc.stdout)
    rendered = (DEST / "code-review.html").read_text(encoding="utf-8")
    sections = re.findall(r'<h2 class="section-title"><span class="num">§(\d)</span>', rendered)
    assert sections == list("1234567"), sections
    assert "{{" not in rendered
    print("Seven sections and all suggested Python fragments verified.")


if __name__ == "__main__":
    main()
