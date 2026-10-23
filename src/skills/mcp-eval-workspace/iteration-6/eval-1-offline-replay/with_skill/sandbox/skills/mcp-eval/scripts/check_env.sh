#!/usr/bin/env bash
# 检查本机离线依赖；不读取凭据值、不连接设备或模型。
set -u
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "用法：在交付根目录执行 bash skills/mcp-eval/scripts/check_env.sh"
  echo "可用 MCP_EVAL_PYTHON 指定解释器路径，例如 .venv/bin/python。"
  echo "仅检查本机环境；密钥只检查是否设置，不打印值。此脚本不证明设备或API可用。"
  exit 0
fi
if [ "$#" -ne 0 ]; then
  echo "未知参数，请先使用 --help" >&2
  exit 2
fi
PYTHON="${MCP_EVAL_PYTHON:-python3}"
failed=0
if "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  echo "[OK] Python >= 3.10"
else
  echo "[FAIL] Python >= 3.10 不可用"
  failed=1
fi
if "$PYTHON" -c 'import jsonschema, pytest' >/dev/null 2>&1; then
  echo "[OK] jsonschema / pytest 可导入"
else
  echo "[FAIL] 依赖未就绪，按 README 安装到项目虚拟环境"
  failed=1
fi
if [ -f src/mcp_eval/runner.py ] && [ -f requirements.txt ]; then
  echo "[OK] 当前目录为交付根目录"
else
  echo "[FAIL] 请进入交付根目录（应有 src/mcp_eval/ 与 requirements.txt）"
  failed=1
fi
if command -v adb >/dev/null 2>&1; then
  echo "[OK] adb 命令存在；未验证设备连接和版本"
else
  echo "[WARN] adb 不存在，仅真机模式需要"
fi
for var in DEEPSEEK_API_KEY KIMI_API_KEY; do
  if [ -n "${!var:-}" ]; then
    echo "[INFO] $var 已设置（未验证权益，值不显示）"
  else
    echo "[INFO] $var 未设置（离线回放不需要）"
  fi
done
if [ "$failed" -eq 0 ]; then
  echo "离线基础环境检查通过；设备、工具绑定、模型和完整发现能力仍需分别验证。"
fi
exit "$failed"
