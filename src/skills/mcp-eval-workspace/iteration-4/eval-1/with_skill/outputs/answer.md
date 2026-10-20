# 场景 1：离线回放实际结果（with_skill）

## 结论

已在指定交付根目录执行一次正式离线回放，生成独立新批次。根据本次命令输出及新批次的 manifest、逐项结果、汇总、报告和全部 8 份 artifact 核对：**计划 8 项，执行 8 项，通过 8 项，失败 0 项，无法判断 0 项，未执行 0 项**。

数据全部为 `synthetic`，仅证明这些合成样本在当前评测器上的离线回放与判定结果，不证明真实车机、真实模型或 IDE／客户端能力，也不代表项目最终验收通过。

## 执行信息

- 终端：Ubuntu Bash。
- 工作目录：`/home/tssh/文档/Works/mission/校招生ai演练任务/src`。
- 解释器：`tests/results/remediation-2026-10-16/.venv/bin/python`；本次 manifest 记录 Python `3.10.12`。
- 环境：`PYTHONPATH=src`；另设 `PYTHONDONTWRITEBYTECODE=1`，禁用 Python 字节码缓存写入。
- 已读取 `skills/mcp-eval/SKILL.md` 与 `references/report-guide.md`；先执行环境脚本帮助、自检、CLI 帮助及 dry-run，再执行正式回放。自检通过，dry-run 显示计划 8 项、执行 0 项、`device_verified=false`、无警告。
- 正式执行命令（已由助手执行，无需用户重复）：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval run configs/runs/replay_smoke.json
```

- 实际 `run_id`：`replay-smoke-20261020T082342228588Z-d64d2f10`。
- 结果时间：`2026-10-20T16:23:42+08:00`。
- 实际新批次绝对路径：

```text
/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/replay-smoke-20261020T082342228588Z-d64d2f10
```

- 正式运行返回 `executed=8`、`interrupted=false`、`warnings=[]`；manifest 为 `state=finished`、`recorded_items=8`、`attempted_items=8`。

## 计划与逐项结果

分母取本批次 `manifest.json` 的 8 个 `planned_items`，与 `results.jsonl` 的 8 个计划项逐项对应。所有条目均为 L1（接口级）、`channel=replay`、`model=null`、`repeat_index=0`、`execution_status=completed`、`source_type=synthetic`。

| 分组 | 计划 | 通过 | 失败 | 无法判断 | 未执行 | 计划内通过率 | 判定覆盖率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 正向 | 6 | 6 | 0 | 0 | 0 | 100% | 100% |
| 负面 | 2 | 2 | 0 | 0 | 0 | 100% | 100% |
| 合计 | 8 | 8 | 0 | 0 | 0 | 100% | 100% |

以下证据路径均相对于实际新批次目录。

| 计划项 | 用例 | 判定 | 实际证据摘要 | 证据文件 |
|---|---|---|---|---|
| item-00001 | N01 | pass | 未知工具返回 `-32602`，信息为 `Unknown tool: MCPVehicleService.noSuchTool`，匹配冻结的预期错误类型与信息 | `artifacts/item-00001.json` |
| item-00002 | N02 | pass | 温度 40 返回 `-32602`，信息为 `temperature 40 out of range [16,30]`，匹配参数越界预期 | `artifacts/item-00002.json` |
| item-00003 | P01 | pass | 合成工具列表含 `HvacService.getTemp` 和 `HvacService.setTemp` 及输入 schema，满足冻结断言 | `artifacts/item-00003.json` |
| item-00004 | P02 | pass | 合成设置温度 22 返回成功，独立 `getTemp` 回读为 22 | `artifacts/item-00004.json` |
| item-00005 | P03 | pass | 合成设置下边界温度 16 返回成功，独立回读为 16 | `artifacts/item-00005.json` |
| item-00006 | P04 | pass | 合成 `MCPVoiceService.setAcSwitch(value=1)` 返回 `success=true` | `artifacts/item-00006.json` |
| item-00007 | P05 | pass | 合成资源响应非空，URI 为 `dds://Hvac_Status_topic` | `artifacts/item-00007.json` |
| item-00008 | P06 | pass | 合成设置上边界温度 30 返回成功，独立回读为 30 | `artifacts/item-00008.json` |

负面用例通过依据是响应匹配预先冻结的错误判据，不是“出现任意错误即通过”。P02、P03、P06 的回读属于对应计划项的后置条件，不另增计划分母。

## 来源与可追溯性

- 配置：`configs/runs/replay_smoke.json`，`channel=replay`、`model_refs=[]`、`repeat=1`。
- 原始录制：`recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl`。
- 本批次录制副本：`recording-input.jsonl`。
- 原始录制包含 11 条合成事件：8 条主事件及 3 条状态回读；均标注 `source_type=synthetic`、`run_id=synthetic-v2`。
- 结果中的 `provenance.source_run_id=synthetic-v2`。N01、N02、P01、P02、P03、P04、P05、P06 的主事件索引分别为 `0:0`、`1:0`、`2:0`、`3:0`、`5:0`、`7:0`、`8:0`、`9:0`；三个回读索引为 `4:0`、`6:0`、`10:0`。
- 已执行 `sha256sum`：原始录制与本批次副本均为 `0a18cffdb92afe1d683d88177f3821f27240bbcac5506d57457ce588e8bcc848`，与 manifest 的 `recording_sha256` 一致。
- manifest 保存冻结的用例、服务配置、运行配置及 14 个评测器源码文件的哈希。服务配置中的基线提交 `f152ba865b433b0769af18c4ab03db501d24bbef` 仅为配置记录；`device_serial` 为空，本轮未核验设备二进制或访问其源码树。
- 原始合成输入没有采集时间；结果中的 `source_timestamp` 不作为历史设备采集时间证明。`latency_ms` 为 `null`，汇总时延样本数为 0，不能报告为车机时延 0 ms。

## 问题、边界与产物

本次批次无失败、无法判断、缺失计划项或运行警告。P01／P05 的合成回放通过不证明设备具备工具发现／资源读取通道。模型计划数为 0，未执行 L2（模型级）或 IDE／客户端评测。

没有运行 pytest 测试、连接设备或外部模型，也没有修改既有源码、配置、文档或提交 Git。环境自检只检查依赖可导入，其中包含 pytest 的导入检查，不是测试执行。本轮仅运行一次正式 `run replay_smoke`，未执行 rebuild，未读取旧批次或其他组评测结果。

新批次共 13 个文件：`manifest.json`、`results.jsonl`、`summary.json`、`report.md`、`recording-input.jsonl` 及上表的 8 个 artifact。助手使用 `apply_patch` 新增的文件仅为本目录 `answer.md` 和 `access-log.md`；完整访问路径、工具、命令及产物列表见 [access-log.md](access-log.md)。

本次离线任务已具备结果与来源证据。若后续需要真机、模型或客户端结论，应在对应任务中另行取得实际调用、版本及原始日志证据。
