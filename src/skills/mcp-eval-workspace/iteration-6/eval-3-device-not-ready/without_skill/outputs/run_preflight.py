"""Run only local preflight commands and preserve their unmodified byte output."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys


OUTPUT = Path(__file__).resolve().parent
SANDBOX = OUTPUT.parent / "sandbox"
PYTHON = "/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python"
COMMANDS = [
    ("01-help", 0, ["--help"]),
    ("02-checklist", 0, ["checklist"]),
    ("03-l1-device-dry-run", 2, ["run", "configs/runs/l1_device.json", "--dry-run"]),
    ("04-l2-device-dry-run", 2, ["run", "configs/runs/l2_device.json", "--dry-run"]),
    ("05-replay-dry-run", 0, ["run", "configs/runs/replay_smoke.json", "--dry-run"]),
    ("06-show-call-p02", 0, ["show-call", "tests/cases/l1/P02_set_temp_valid.json"]),
    ("07-catalog-dry-run", 0, ["capture-catalog", "configs/servers/ark_mcp_service.json", "--dry-run"]),
    ("08-show-call-p01", 2, ["show-call", "tests/cases/l1/P01_tools_list.json"]),
    ("09-show-call-p05", 2, ["show-call", "tests/cases/l1/P05_resources_read.json"]),
]


def snapshot():
    paths = {
        SANDBOX / "README.md",
        SANDBOX / "docs/catalog-capture.md",
        SANDBOX / "docs/device-readiness.md",
        SANDBOX / "recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl",
    }
    for directory, pattern in (("src/mcp_eval", "*.py"), ("configs", "*.json"), ("tests/cases", "*.json")):
        paths.update((SANDBOX / directory).rglob(pattern))
    result = {}
    for path in sorted(paths):
        if not path.resolve().is_relative_to(SANDBOX.resolve()):
            raise RuntimeError(f"Input resolves outside this sandbox: {path}")
        result[str(path.relative_to(SANDBOX))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def save_json(name, data):
    (OUTPUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    if Path.cwd().resolve() != SANDBOX.resolve():
        raise RuntimeError("Run this script with this group's sandbox as the working directory")
    if sys.executable != PYTHON:
        raise RuntimeError(f"Unexpected interpreter: {sys.executable}")
    before = snapshot()
    save_json("checked-inputs-before.json", before)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH="src")
    results = []
    for name, expected_code, arguments in COMMANDS:
        argv = [PYTHON, "-B", "-m", "mcp_eval", *arguments]
        completed = subprocess.run(argv, cwd=SANDBOX, env=env, capture_output=True, timeout=60)
        (OUTPUT / f"{name}.stdout.txt").write_bytes(completed.stdout)
        (OUTPUT / f"{name}.stderr.txt").write_bytes(completed.stderr)
        (OUTPUT / f"{name}.exitcode.txt").write_text(str(completed.returncode) + "\n", encoding="utf-8")
        result = {"name": name, "argv": argv, "command": shlex.join(argv), "cwd": str(SANDBOX),
                  "environment_overrides": {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "src"},
                  "returncode": completed.returncode, "expected_returncode": expected_code,
                  "stdout": f"{name}.stdout.txt", "stderr": f"{name}.stderr.txt"}
        results.append(result)
        save_json("commands.json", results)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        sys.stdout.buffer.write(completed.stdout)
        sys.stdout.buffer.write(completed.stderr)
        sys.stdout.flush()
    after = snapshot()
    save_json("checked-inputs-after.json", after)
    verification = {
        "checked_input_count": len(before),
        "checked_inputs_unchanged": before == after,
        "changed_checked_inputs": sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key)),
        "expected_exit_codes_observed": all(item["returncode"] == item["expected_returncode"] for item in results),
        "commands_completed": len(results),
        "real_device_cases_executed": 0,
        "model_api_calls": 0,
        "synthetic_replay_executed_this_run": False,
        "token_usage": None,
        "elapsed_seconds": None,
    }
    save_json("preflight-verification.json", verification)
    print(json.dumps(verification, ensure_ascii=False, indent=2))
    return 0 if before == after and verification["expected_exit_codes_observed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
