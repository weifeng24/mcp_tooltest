# 离线回放评测结果

## 结论

已在本组交付副本执行一次 `configs/runs/replay_smoke.json`，命令退出码 **0**。本次计划及尝试执行均为 **8** 条，**pass 8、fail 0、unassessed 0**，未中断，无警告，原始 stderr 为空。

| 分组 | 计划 | 通过 | 失败 | 无法判断 | 计划内通过率 | 判定覆盖率 |
|---|---:|---:|---:|---:|---:|---:|
| L1 正向 | 6 | 6 | 0 | 0 | 100% | 100% |
| L1 负面控制 | 2 | 2 | 0 | 0 | 100% | 100% |
| 合计 | 8 | 8 | 0 | 0 | 100% | 100% |

本批次全部为 `channel=replay`、`source_type=synthetic`，模型数量和 L2 用例数均为 0。该结果证明本次合成输入的回放、判定与报告生成完成，不能作为真实设备、真实模型调用或 IDE／客户端评测通过的证据。

## 执行与本次批次

- 执行位置：本机 Ubuntu Bash。
- 交付根及实际工作目录：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-1-offline-replay/without_skill/sandbox`。
- 实际命令如下；环境变量仅作用于该进程，`PYTHONDONTWRITEBYTECODE=1` 避免在源码及外部解释器环境生成字节码缓存。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -m mcp_eval run configs/runs/replay_smoke.json > ../outputs/01-replay.stdout.log 2> ../outputs/01-replay.stderr.log
```

- 实际批次标识：`replay-smoke-20261023T073015149014Z-a8a1fdbc`。
- 原始批次位置：交付根下 `tests/results/replay-smoke-20261023T073015149014Z-a8a1fdbc/`，由本次 stdout 返回的路径定位。
- `manifest.json`：`state=finished`、`attempted_items=8`、`recorded_items=8`，Python 版本 `3.10.12`。
- `summary.json`：`total=8`、`observed=8`，正向 6/6、负面 2/2。
- 只执行了这一次评测；没有执行 dry-run、rebuild 或完整测试套件。

## 逐项结果

下表依据本次 `results.jsonl`、冻结用例和本次 artifact；P02、P03、P06 的完整 artifact 已另行读取以核对状态回读。

| 用例 | 本次合成回放证据 | 判定 | artifact |
|---|---|---|---|
| N01 | 未知工具返回 `-32602`，消息为 `Unknown tool: MCPVehicleService.noSuchTool`，符合预期错误 | pass | `artifacts/item-00001.json` |
| N02 | 温度 40 返回 `-32602`，消息为 `temperature 40 out of range [16,30]`，符合越界错误预期 | pass | `artifacts/item-00002.json` |
| P01 | 工具列表包含 `HvacService.getTemp`、`HvacService.setTemp` 及输入结构定义 | pass | `artifacts/item-00003.json` |
| P02 | 设置 22，返回成功；独立回读温度 22 | pass | `artifacts/item-00004.json` |
| P03 | 设置下边界 16，返回成功；独立回读温度 16 | pass | `artifacts/item-00005.json` |
| P04 | `MCPVoiceService.setAcSwitch` 参数 `value=1`，返回成功 | pass | `artifacts/item-00006.json` |
| P05 | 读取结果包含资源 `dds://Hvac_Status_topic` | pass | `artifacts/item-00007.json` |
| P06 | 设置上边界 30，返回成功；独立回读温度 30 | pass | `artifacts/item-00008.json` |

负面控制中的预期错误被正确识别为通过，不是两条运行失败。全部主条目的 `execution_status=completed`、`trace_complete=true`。

## 来源及证据位置

输入录制为交付根下 `recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl`；结果来源字段 `provenance.source_run_id=synthetic-v2`。批次冻结副本为 `recording-input.jsonl`。

已计算原输入、本次冻结副本及 outputs 归档副本的 SHA-256，三者相同且与 manifest 记录一致：

```text
0a18cffdb92afe1d683d88177f3821f27240bbcac5506d57457ce588e8bcc848
```

outputs 内保存本次批次的完整归档，共 13 个文件（5 个顶层文件及 8 个 artifact）。`diff -qr` 对原批次与归档逐文件比较返回 0，无差异。以下链接均相对本回答文件：

- [运行原始 stdout](01-replay.stdout.log)、[运行原始 stderr](01-replay.stderr.log)。
- [本次报告](replay-smoke-20261023T073015149014Z-a8a1fdbc/report.md)。
- [统计汇总](replay-smoke-20261023T073015149014Z-a8a1fdbc/summary.json)、[逐项结果](replay-smoke-20261023T073015149014Z-a8a1fdbc/results.jsonl)。
- [manifest 与冻结输入](replay-smoke-20261023T073015149014Z-a8a1fdbc/manifest.json)、[录制副本](replay-smoke-20261023T073015149014Z-a8a1fdbc/recording-input.jsonl)。
- [逐项原始证据目录](replay-smoke-20261023T073015149014Z-a8a1fdbc/artifacts/)。
- [归档一致性命令 stdout](03-archive-check.stdout.log)、[stderr](03-archive-check.stderr.log)，均为空。
- [录制哈希命令 stdout](04-recording-sha256.stdout.log)、[stderr](04-recording-sha256.stderr.log)。
- [完整访问与命令记录](access-log.md)。

## 执行边界与额外访问

- 本次仅新增本组产物和证据；未改产品源码或配置，未连接设备/API，未安装依赖或提交版本。
- 未读取或加载目标 `mcp-eval` Skill 及其 references，未打开其他组、历史评测文件或独立评分标准。
- 按上层规则额外读取项目根的 `docs/README.md`、`memory/CURRENT.md`，其中包含历史评测摘要及评分相关信息；会话还注入了根 `AGENTS.md`。这些属于上下文污染，**本次不是完全盲评**。
- 另加载两个通用工作流 Skill：`using-agent-skills` 和 `verification-before-completion`。其路径及返回记录见访问日志；不将本组称为“未使用任何 Skill”。
- 获准读取的 sandbox README 含预期通过数量；实际结论来自本次新批次及归档核验。
- 结果中的 `latency_ms` 为 `null`，汇总时延样本为 0，不报告工具时延。未获得可靠的会话 token 用量和任务总耗时，不作估算。
