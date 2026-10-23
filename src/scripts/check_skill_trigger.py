"""检查真实Skill自动触发评测的本机前置条件；默认不调用模型。"""
import argparse
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    queries = json.loads((ROOT / "skills/mcp-eval-workspace/trigger-eval-20.json").read_text())
    assert len(queries) == 20 and all(type(q["should_trigger"]) is bool and q["query"] for q in queries)
    cli = shutil.which("claude")
    creator = Path.home() / ".config/opencode/anthropic-skills/skills/skill-creator"
    result = {"queries": len(queries), "positive": sum(q["should_trigger"] for q in queries),
              "negative": sum(not q["should_trigger"] for q in queries), "claude_cli": cli,
              "yaml_available": importlib.util.find_spec("yaml") is not None,
              "official_runner_exists": (creator / "scripts/run_eval.py").is_file(),
              "authentication": "not_checked", "trigger_evaluation_executed": False,
              "status": "cli_present_authentication_unverified" if cli else "blocked_missing_claude_cli"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if cli else 2


if __name__ == "__main__":
    raise SystemExit(main())
