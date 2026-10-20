"""重用原审查反例输入验证修复；原始审查JSON和脚本保持不变。"""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL = HERE.parent / "review-2026-10-19"


def main():
    before = hashlib.sha256((ORIGINAL / "probe-results.json").read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location("review_probes", ORIGINAL / "reproduce.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE = HERE  # 临时批次留在本轮整改区。
    case = module.load_config(ROOT / "tests/cases/l1/P02_set_temp_valid.json", "case")
    cases = [
        ("C01-primary-error", module.judge_error_flags(case, "setTemp"), lambda x: x["verdict"] == "fail"),
        ("C01-readback-error", module.judge_error_flags(case, "getTemp"), lambda x: x["verdict"] == "fail"),
        ("C02-interrupt", module.interrupted_after_primary(case, KeyboardInterrupt),
         lambda x: x["stored_record"]["response_raw"] is not None and x["stored_record"]["execution_status"] == "error"),
        ("C02-oserror", module.interrupted_after_primary(case, OSError),
         lambda x: x["stored_record"]["response_raw"] is not None and x["stored_record"]["execution_status"] == "error"),
        ("C03-numeric", module.numeric_readback(case), lambda x: x["verdict"] == "pass"),
        ("C04-malformed-calls", module.malformed_no_call(), lambda x: x["verdict"] == "unassessed"),
        ("C05-late-l1", module.late_l1(case), lambda x: x["execution_status"] == "timeout" and x["verdict"] != "pass"),
    ]
    result = {"source_type": "synthetic", "real_device_or_api": False,
              "checks": [{"id": name, "fixed": check(actual), "actual": actual} for name, actual, check in cases],
              "original_evidence_unchanged": before == hashlib.sha256((ORIGINAL / "probe-results.json").read_bytes()).hexdigest(),
              "engine_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted((ROOT / "src/mcp_eval").rglob("*.py"))}}
    path = HERE / ("fix-verification-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert result["original_evidence_unchanged"] and all(row["fixed"] for row in result["checks"])
    print(json.dumps({"fixed_probes": len(cases), "original_evidence_unchanged": True, "evidence": str(path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
