"""Collect local evidence; never launch a model, device, test suite, or subagent."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path.cwd().resolve()
WORK = ROOT / "skills/mcp-eval-workspace/iteration-3"
REPO = ROOT.parent
CREATOR = Path("/home/tssh/.config/opencode/anthropic-skills/skills/skill-creator")
PYTHON = ROOT / "tests/results/remediation-2026-10-16/.venv/bin/python"
ENV = dict(os.environ, PYTHONPATH="src", PYTHONDONTWRITEBYTECODE="1",
           PATH=str(PYTHON.parent) + os.pathsep + os.environ.get("PATH", ""))


def save(relative, value):
    path = (WORK / relative).resolve()
    assert path.is_relative_to(WORK)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Evidence is append-only: a rerun must not replace earlier observations.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def command(name, argv, allowed=(0,)):
    result = subprocess.run(argv, cwd=ROOT, env=ENV, capture_output=True, text=True)
    event = {"argv": argv, "cwd": str(ROOT), "environment_overrides": {
        k: ENV[k] for k in ("PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "PATH")},
        "command": shlex.join(argv), "exit_code": result.returncode,
        "stdout": result.stdout, "stderr": result.stderr}
    save(f"logs/{name}.json", event)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    if result.returncode not in allowed:
        raise RuntimeError(f"Unexpected exit code for {name}: {result.returncode}")
    return result


def outside_inventory():
    listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                            cwd=REPO, capture_output=True, check=True).stdout
    output = {}
    for raw in listed.split(b"\0"):
        if not raw:
            continue
        relative = os.fsdecode(raw)
        path = REPO / relative
        if path.is_relative_to(WORK) or not path.is_file():
            continue
        output[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return output


def prepare():
    save("context/outside-before.json", outside_inventory())
    command("git-head", ["git", "rev-parse", "HEAD"])
    command("git-status-before", ["git", "status", "--short"])
    probe = command("claude-availability", ["bash", "-c", "command -v claude"], (0, 1))
    command("python-version", [str(PYTHON), "--version"])
    command("package-versions", [str(PYTHON), "-c",
            "import importlib.metadata,json; print(json.dumps({p:importlib.metadata.version(p) for p in ['jsonschema','pytest']}))"])
    public = ["README.md", "configs/runs/replay_smoke.json", "configs/servers/ark_mcp_service.json",
              "configs/runs/l2_device.json", "docs/device-readiness.md",
              "tests/cases/l1/N02_param_out_of_range.json", "requirements.txt"]
    skill = ["skills/mcp-eval/SKILL.md", "skills/mcp-eval/evals/evals.json",
             "skills/mcp-eval/references/report-guide.md", "skills/mcp-eval/references/troubleshooting.md"]
    constraints = ["AGENTS.md", "docs/README.md", "memory/CURRENT.md", "memory/DECISIONS.md",
                   "docs/AI实战演练框架v1.2-截图整理.md"]
    helpers = ["SKILL.md", "agents/grader.md", "agents/analyzer.md", "references/schemas.md",
               "scripts/aggregate_benchmark.py", "eval-viewer/generate_review.py", "eval-viewer/viewer.html"]
    snapshots = {}
    for base, files, label in ((ROOT, public + skill, "project"), (REPO, constraints, "constraints"),
                                (CREATOR, helpers, "skill-creator")):
        for relative in files:
            path = base / relative
            raw = path.read_bytes()
            snapshots[f"{label}/{relative}"] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                                                "content": raw.decode("utf-8")}
    save("context/input-snapshots.json", snapshots)
    # Read the specified worksheet row directly without office application caches.
    book = REPO / "docs/2026TS-force AI实战演练选题申报表_郑炜峰.xlsx"
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(book) as archive:
        strings = ["".join(n.itertext()) for n in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("s:si", ns)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(s for s in workbook.find("s:sheets", ns) if s.attrib["name"] == "维度说明")
        rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        rel = next(r for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels")) if r.attrib["Id"] == rid)
        target = rel.attrib["Target"].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        row = ET.fromstring(archive.read(target)).find("s:sheetData/s:row[@r='2']", ns)
        cells = {}
        for cell in row:
            value = cell.find("s:v", ns)
            cells[cell.attrib["r"]] = (strings[int(value.text)] if cell.attrib.get("t") == "s" else value.text) if value is not None else "".join(cell.itertext())
    save("context/topic-row.json", {"path": str(book), "sheet": "维度说明", "row": 2,
                                     "sha256": hashlib.sha256(book.read_bytes()).hexdigest(), "cells": cells})
    save("context/execution-context.json", {
        "created_at": datetime.now(timezone.utc).isoformat(), "cwd": str(ROOT),
        "model": "openai/gpt-6-astra", "harness": "OpenCode API session",
        "available_tools": ["apply_patch", "bash", "glob", "grep", "read", "skill", "webfetch", "multi_tool_use.parallel"],
        "subagent_interface_available": False, "independent_contexts_started": 0,
        "mode": "main_context_with_skill_sanity_only", "baseline": "without_skill (not old_skill)",
        "baseline_status": "not_run", "baseline_isolation_established": False,
        "claude_available": probe.returncode == 0, "claude_lookup_stdout": probe.stdout,
        "user_reported_latest_facts": ["C01-C05已修复", "完整回归160passed", "8合成回放通过", "7原反例修复验证通过"],
        "latest_facts_reverified_here": False,
        "constraints": ["writes only within iteration-3", "no pytest", "no devices or model APIs", "no commit/push", "no memory or product edits"],
        "baseline_required_policy": "Only task prompt and necessary public README/configs; prohibit all skills/, skills-creator/, historical comparison outputs, iteration workspace and neighbouring outputs. Own output writes are the sole workspace exception.",
        "fallback_contamination": "Main context has project rules, memory, all four prompts, expectations, Skill and references; unsuitable for a no-Skill baseline. No baseline answers are generated.",
        "transcript_limitation": "No raw subagent notification or export interface. Harness Read results remain in session; input-snapshots preserve source bytes, not a fabricated transcript. Subprocess return codes/stdout/stderr preserved verbatim in logs.",
        "timing": {"total_tokens": None, "duration_ms": None, "total_duration_seconds": None}})


def preflight():
    command("check-env-help", ["bash", "skills/mcp-eval/scripts/check_env.sh", "--help"])
    command("check-env", ["bash", "skills/mcp-eval/scripts/check_env.sh"])
    command("cli-help", [str(PYTHON), "-m", "mcp_eval", "--help"])
    command("run-help", [str(PYTHON), "-m", "mcp_eval", "run", "--help"])


def replay():
    cfg = json.loads((ROOT / "configs/runs/replay_smoke.json").read_text())
    cfg["run_id"] = "skill-iteration3-" + uuid.uuid4().hex
    cfg["output_dir"] = "skills/mcp-eval-workspace/iteration-3/evidence/replay"
    save("inputs/replay.json", cfg)
    path = "skills/mcp-eval-workspace/iteration-3/inputs/replay.json"
    command("replay-dry-run", [str(PYTHON), "-m", "mcp_eval", "run", path, "--dry-run"])
    command("replay-run", [str(PYTHON), "-m", "mcp_eval", "run", path])


def integrity():
    before = json.loads((WORK / "context/outside-before.json").read_text())
    after = outside_inventory()
    save("context/outside-after.json", after)
    result = {"changed": sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
              "added": sorted(after.keys() - before.keys()), "removed": sorted(before.keys() - after.keys()),
              "scope": "git tracked + untracked nonignored files outside iteration-3; ignored environment/cache files not comprehensively monitored"}
    save("context/write-boundary-check.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert not any(result[k] for k in ("changed", "added", "removed"))


if __name__ == "__main__":
    assert (ROOT / "src/mcp_eval").is_dir(), "Run explicitly from delivery root"
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "preflight", "replay", "integrity"])
    {"prepare": prepare, "preflight": preflight, "replay": replay, "integrity": integrity}[parser.parse_args().phase]()
