"""核对本地材料、已有软件验证快照与新增演示证据，保存独立检查结果。"""
import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href", "src") and value:
                self.links.append(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "tests/results/local-completion-2026-10-23" / f"checks-{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    commands = {}
    python = ROOT / "tests/results/remediation-2026-10-16/.venv/bin/python"

    def check_command(label, argv, expected=0, env=None):
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=120, env=env)
        (out / f"{label}.stdout.txt").write_text(proc.stdout, encoding="utf-8")
        (out / f"{label}.stderr.txt").write_text(proc.stderr, encoding="utf-8")
        commands[label] = {"argv": list(map(str, argv)), "returncode": proc.returncode, "expected": expected}
        assert proc.returncode == expected, label
        return proc.stdout

    creator = Path.home() / ".config/opencode/anthropic-skills/skills/skill-creator"
    check_command("creator-structure", [sys.executable, "-B", str(creator / "scripts/quick_validate.py"), "skills/mcp-eval"])
    check_command("skill-help", ["bash", "skills/mcp-eval/scripts/check_env.sh", "--help"])
    check_command("skill-env", ["bash", "skills/mcp-eval/scripts/check_env.sh"], env={**os.environ, "MCP_EVAL_PYTHON": str(python)})
    check_command("trigger-help", [sys.executable, "-B", "scripts/check_skill_trigger.py", "--help"])
    trigger = json.loads(check_command("trigger-env", [sys.executable, "-B", "scripts/check_skill_trigger.py"], expected=2))
    assert not trigger["trigger_evaluation_executed"] and trigger["status"] == "blocked_missing_claude_cli"
    check_command("git-diff-check", ["git", "diff", "--check"])

    current = {str(p.relative_to(ROOT / "src/mcp_eval")): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((ROOT / "src/mcp_eval").rglob("*.py"))}
    old = load(ROOT / "tests/results/remediation-2026-10-23/verification-20261023T065124607189Z/verification.json")
    assert current == load(Path(old["smoke"]["manifest"]))["engine_sources"]
    demo = load(ROOT / "docs/defense/demo-session.json")
    assert current == demo["verification"]["engine_sha256"]
    assert demo["verification"]["smoke"] == {"pass": 8, "fail": 0, "unassessed": 0}
    assert demo["verification"]["negative"] == {"pass": 0, "fail": 1, "unassessed": 0}
    assert demo["verification"]["rebuild_identical"]
    browser_file = ROOT / "tests/results/local-completion-2026-10-23/browser-20261023T084549173782Z/verification.json"
    browser = load(browser_file)
    assert browser["status"] == "passed" and not browser["page_errors"] and browser["video_seconds"] > 30
    assert all("file:///api/feedback" in error for error in browser["console_errors"])
    original_template = ROOT.parent / "docs/2026-TS-Force-AI实战演练-校招生答辩模板.html"
    assert hashlib.sha256(original_template.read_bytes()).hexdigest() == load(ROOT / "docs/defense/build-metadata.json")["company_template_sha256"]
    iteration = ROOT / "skills/mcp-eval-workspace/iteration-6"
    skill_hashes = load(iteration / "skill-hashes.json")
    assert all(hashlib.sha256((ROOT / "skills/mcp-eval" / name).read_bytes()).hexdigest() == digest for name, digest in skill_hashes.items())
    scores = load(iteration / "benchmark.json")["runs"]
    assert len(scores) == 14
    totals = {mode: sum(row["result"]["passed"] for row in scores if row["configuration"] == mode)
              for mode in ("with_skill", "without_skill")}
    assert totals == {"with_skill": 35, "without_skill": 32}
    load(ROOT / "docs/comparison-records-template.json")
    for path in [ROOT / "scripts" / name for name in ("check_skill_trigger.py", "prepare_local_demo.py", "build_defense.py", "check_defense.py", "verify_local_materials.py")]:
        ast.parse(path.read_text(encoding="utf-8"))
    files = [ROOT / name for name in ("README.md", "midterm.md", "tasks/todo.md", "tasks/local-completion-2026-10-23.md",
              "docs/report.md", "docs/defense-outline.md", "docs/defense-template-analysis.md", "docs/effect-comparison-plan.md",
              "docs/training-and-business-inputs.md", "docs/defense/README.md", "docs/defense/speaker-notes.md",
              "skills-creator/fix-log.md", "skills/mcp-eval-workspace/trigger-readiness.md",
              "skills/mcp-eval-workspace/iteration-6/README.md", "skills/mcp-eval-workspace/iteration-6/benchmark.md")]
    files += [ROOT.parent / name for name in ("docs/README.md", "memory/CURRENT.md", "memory/DECISIONS.md")]
    broken, count = [], 0

    def check_links(path, targets):
        nonlocal count
        for target in targets:
            target = target.strip().strip("<>")
            if urlparse(target).scheme or target.startswith("#"):
                continue
            count += 1
            if not (path.parent / unquote(target.split("#", 1)[0])).resolve().exists():
                broken.append({"file": str(path.relative_to(ROOT.parent)), "target": target})

    for path in files:
        check_links(path, re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")))
    for name in ("index.html", "offline-demo.html"):
        path = ROOT / "docs/defense" / name
        html = Links()
        html.feed(path.read_text(encoding="utf-8"))
        check_links(path, html.links)
    result = {"commands": commands, "product_matches_184_test_snapshot": True, "product_matches_demo_snapshot": True,
              "software_tests_rerun_this_step": False, "skill_scores": totals, "skill_snapshot_unchanged": True,
              "company_template_unchanged": True, "demo": demo["verification"], "browser_evidence": str(browser_file.relative_to(ROOT)),
              "trigger_status": trigger["status"], "markdown_files_checked": len(files), "local_links_checked": count,
              "broken_links": broken, "status": "passed" if not broken else "failed"}
    (out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"evidence": str(out.relative_to(ROOT)), "status": result["status"], "local_links": count, "broken_links": broken}, ensure_ascii=False, indent=2))
    assert not broken


if __name__ == "__main__":
    main()
