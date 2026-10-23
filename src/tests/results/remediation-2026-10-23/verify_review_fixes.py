"""重用10-23审查反例输入验证修复；原始审查probe-results.json保持不变。"""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from mcp_eval.config import ConfigError

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL = HERE.parent / "review-2026-10-23"


def main():
    before = hashlib.sha256((ORIGINAL / "probe-results.json").read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location("review_2026_10_23_probes", ORIGINAL / "reproduce.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    l2 = module.nonfinite_dispatch()
    try:
        module.nonfinite_l1()
        l1 = {"config_rejected": False}
    except (ConfigError, ValueError):
        l1 = {"config_rejected": True}
    deadline = module.lost_decision("deadline")
    length = module.lost_decision("length")

    checks = [
        ("C01-L2-nonfinite", l2["arguments_parse_error"] is not None
         and l2["validation_errors"] >= 1 and l2["dispatched"] == 0, l2),
        ("C01-L1-nonfinite", l1["config_rejected"], l1),
        ("C02-deadline-decision", deadline["verdict"] == "fail" and deadline["dispatched"] == 0
         and deadline["observed_decisions"] == 1, {k: v for k, v in deadline.items() if k != "record"}),
        ("C02-length-decision", length["verdict"] == "fail" and length["dispatched"] == 0
         and length["observed_decisions"] == 1, {k: v for k, v in length.items() if k != "record"}),
    ]
    result = {"source_type": "synthetic", "real_device_or_api": False,
              "checks": [{"id": name, "fixed": ok, "actual": actual} for name, ok, actual in checks],
              "original_evidence_unchanged":
                  before == hashlib.sha256((ORIGINAL / "probe-results.json").read_bytes()).hexdigest(),
              "engine_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted((ROOT / "src/mcp_eval").rglob("*.py"))}}
    path = HERE / ("fix-verification-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    assert result["original_evidence_unchanged"] and all(row["fixed"] for row in result["checks"])
    print(json.dumps({"fixed_probes": len(checks), "original_evidence_unchanged": True,
                      "evidence": str(path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
