"""命令行入口：python3 -m mcp_eval <command>。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .device import build_test_config
from .runner import on_device_checklist, run_evaluation

DELIVERY_ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcp_eval", description="车载 MCP 工具评测：运行评测、生成车机配置、上机清单"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="按 run 配置执行评测")
    p_run.add_argument("run_config", help="run 配置路径（相对交付区根目录）")
    p_run.add_argument("--dry-run", action="store_true", help="只校验与展示计划，不执行")

    p_gen = sub.add_parser("gen-config", help="由单条用例生成车机 test_config JSON")
    p_gen.add_argument("case_file", help="用例 JSON 路径（相对交付区根目录）")

    sub.add_parser("checklist", help="输出上机日检查清单")

    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            outcome = run_evaluation(args.run_config, DELIVERY_ROOT, dry_run=args.dry_run)
            print(json.dumps(outcome, ensure_ascii=False, indent=2))
        elif args.command == "gen-config":
            case = load_config(DELIVERY_ROOT / args.case_file, "case")
            print(json.dumps(build_test_config(case), ensure_ascii=False, indent=2))
        elif args.command == "checklist":
            server = load_config(DELIVERY_ROOT / "configs/servers/ark_mcp_service.json", "server")
            print(on_device_checklist(server))
    except (ConfigError, FileNotFoundError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
