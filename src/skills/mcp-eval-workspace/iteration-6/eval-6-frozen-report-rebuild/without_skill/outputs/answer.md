# 冻结批次报告重建结果

## 结论与产物

已在本组 `sandbox/` 执行 `mcp_eval rebuild fixtures/rebuild-batch`，重建命令退出码为 **0**，标准错误输出为空。过期占位文件已替换为按冻结计划及现有结果生成的报告：

- [summary.json](../sandbox/fixtures/rebuild-batch/summary.json)
- [report.md](../sandbox/fixtures/rebuild-batch/report.md)

批次标识保持为 `replay-smoke-20261023T071912756704Z-a8c6923f`。重建前 summary 为 `{"stale": true, "total": 999}`，report 仅有 STALE 提示。

## 本批统计

| 范围 | 计划数 | 通过 | 失败 | 无法判断 | 计划内通过率 | 判定覆盖率 |
|---|---:|---:|---:|---:|---:|---:|
| 正向用例 | 6 | 5 | 0 | 1 | 83.3% | 83.3% |
| 负面控制 | 2 | 1 | 1 | 0 | 50.0% | 100.0% |
| 合计 | 8 | 6 | 1 | 1 | 75.0% | 87.5% |

- 已判定条目通过率为 `6/7 ≈ 85.7%`；它与计划内通过率 `6/8 = 75.0%` 分母不同。
- **N02 失败**：温度 40 的越界请求应返回约定错误，现有响应未出现该错误，原判定为“预期错误未出现”。失败类别为 `assertion_failed: 1`。
- **P05 无法判断**：`execution_status=not_run`、`trace_complete=false`、`error_category=fixture_missing_evidence`，缺失响应证据；保留在计划分母中。
- `observed=8` 表示存在 8 条结果记录，状态为 7 条 `completed`、1 条 `not_run`，不能解释为本次新执行了 8 个工具调用。manifest 原有计数字段保持原样；报告分母依据其 `planned_items`。
- 本批均为 `channel=replay`、`source_type=synthetic`，原记录注明人工构造混合结果；不能用于真机、真实模型或客户端能力结论。
- 时延均未知，summary 保留 `null` 和样本数 0，未用零时延替代未知数据。

## 重建是否等同于重新调用工具

**不等同。** 本次只重算汇总指标并生成 Markdown 报告，没有重新调用工具、模型或设备，也没有重放录制。

源码依据：

1. `sandbox/src/mcp_eval/__main__.py:61–67` 从本批 `manifest.json` 取得冻结用例、`planned_items` 和 `run_id`，将它们与本批 `results.jsonl` 传给 `write_report`。当前 configs 和用例目录不替代冻结定义。
2. `sandbox/src/mcp_eval/report.py:37–67,103–115` 读取已有 verdict，核对条目身份，以冻结计划为分母汇总并写入两个输出文件；不调用执行器，也不重新运行 `judge_record`。
3. 因此本次保留 N02 的失败与 P05 的证据缺失，不能通过报告重建补齐证据或获得新的运行结论。

退出码 0 在本次 `rebuild` 分支中表示报告生成成功，**不表示本批全部用例通过**。

## 原始输入与产品完整性

使用 SHA-256（文件内容指纹）记录并比较重建前后内容：

- 重建前，本批 13 个文件均与预置 `input-hashes-before.json` 的对应项一致。
- 前后共核对 **35 个文件**，仅 `fixtures/rebuild-batch/summary.json` 和 `report.md` 改变。
- **33 个受保护文件内容不变**：本批 manifest、results、录制副本及 8 个 artifacts 共 11 个文件；产品 Python 源码 14 个、配置 JSON 6 个、README 和 requirements 共 22 个文件。
- 8 个 artifact 与对应 results 记录逐项一致；录制副本指纹与 manifest 的 `recording_sha256` 一致；14 个产品源码指纹与 manifest 的 `engine_sources` 一致。
- 命令后再次列举源码、配置和目标批次文件，清单与此前一致，没有新增字节码缓存。

前后指纹与比较依据：

- [hashes-before.json](hashes-before.json)、[hashes-after.json](hashes-after.json)
- [baseline-check.json](baseline-check.json)、[hash-comparison.json](hash-comparison.json)
- [verification.json](verification.json)：独立核对结果记录、分组指标、8 行报告条目、证据对应关系及指纹。

## 命令证据与额外访问

终端为 Ubuntu Bash，工作目录为本组 `sandbox/`；使用用户指定解释器、`PYTHONPATH=src`，并设置 `PYTHONDONTWRITEBYTECODE=1` 与 `-B` 禁止写入字节码缓存。实际命令参数与退出码见 [rebuild-command.json](rebuild-command.json)。本次仅执行一次产品重建。

- 产品命令原始输出：[stdout](rebuild.stdout.txt)、[stderr](rebuild.stderr.txt)（空）。
- 核验脚本与原始输出：[check_rebuild.py](check_rebuild.py)、[stdout](verification.stdout.txt)、[stderr](verification.stderr.txt)（空）。
- 完整读取、搜索、额外访问及命令记录：[access-log.md](../access-log.md)。

按上层要求读取了项目根 `docs/README.md`、`memory/CURRENT.md`；另加载通用流程 `using-agent-skills`、`verification-before-completion`。未读取目标 Skill 或 references，未打开其他组、历史评测及评分标准文件。强制读取的索引和记忆包含历史结果/评分摘要，因此本轮不能称为完全盲评；这些额外访问已披露。

本次未连接设备/API、安装依赖或执行提交。未读取或修改预置 `timing.json`，不估算未知 token 或时长。本组任务已完成；后续交接状态保存在本组 [memory/CURRENT.md](../memory/CURRENT.md)。
