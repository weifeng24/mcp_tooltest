"""最终证据一致性、独立运行副本和文档链接检查；不访问设备/API。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORKSPACE = ROOT.parent


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((ROOT / "src/mcp_eval").rglob("*.py"))}
    fixed = json.loads((HERE / "fix-verification-20261019T102528075419Z.json").read_text())
    verified = json.loads((HERE / "verification-20261019T102527934113Z/verification.json").read_text())
    manifest = json.loads(Path(verified["smoke"]["manifest"]).read_text())
    assert source_hashes == fixed["engine_sha256"]
    assert source_hashes == {"src/mcp_eval/" + k: v for k, v in manifest["engine_sources"].items()}
    suite = ET.parse(HERE / "verification-20261019T102527934113Z/pytest.xml").getroot().find("testsuite")
    assert suite.get("tests") == "160" and all(suite.get(key) == "0" for key in ("failures", "errors", "skipped"))

    standalone = HERE / ("standalone-" + stamp)
    standalone.mkdir()
    for folder in ("src/mcp_eval", "configs", "recordings", "tests/cases"):
        shutil.copytree(ROOT / folder, standalone / folder)
    for name in ("README.md", "requirements.txt"):
        shutil.copyfile(ROOT / name, standalone / name)
    env = {**os.environ, "PYTHONPATH": str(standalone / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    commands = []

    def run(args):
        command = [sys.executable, "-B", "-m", "mcp_eval", *args]
        result = subprocess.run(command, cwd=standalone, env=env, text=True, capture_output=True, timeout=60)
        commands.append({"argv": command, "cwd": str(standalone), "returncode": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    run(["run", "configs/runs/replay_smoke.json", "--dry-run"])
    replay = run(["run", "configs/runs/replay_smoke.json"])
    assert replay["counts"] == {"pass": 8, "fail": 0, "unassessed": 0}
    before = hashlib.sha256(Path(replay["summary"]).read_bytes()).hexdigest()
    run(["rebuild", str(Path(replay["manifest"]).parent.relative_to(standalone))])
    assert before == hashlib.sha256(Path(replay["summary"]).read_bytes()).hexdigest()
    assert not (standalone / "memory").exists()

    paths = ["README.md", "midterm.md", "docs/design.md", "docs/remediation.md", "docs/remediation-2026-10-19.md",
             "docs/report.md", "docs/device-readiness.md", "docs/case-freeze.md", "docs/defense-outline.md",
             "tasks/todo.md", "tasks/plan.md", "tasks/remediation-2026-10-19.md", "skills-creator/fix-log.md",
             "skills/mcp-eval/SKILL.md", "skills/mcp-eval/references/troubleshooting.md",
             "skills/mcp-eval-workspace/iteration-4/README.md", "skills/mcp-eval-workspace/iteration-5/README.md",
             "tests/results/remediation-2026-10-19/README.md"]
    files = [ROOT / name for name in paths] + [WORKSPACE / name for name in ("docs/README.md", "memory/CURRENT.md", "memory/DECISIONS.md")]
    broken, links = [], 0
    for file in files:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", file.read_text()):
            target = target.strip().strip("<>")
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            links += 1
            if not (file.parent / unquote(target.split("#", 1)[0])).exists():
                broken.append({"file": str(file.relative_to(WORKSPACE)), "target": target})
    for iteration, groups in ((4, ("with_skill", "without_skill")), (5, ("with_skill", "old_skill"))):
        text = (ROOT / f"skills/mcp-eval-workspace/iteration-{iteration}/review.html").read_text()
        assert all(group in text for group in groups), "复核页面缺少一组输出"
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, text=True, capture_output=True)
    result = {"date": datetime.now(timezone.utc).isoformat(), "product_source_matches_160_tests": True,
              "product_source_matches_7_fixed_probes": True, "standalone_counts": replay["counts"],
              "standalone_rebuild_identical": True, "standalone_has_no_memory": True,
              "standalone_scope": "最小离线运行副本，复用现有依赖解释器；不是正式交付包或重新安装验证",
              "standalone_directory": str(standalone.relative_to(ROOT)), "commands": commands,
              "markdown_files": len(files), "local_links": links, "broken_links": broken,
              "skill_viewers_contain_both_groups": True, "git_diff_check_returncode": diff.returncode,
              "git_diff_check_output": diff.stdout + diff.stderr}
    output = HERE / ("final-check-" + stamp + ".json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "commands"}, ensure_ascii=False, indent=2))
    print(str(output))
    assert not broken and diff.returncode == 0


if __name__ == "__main__":
    main()
