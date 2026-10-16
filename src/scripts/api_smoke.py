#!/usr/bin/env python3
"""模型 API 冒烟脚本：验证密钥、模型名与工具调用格式是否可用。

用法（在交付区根目录 src/ 下）：
    export DEEPSEEK_API_KEY=<你的key>
    PYTHONPATH=src python3 ../scripts/api_smoke.py configs/models/deepseek.json

模型决策走真实 API；工具执行是本地 mock（永远成功），不连接车机。
预期：模型对 M01 任务选择 setTemp 类工具并给出参数 22。
"""
from __future__ import annotations

import sys
from pathlib import Path

DELIVERY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DELIVERY_ROOT / "src"))

from mcp_eval.config import load_config  # noqa: E402
from mcp_eval.judge import judge_record  # noqa: E402
from mcp_eval.model_loop import ModelLoop  # noqa: E402
from mcp_eval.providers import create_provider  # noqa: E402

TOOLS = [
    {
        "name": "16777217.setTemp",
        "description": "设置空调温度",
        "inputSchema": {
            "type": "object",
            "properties": {"temperature": {"type": "integer", "minimum": 16, "maximum": 30}},
            "required": ["temperature"],
        },
    },
    {
        "name": "16777217.getTemp",
        "description": "获取空调当前设置的温度",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


class MockExecutor:
    channel = "replay"

    def __call__(self, name: str, arguments: dict) -> dict:
        return {"content": [{"type": "text", "text": "ok"}], "success": True}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    model_cfg = load_config(DELIVERY_ROOT / sys.argv[1], "model")
    case = load_config(DELIVERY_ROOT / "tests/cases/l2/M01_set_temp_task.json", "case")
    provider = create_provider(model_cfg)
    loop = ModelLoop(provider, MockExecutor(), TOOLS, max_rounds=3)
    record = loop.run_case(case, "api-smoke", model_cfg["model_config_id"], timeout_seconds=90)
    judge_record(case, record)
    print(f"execution_status: {record.execution_status}")
    print(f"error_category:   {record.error_category}")
    print(f"stopped_reason:   {record.response_raw.get('stopped_reason')}")
    print(f"tool_calls:       {[(c['name'], c['arguments']) for c in record.response_raw['tool_calls']]}")
    print(f"final_answer:     {record.response_raw.get('final_answer')}")
    print(f"usage:            {record.response_raw.get('usage')}")
    print(f"verdict:          {record.verdict} ({record.verdict_reason})")
    return 0 if record.execution_status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
