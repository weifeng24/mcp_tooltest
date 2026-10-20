# 场景1访问记录

执行者为主会话，模式为 `main_context_fallback_nonindependent`。未启动子代理，没有独立会话ID；主上下文已经包含所有场景、expectations、根规则与旧memory。此日志记录实际访问，不主张上下文隔离。

## 实际读取

- 项目 `skills/mcp-eval/SKILL.md`、`references/report-guide.md`、`references/troubleshooting.md`。
- 项目 `README.md`、`configs/runs/replay_smoke.json`、`configs/servers/ark_mcp_service.json`。
- 本次CLI返回的新批次 `manifest.json`（分两段完整读取）、`results.jsonl`（Read对长行有截断，原文件完整保留）、`summary.json`、`report.md`。
- 执行时CLI自动读取8条 `tests/cases/l1/*.json`、录制 `recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl`、项目schema与源码模块；manifest保存输入与引擎哈希。没有人工通读产品实现。
- 共享上下文和管理侧读取清单见 `context/access-boundary.md`；原始输入快照见 `context/input-snapshots.json`。这些不是独立代理输入证明。

## 实际命令

cwd均为 `/home/tssh/文档/Works/mission/校招生ai演练任务/src`。由 `scripts/collect_evidence.py preflight` 与 `replay` 依次执行；精确argv、环境覆盖、退出码与原始返回分别在下列日志中：

1. `logs/check-env-help.json`：`bash skills/mcp-eval/scripts/check_env.sh --help`。
2. `logs/check-env.json`：`bash skills/mcp-eval/scripts/check_env.sh`，仅检测环境和命令可用性。
3. `logs/cli-help.json`：指定解释器 `-m mcp_eval --help`。
4. `logs/run-help.json`：指定解释器 `-m mcp_eval run --help`。
5. `logs/replay-dry-run.json`：指定解释器 `-m mcp_eval run skills/mcp-eval-workspace/iteration-3/inputs/replay.json --dry-run`。
6. `logs/replay-run.json`：相同配置正式回放，无 `--dry-run`。

以上子进程均设置 `PYTHONPATH=src`、`PYTHONDONTWRITEBYTECODE=1`，PATH首项为指定venv的bin。pytest仅被环境脚本导入检查，未运行测试集。无rebuild、设备/API调用。

## 实际写入

- 管理脚本生成本轮 `inputs/replay.json`、命令日志及 `evidence/replay/` 下唯一新批次。原始结果未编辑。
- 本场景文字输出仅 `outputs/answer.md` 与本文件，均用apply_patch首次写入，未从历史代理答案复制。
- 评分、timing、上下文和总报告由管理侧保存，不能当作代理返回。
