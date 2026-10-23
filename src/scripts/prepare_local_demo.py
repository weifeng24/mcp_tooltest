"""在独立副本执行合成回放、负面发现和报告重建，保存展示用真实命令输出。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "tests/results/local-completion-2026-10-23" / f"demo-{stamp}"
    runtime = out / "runtime"
    runtime.mkdir(parents=True, exist_ok=False)
    for name in ("src/mcp_eval", "configs", "tests/cases", "recordings"):
        shutil.copytree(ROOT / name, runtime / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "requirements.txt", runtime / "requirements.txt")
    env = {**os.environ, "PYTHONPATH": str(runtime / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    steps = []

    def run(title, args, expected=0):
        argv = [sys.executable, "-B", "-m", "mcp_eval", *args]
        start = time.monotonic()
        proc = subprocess.run(argv, cwd=runtime, env=env, capture_output=True, text=True, timeout=60)
        prefix = f"step-{len(steps) + 1:02d}"
        (out / f"{prefix}.stdout.txt").write_text(proc.stdout, encoding="utf-8")
        (out / f"{prefix}.stderr.txt").write_text(proc.stderr, encoding="utf-8")
        step = {"title": title, "argv": argv, "display_command": "PYTHONPATH=src python3 -m mcp_eval " + " ".join(args),
                "cwd": str(runtime), "returncode": proc.returncode, "subprocess_seconds": time.monotonic() - start,
                "stdout_path": str((out / f"{prefix}.stdout.txt").relative_to(ROOT)),
                "stderr_path": str((out / f"{prefix}.stderr.txt").relative_to(ROOT)),
                "stdout": proc.stdout, "stderr": proc.stderr}
        steps.append(step)
        save(out / "commands.json", steps)
        assert proc.returncode == expected, (title, proc.returncode, proc.stderr)
        return proc.stdout

    run("1 · 查看真实命令帮助", ["--help"])
    dry = json.loads(run("2 · 本地预检，执行数为零", ["run", "configs/runs/replay_smoke.json", "--dry-run"]))
    assert dry["executed"] == 0 and dry["plan"]["total_planned"] == 8
    steps[-1]["display_output"] = json.dumps({"planned": 8, "executed": 0, "device_verified": dry["device_verified"]}, ensure_ascii=False, indent=2)
    smoke = json.loads(run("3 · 实际运行合成回放", ["run", "configs/runs/replay_smoke.json"]))
    assert smoke["counts"] == {"pass": 8, "fail": 0, "unassessed": 0}
    steps[-1]["display_output"] = json.dumps({"run_id": smoke["run_id"], "counts": smoke["counts"], "source_type": "synthetic",
                                              "report": str(Path(smoke["report"]).relative_to(runtime))}, ensure_ascii=False, indent=2)
    rows = [json.loads(line) for line in (runtime / "recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl").read_text().splitlines() if line.strip()]
    changed = 0
    for row in rows:
        if row["case_id"] == "N02":
            row["response_raw"] = {"jsonrpc": "2.0", "id": 1, "result": {"isError": False, "success": True}}
            row["verdict"], row["verdict_reason"] = None, None
            row.setdefault("provenance", {})["demo_fixture"] = "synthetic_success_for_invalid_input"
            changed += 1
    assert changed == 1
    recording = runtime / "recordings/DEMO_SYNTHETIC_NEGATIVE.jsonl"
    recording.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    run_config = json.loads((runtime / "configs/runs/replay_smoke.json").read_text())
    run_config.update(run_id="demo-negative", case_glob="tests/cases/l1/N02_param_out_of_range.json", recording="recordings/DEMO_SYNTHETIC_NEGATIVE.jsonl")
    save(runtime / "configs/runs/demo-negative.json", run_config)
    negative = json.loads(run("4 · 越界返回成功，评测应发现失败", ["run", "configs/runs/demo-negative.json"], expected=1))
    assert negative["counts"] == {"pass": 0, "fail": 1, "unassessed": 0}
    steps[-1]["display_output"] = json.dumps({"counts": negative["counts"], "returncode": 1,
                                             "source_type": "synthetic", "reason": "预期错误未出现；保留fail，不改预期"}, ensure_ascii=False, indent=2)
    summary_path = Path(smoke["summary"])
    before = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    run("5 · 从冻结输入重建报告", ["rebuild", str(Path(smoke["manifest"]).parent.relative_to(runtime))])
    identical = before == hashlib.sha256(summary_path.read_bytes()).hexdigest()
    assert identical
    steps[-1]["display_output"] = json.dumps({"summary_sha256_unchanged": identical, "device_calls": 0, "model_requests": 0,
                                             "note": "重建读取既有结果，不重新执行工具"}, ensure_ascii=False, indent=2)
    save(out / "commands.json", steps)
    verification = {"status": "passed", "source_type": "synthetic", "smoke": smoke["counts"], "negative": negative["counts"],
                    "rebuild_identical": identical, "independent_copy": True, "fresh_dependency_install": False,
                    "runtime": str(runtime.relative_to(ROOT)), "smoke_report": str(Path(smoke["report"]).relative_to(ROOT)),
                    "negative_report": str(Path(negative["report"]).relative_to(ROOT)),
                    "engine_sha256": {str(p.relative_to(ROOT / "src/mcp_eval")): hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in sorted((ROOT / "src/mcp_eval").rglob("*.py"))}}
    save(out / "verification.json", verification)
    save(ROOT / "docs/defense/demo-session.json", {"recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "synthetic", "presentation_mode": "已执行命令记录回看，非实时终端、非车机验证",
        "evidence": str(out.relative_to(ROOT)), "verification": verification, "steps": steps})
    print(json.dumps({"evidence": str(out.relative_to(ROOT)), "status": "passed", "demo": "docs/defense/demo-session.json"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
