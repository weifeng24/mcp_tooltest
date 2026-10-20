# 场景1：离线回放结果

执行性质：读取当前 Skill 后在主上下文完成的检查，非独立子代理运行，不构成与 without_skill 的对照。

## 实际执行

在交付根目录使用 `tests/results/remediation-2026-10-16/.venv/bin/python`，设置 `PYTHONPATH=src`、`PYTHONDONTWRITEBYTECODE=1`。先执行环境脚本帮助、环境检查、CLI 帮助和 run 帮助，再执行本轮配置的 `--dry-run` 与正式回放。预检显示计划8项、执行0项、`device_verified=false`；回放退出码0。原始命令、stdout、stderr、退出码均在日志中。〔1〕〔2〕

本轮配置复制自 `configs/runs/replay_smoke.json`，只改变 `run_id` 和 `output_dir`，写入本轮工作区，未覆盖原配置。没有执行 pytest、设备命令、模型API或历史批次重建。

## 实际批次与数量

- 实际 `run_id`：`skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4`。
- 批次目录（相对交付根目录）：`skills/mcp-eval-workspace/iteration-3/evidence/replay/skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4/`。
- 已读取该目录的 `manifest.json`、`results.jsonl`、`summary.json` 和 `report.md`。〔3〕〔4〕〔5〕〔6〕

| 计划项 | 通过 | 失败 | unassessed | 未执行 |
|---:|---:|---:|---:|---:|
| 8 | 8 | 0 | 0 | 0 |

分母N=8来自 manifest 的全部 `planned_items`，并非仅统计成功结果。6条正向P01—P06、2条负面N01—N02均有对应结果；模型为null，`repeat_index=0`。计划内通过率8/8，判定覆盖率8/8。〔3〕〔4〕〔5〕

## 来源与边界

8条结果的 `channel=replay`、`source_type=synthetic`，来源录制为 `recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl`，`source_run_id=synthetic-v2`。manifest记录其SHA-256为 `0a18cffdb92afe1d683d88177f3821f27240bbcac5506d57457ce588e8bcc848`。这验证本次合成回放，不证明真机、真实模型、IDE或自动触发通过，也不代表导师验收。〔3〕〔4〕

本轮没有重新执行160项完整回归或7个原反例；相关完成事实来自用户最新说明。项目README和memory中的旧状态未作为本次实测结论。本次没有代理token或耗时返回，相关指标保持null，不能用回放内部时延替代代理耗时。

## 引用

以下路径均相对交付根目录。

- 〔1〕 `skills/mcp-eval-workspace/iteration-3/logs/replay-dry-run.json`：预检原始返回。
- 〔2〕 `skills/mcp-eval-workspace/iteration-3/logs/replay-run.json`：正式回放原始返回。
- 〔3〕 `skills/mcp-eval-workspace/iteration-3/evidence/replay/skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4/manifest.json`：计划、输入与哈希。
- 〔4〕 `skills/mcp-eval-workspace/iteration-3/evidence/replay/skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4/results.jsonl`：8项实际判定与来源。
- 〔5〕 `skills/mcp-eval-workspace/iteration-3/evidence/replay/skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4/summary.json`：数量与统计口径。
- 〔6〕 `skills/mcp-eval-workspace/iteration-3/evidence/replay/skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4/report.md`：逐项报告。
