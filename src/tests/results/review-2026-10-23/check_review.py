"""检查本轮审查快照一致性、报告结构和交接链接。"""
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
    evidence = json.loads((HERE / "probe-results.json").read_text())
    current = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in sorted((ROOT / "src/mcp_eval").rglob("*.py"))}
    assert evidence["engine_sha256"] == current
    verification = json.loads((HERE / "verification-20261023T063209736713Z/verification.json").read_text())
    manifest = json.loads(Path(verification["smoke"]["manifest"]).read_text())
    assert {"src/mcp_eval/" + k: v for k, v in manifest["engine_sources"].items()} == current
    assert verification["status"] == "passed" and verification["rebuild_identical"]
    assert verification["smoke"]["counts"] == {"pass": 8, "fail": 0, "unassessed": 0}
    old = json.loads((HERE / "fix-verification-20261023T063427862457Z.json").read_text())
    assert len(old["checks"]) == 7 and all(row["fixed"] for row in old["checks"])
    assert old["original_evidence_unchanged"]
    probes = evidence["probes"]
    assert probes["C01-L2-nonfinite"]["dispatched"] == 1 and probes["C01-L2-nonfinite"]["argument_is_nan"]
    assert probes["C01-L1-nonfinite"]["config_accepted"]
    for key in ("C02-deadline-decision", "C02-length-decision"):
        assert probes[key]["observed_decisions"] == 1 and probes[key]["judged_calls"] == 0
        assert probes[key]["verdict"] == "unassessed" and probes[key]["dispatched"] == 0
    report_dir = ROOT / "docs/reviews/2026-10-23"
    report = (report_dir / "code-review.html").read_text()
    assert re.findall(r'<h2 class="section-title"><span class="num">§(\d)</span>', report) == list("1234567")
    assert all(f"P{level}" in report for level in range(4)) and "CL 评分 +1" not in report
    scores = re.search(r'var\s+dimScores\s*=\s*(\[[^\]]+\])', report)
    assert scores and len(json.loads(scores[1])) == 9
    assert all(len(re.findall(r"<td\b", row)) == 7 for row in re.findall(r'<tr class="issue-row".*?</tr>', report, re.S))
    files = [WORKSPACE / "docs/README.md", WORKSPACE / "memory/CURRENT.md", WORKSPACE / "memory/DECISIONS.md",
             ROOT / "README.md", ROOT / "tasks/todo.md", HERE / "verification.md", *report_dir.glob("*.md")]
    broken, count = [], 0
    for path in files:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            target = target.strip().strip("<>")
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            count += 1
            if not (path.parent / unquote(target.split("#", 1)[0])).resolve().exists():
                broken.append({"file": str(path.relative_to(WORKSPACE)), "target": target})
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    engine = subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", "src/mcp_eval"], cwd=ROOT, capture_output=True, text=True)
    result = {"engine_matches_head": engine.returncode == 0, "regression_and_probe_same_engine": True,
              "old_fixed_probes": 7, "new_probes": 4, "findings": 2, "report_sections": 7,
              "markdown_files_checked": len(files), "local_links_checked": count, "broken_links": broken,
              "git_diff_check_returncode": diff.returncode}
    (HERE / "review-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert not broken and diff.returncode == 0 and engine.returncode == 0


if __name__ == "__main__":
    main()
