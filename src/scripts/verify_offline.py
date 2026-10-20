"""在当前解释器下运行测试及无设备/无API的 CLI 验证，保存独立证据目录。"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-parent", default="tests/results/remediation-2026-10-16",
                        help="证据父目录，必须位于交付区内；每次建立唯一子目录")
    args = parser.parse_args()
    parent = (ROOT / args.output_parent).resolve()
    if not parent.is_relative_to(ROOT):
        parser.error("证据输出目录必须位于交付区内")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = parent / f"verification-{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    commands = {}

    def run(label, args):
        proc = subprocess.run([sys.executable, "-B", *args], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=120)
        (out / f"{label}.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        commands[label] = {"args": args, "returncode": proc.returncode}
        if proc.returncode:
            raise RuntimeError(f"{label} 未通过，查看 {out / (label + '.txt')}")
        return proc.stdout

    result = {"python": sys.version, "prefix": sys.prefix, "base_prefix": sys.base_prefix,
              "isolated_venv": sys.prefix != sys.base_prefix,
              "dependencies": {distribution.metadata["Name"]: distribution.version
                               for distribution in importlib.metadata.distributions()}, "commands": commands}
    try:
        run("pytest", ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--junitxml", str(out / "pytest.xml")])
        run("help", ["-m", "mcp_eval", "--help"])
        run("dry-run", ["-m", "mcp_eval", "run", "configs/runs/replay_smoke.json", "--dry-run"])
        run("show-call", ["-m", "mcp_eval", "show-call", "tests/cases/l1/P02_set_temp_valid.json"])
        run("checklist", ["-m", "mcp_eval", "checklist"])
        run("catalog-plan", ["-m", "mcp_eval", "capture-catalog", "configs/servers/ark_mcp_service.json",
                             "--service", "MCPVehicleService", "--dry-run"])
        outcome = json.loads(run("smoke", ["-m", "mcp_eval", "run", "configs/runs/replay_smoke.json"]))
        before = hashlib.sha256(Path(outcome["summary"]).read_bytes()).hexdigest()
        run("rebuild", ["-m", "mcp_eval", "rebuild", str(Path(outcome["manifest"]).parent.relative_to(ROOT))])
        result["rebuild_identical"] = before == hashlib.sha256(Path(outcome["summary"]).read_bytes()).hexdigest()
        result["smoke"] = outcome
        assert result["rebuild_identical"] and outcome["counts"] == {"pass": 8, "fail": 0, "unassessed": 0}
        result["status"] = "passed"
    finally:
        (out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evidence": str(out), "status": result["status"], "isolated": result["isolated_venv"],
                      "counts": outcome["counts"], "report": outcome["report"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
