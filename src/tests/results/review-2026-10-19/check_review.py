"""验证本轮评审证据、报告结构和受影响文档链接。"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORKSPACE = ROOT.parent


def main():
    evidence = json.loads((HERE / "probe-results.json").read_text(encoding="utf-8"))
    current = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((ROOT / "src/mcp_eval").rglob("*.py"))}
    assert current == evidence["engine_sha256"], "审查后产品源码已变化，须复核结论"
    verification = json.loads((ROOT / "tests/results/remediation-2026-10-16/verification-20261019T084803765223Z/verification.json").read_text())
    manifest = json.loads(Path(verification["smoke"]["manifest"]).read_text())
    assert {"src/mcp_eval/" + key: value for key, value in manifest["engine_sources"].items()} == current
    assert evidence["reproduced"] == 7 and len(evidence["probes"]) == 7
    assert verification["status"] == "passed" and verification["rebuild_identical"]
    findings = json.loads((HERE / "findings.json").read_text())
    assert len(findings["issues"]) == 5
    report_dir = ROOT / "docs/reviews/2026-10-19"
    report = (report_dir / "code-review.html").read_text(encoding="utf-8")
    assert re.findall(r'<h2 class="section-title"><span class="num">§(\d)</span>', report) == list("1234567")
    assert all(f"P{level}" in report for level in range(4))
    assert "CL 评分 +1" not in report
    files = [WORKSPACE / "docs/README.md", WORKSPACE / "memory/CURRENT.md", WORKSPACE / "memory/DECISIONS.md",
             ROOT / "README.md", ROOT / "docs/design.md", ROOT / "docs/remediation.md", ROOT / "tasks/todo.md",
             ROOT / "midterm.md", HERE / "verification.md", *report_dir.glob("*.md")]
    broken, count = [], 0
    for path in files:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.strip().strip("<>")
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            local = unquote(target.split("#", 1)[0])
            count += 1
            resolved = (path.parent / local).resolve()
            if resolved != HERE / "review-checks.json" and not resolved.exists():
                broken.append({"file": str(path.relative_to(WORKSPACE)), "target": target})
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, text=True, capture_output=True)
    result = {"engine_unchanged": True, "regression_and_probe_same_engine": True,
              "review_sections": 7, "findings": 5, "reproduced_probes": 7,
              "markdown_files_checked": len(files), "local_links_checked": count, "broken_links": broken,
              "git_diff_check_returncode": diff.returncode, "git_diff_check_output": diff.stdout + diff.stderr}
    (HERE / "review-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert not broken and diff.returncode == 0


if __name__ == "__main__":
    main()
