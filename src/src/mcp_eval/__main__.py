"""命令行入口：python3 -m mcp_eval <command>。"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .device import build_test_config, command_for_case
from .runner import on_device_checklist, run_evaluation, local_path
from .report import write_report
from .catalog import capture_catalog, catalog_plan

DELIVERY_ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcp_eval", description="车载 MCP 评测：独立批次、离线回放、报告重建与上机预检"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="按 run 配置执行评测")
    p_run.add_argument("run_config", help="run 配置路径（相对交付区根目录）")
    p_run.add_argument("--dry-run", action="store_true", help="只校验与展示计划，不执行")

    p_gen = sub.add_parser("gen-config", help="历史配置格式参考（不由当前设备通道消费）")
    p_gen.add_argument("case_file", help="用例 JSON 路径（相对交付区根目录）")

    sub.add_parser("checklist", help="输出上机日检查清单")
    p_show = sub.add_parser("show-call", help="显示单工具调用 argv，不连接设备")
    p_show.add_argument("case_file")
    p_rebuild = sub.add_parser("rebuild", help="依据批次 manifest 重建报告，不执行工具或模型")
    p_rebuild.add_argument("batch_dir")
    p_capture = sub.add_parser("capture-catalog", help="只读采集已有注册定义dump，不执行工具或实时tools/list")
    p_capture.add_argument("server_config")
    p_capture.add_argument("--service", action="append", help="只采集明确选择的服务，可重复；默认server中的服务清单")
    p_capture.add_argument("--timeout", type=float, default=120, help="整次文件采集的总等待预算（秒）")
    p_capture.add_argument("--dry-run", action="store_true", help="仅显示文件读取计划，不运行adb")

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            outcome = run_evaluation(args.run_config, DELIVERY_ROOT, dry_run=args.dry_run)
            print(json.dumps(outcome, ensure_ascii=False, indent=2))
            if outcome.get("interrupted"):
                return 130
            counts = outcome.get("counts", {})
            return 1 if counts.get("fail") or counts.get("unassessed") else 0
        elif args.command == "gen-config":
            case = load_config(DELIVERY_ROOT / args.case_file, "case")
            print("仅为历史格式参考，不会被当前 device 通道自动加载。", file=sys.stderr)
            print(json.dumps(build_test_config(case), ensure_ascii=False, indent=2))
        elif args.command == "show-call":
            case = load_config(local_path(DELIVERY_ROOT, args.case_file), "case")
            server = load_config(DELIVERY_ROOT / "configs/servers/ark_mcp_service.json", "server")
            print(json.dumps({"argv": command_for_case(case, server.get("service_bin", "mcp_service")),
                              "device_verified": False}, ensure_ascii=False, indent=2))
        elif args.command == "rebuild":
            batch = local_path(DELIVERY_ROOT, args.batch_dir)
            manifest = json.loads((batch / "manifest.json").read_text(encoding="utf-8"))
            cases = {case["case_id"]: case for case in manifest["inputs"]["cases"]}
            summary, report = write_report(batch / "results.jsonl", cases, batch,
                                           manifest["run_id"], manifest["planned_items"])
            print(json.dumps({"summary": str(summary), "report": str(report)}, ensure_ascii=False))
        elif args.command == "capture-catalog":
            if not math.isfinite(args.timeout) or args.timeout <= 0:
                raise ConfigError("timeout必须为有限正数")
            server = load_config(local_path(DELIVERY_ROOT, args.server_config), "server")
            if args.dry_run:
                print(json.dumps({"files": catalog_plan(server, args.service), "executed": 0,
                                  "device_configured": bool(server["device_serial"]),
                                  "runtime_tools_list_tested": False}, ensure_ascii=False, indent=2))
            else:
                outcome = capture_catalog(server, DELIVERY_ROOT, services=args.service, timeout=args.timeout)
                print(json.dumps(outcome, ensure_ascii=False, indent=2))
                return 130 if outcome["interrupted"] else 0 if outcome["catalog_status"] == "complete" else 1
        elif args.command == "checklist":
            server = load_config(DELIVERY_ROOT / "configs/servers/ark_mcp_service.json", "server")
            print(on_device_checklist(server))
    except (ConfigError, OSError, ValueError, KeyError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
