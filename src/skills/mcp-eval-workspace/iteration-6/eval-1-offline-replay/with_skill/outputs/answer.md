# 离线回放评测结果

## 结论

已在本组 `sandbox` 中对 `configs/runs/replay_smoke.json` 执行 **1 次正式离线评测**，此前完成帮助查看、环境自检及一次 `--dry-run`。正式命令退出码为 **0**；固定计划 8 项，执行 8 项，通过 8 项，失败 0 项，无法判断 0 项，未执行 0 项。

全部结果来源为 **`synthetic` 合成样本**，执行通道为 `replay`。本次证明这组输入的离线回放、断言判定和报告生成完成，不构成真机、真实模型、IDE 客户端或整个 Skill 行为评测通过的结论。

## 执行与批次

- 工作目录：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-1-offline-replay/with_skill/sandbox`
- Python：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python`
- 环境：`PYTHONPATH=src`、`PYTHONDONTWRITEBYTECODE=1`。
- 实际 `run_id`：`replay-smoke-20261023T073041689863Z-ee5b5d7f`。
- 本次批次目录：`sandbox/tests/results/replay-smoke-20261023T073041689863Z-ee5b5d7f/`，由本次命令输出取得。
- `manifest.state=finished`，`interrupted=false`，`warnings=[]`；模型配置为空，重复次数为 1，所有条目的 `model=null`、`repeat_index=0`。
- 自检通过本机基础依赖检查；其 adb 存在检查不代表设备连接或接口可用。预检返回 `executed=0`、`device_verified=false`。

正式命令通过本组 `outputs/capture_command.py` 捕获。实际执行的子命令为：

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -m mcp_eval run configs/runs/replay_smoke.json
```

这是已执行命令记录，无需用户再次运行。

## 数量与逐项证据

分母来自本次 `manifest.planned_items`；与 `results.jsonl`、`summary.json`、`report.md` 对照一致。

| 范围 | 计划 | 通过 | 失败 | 无法判断 | 未执行 | 计划内通过率 | 判定覆盖率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| L1 正向 | 6 | 6 | 0 | 0 | 0 | 100% | 100% |
| L1 负面 | 2 | 2 | 0 | 0 | 0 | 100% | 100% |
| 合计 | 8 | 8 | 0 | 0 | 0 | 100% | 100% |

L2 计划数为 0。所有计划项均为 `completed/pass`、`source_type=synthetic`，没有缺失计划项。以下证据路径相对于本次批次目录。

| 条目 / 用例 | 本次响应与判定依据 | 证据 |
|---|---|---|
| item-00001 / N01 | 未知工具返回 `-32602`，消息为 `Unknown tool: MCPVehicleService.noSuchTool`；与冻结的错误码和消息规则匹配。 | `artifacts/item-00001.json` |
| item-00002 / N02 | 温度 40 返回 `-32602`，消息为 `temperature 40 out of range [16,30]`；与冻结的越界错误规则匹配。 | `artifacts/item-00002.json` |
| item-00003 / P01 | 工具列表含 `HvacService.getTemp`、`HvacService.setTemp` 及输入 schema；非空、命名和指定工具存在性断言通过。 | `artifacts/item-00003.json` |
| item-00004 / P02 | 设置 22 返回 `success=true`；独立 `getTemp` 合成回读为 22，满足后置条件。 | `artifacts/item-00004.json` |
| item-00005 / P03 | 下边界 16 返回 `success=true`；独立 `getTemp` 合成回读为 16。 | `artifacts/item-00005.json` |
| item-00006 / P04 | `MCPVoiceService.setAcSwitch(value=1)` 返回 `success=true`，满足该用例冻结断言；该用例未配置独立状态回读。 | `artifacts/item-00006.json` |
| item-00007 / P05 | 资源响应非空，返回 URI 为 `dds://Hvac_Status_topic`，满足冻结断言。 | `artifacts/item-00007.json` |
| item-00008 / P06 | 上边界 30 返回 `success=true`；独立 `getTemp` 合成回读为 30。 | `artifacts/item-00008.json` |

负面用例的通过依据是匹配预先冻结的特定错误，不是任意报错或没有调用。3 次后置条件回读属于对应计划项的证据，不额外计入计划分母。

## 来源核对

- 输入录制：`sandbox/recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl`。
- 批次冻结副本：[recording-input.jsonl](../sandbox/tests/results/replay-smoke-20261023T073041689863Z-ee5b5d7f/recording-input.jsonl)。已完整读取，其中 11 条合成记录对应 8 项主动作和 3 次后置条件回读；来源批次标识为 `synthetic-v2`。
- 原录制与冻结副本经 `sha256sum` 校验一致，并与 manifest 的 `recording_sha256` 一致：
  `0a18cffdb92afe1d683d88177f3821f27240bbcac5506d57457ce588e8bcc848`。
- manifest 冻结了用例、服务配置、运行配置和评测器源码哈希；记录 Python `3.10.12`、schema 版本 2。服务配置中的基线提交仅为配置记录，未访问对应外部源码树、未核验车端二进制。
- 已读取全部 8 份 artifact。`results.jsonl` 的 3 条长行在读取工具中显示截断，其完整后置条件与来源已通过对应的多行 artifact 核对。

本批次没有失败、无法判断、`no_recording` 或缺失执行证据项。P01/P05 的合成通过不证明设备侧工具发现或资源读取可用；P04 的成功响应不证明真实设备状态发生变化。

## 未验证事项与后续

本次未连接设备或模型 API，未执行真实模型及 IDE 客户端评测。真实接口时延均为未知：汇总中的时延样本数为 0，统计值为 `null`，不能报告为 0 ms。本组未取得执行代理的 token 总量或总耗时统计，未估算、未补造。

本次离线任务没有需整改的失败项。若后续开展真实评测，需以已核验的设备版本、工具定义及真实请求/响应证据建立独立批次；本报告不替代该验证。

## 证据入口与上下文披露

- [manifest.json](../sandbox/tests/results/replay-smoke-20261023T073041689863Z-ee5b5d7f/manifest.json)
- [results.jsonl](../sandbox/tests/results/replay-smoke-20261023T073041689863Z-ee5b5d7f/results.jsonl)
- [summary.json](../sandbox/tests/results/replay-smoke-20261023T073041689863Z-ee5b5d7f/summary.json)
- [report.md](../sandbox/tests/results/replay-smoke-20261023T073041689863Z-ee5b5d7f/report.md)
- [正式命令 stdout](05-replay.stdout.txt)、[stderr](05-replay.stderr.txt)、[退出码及命令元数据](05-replay.execution.json)
- [录制哈希校验](06-recording-sha256.stdout.txt)
- [完整访问与执行记录](access-log.md)：包含每次显式读取、命令及返回，以及其他命令的原始 stdout/stderr 路径。

**存在额外上下文访问。** 上层规则要求读取根目录 `docs/README.md` 与 `memory/CURRENT.md`，其中包含历史回归及 Skill 对照摘要，已记录为上下文污染；未继续打开其引用的历史运行答案、历史 Skill 工作区或评分材料。另加载了全局 `skill-creator`、`using-agent-skills`、`verification-before-completion` 指导。本次结论仅依据上述新批次证据。

文件写入限定在本组：命令产物位于 `sandbox/tests/results/`，回答、日志与捕获脚本位于 `outputs/`。未编辑产品、Skill 或主项目文件，未安装依赖、未提交。
