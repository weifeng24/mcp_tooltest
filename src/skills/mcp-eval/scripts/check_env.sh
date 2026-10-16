#!/usr/bin/env bash
# mcp-eval 环境检查：确认评测运行所需条件，不打印密钥内容。
# 用法：在交付区根目录执行 bash skills/mcp-eval/scripts/check_env.sh
set -u
ok=0

check() {  # $1=名称 $2=通过条件（0 为通过）$3=失败提示
  if [ "$2" -eq 0 ]; then
    echo "[OK]   $1"
  else
    echo "[FAIL] $1 —— $3"
    ok=1
  fi
}

python3 --version >/dev/null 2>&1
check "Python3 可用" $? "需要 Python >= 3.10"

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null
check "Python >= 3.10" $? "当前版本过低"

python3 -c "import jsonschema, pytest" >/dev/null 2>&1
check "依赖 jsonschema/pytest" $? "pip install -r requirements.txt"

[ -f "src/mcp_eval/runner.py" ]
check "位于交付区根目录" $? "请 cd 到交付区 src/ 再执行（应能看到 src/mcp_eval/）"

if command -v adb >/dev/null 2>&1; then
  echo "[OK]   adb 可用（$(adb version | head -1)）"
else
  echo "[WARN] adb 不可用 —— 仅真机模式需要，回放模式可忽略"
fi

for var in DEEPSEEK_API_KEY KIMI_API_KEY; do
  if [ -n "${!var:-}" ]; then
    echo "[OK]   $var 已设置（值不显示）"
  else
    echo "[WARN] $var 未设置 —— 仅 L2 模型批次需要：export $var=<你的key>"
  fi
done

if [ "$ok" -eq 0 ]; then
  echo "环境就绪：可运行回放冒烟 PYTHONPATH=src python3 -m mcp_eval run configs/runs/replay_smoke.json"
else
  echo "存在未通过项，按上述提示处理后再运行"
fi
exit $ok
