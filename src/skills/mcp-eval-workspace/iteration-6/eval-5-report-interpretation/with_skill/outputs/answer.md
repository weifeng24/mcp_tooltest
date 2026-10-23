# 指定批次报告解读

## 1. 结论与核对范围

**计划 8 项，通过 6 项、失败 1 项、无法判断 1 项；计划内通过率为 6/8＝75.0%。P05 未执行且缺少证据，必须保留在分母中。全部记录均为人工构造的合成回放证据，不能支撑真机、真实模型或 IDE／客户端评测通过的结论。**

- 交付根：本组 `sandbox/`。
- 批次路径：`sandbox/fixtures/report-batch/`。
- `run_id`：`replay-smoke-20261023T071912756704Z-a8c6923f`。
- 已读取：指定 Skill、报告解读契约、批次 `manifest.json`、`results.jsonl`、`summary.json`、`report.md` 及全部 8 份 `artifacts/item-*.json`。
- 已执行：使用用户指定 Python 解释器进行一次本地静态统计与文件一致性核对。未导入评测器、未重跑工具、未重建报告、未连接设备或 API。
- 核对输出：[local-check.stdout.json](./local-check.stdout.json)。读取范围和完整命令见 [access-log.md](./access-log.md)。

以下证据路径除特别说明外，均相对于 `sandbox/fixtures/report-batch/`。

## 2. 数量与统计口径

分母取 `manifest.json.planned_items` 的 8 个固定计划项，包括 6 条正向用例、2 条负面用例。全部属于 L1（工具接口级）、`channel=replay`；各项 `model=null`、`repeat_index=0`，即无被测模型、每项仅有第 1 次记录。

| 范围 | 计划 N | 通过 P | 失败 F | 无法判断 U | 未执行 | 计划内通过率 P/N | 判定覆盖率 (P+F)/N |
|---|---:|---:|---:|---:|---:|---:|---:|
| 全批次 | 8 | 6 | 1 | 1 | 1 | 75.0% | 87.5% |
| 正向用例 | 6 | 5 | 0 | 1 | 1 | 83.3% | 83.3% |
| 负面用例 | 2 | 1 | 1 | 0 | 0 | 50.0% | 100.0% |

- `results.jsonl` 有 8 条记录，与计划项一一对应，无缺失、多余或重复的 `item_id`。8 份 artifact 与对应结果记录内容相同。
- 执行状态为 `completed=7`、`not_run=1`。未执行项属于无法判断项，不能再与 U 相加作为另一项。
- 已判定项通过率为 `6/(6+1)≈85.7%`，它排除了 P05，**不能替代计划内通过率 75.0%**。正向组的已判定项通过率为 `5/5=100%`，也不能表述为全部 6 条正向通过。
- 两个分组的数量和比例与 `summary.json`、`report.md` 一致；全批次比例由固定计划和逐项结果计算。
- `manifest` 保留 `state=finished`、`recorded_items=8`、`attempted_items=8`，但 P05 的实际记录为 `not_run`。这些批次元数据不能证明 8 项均执行完成，也不能证明全部通过。夹具明确经过人工构造；本轮没有修改这些元数据，也未追溯其生成过程。

## 3. 逐项判定及未完成项

以下各行均属于上述同一 `run_id`，`model=null`、`repeat_index=0`。

| item / case | 状态 / 判定 | 核对依据及边界 | 证据 |
|---|---|---|---|
| item-00001 / N01 | completed / pass | 未知工具返回错误码 `-32602`，消息 `Unknown tool: MCPVehicleService.noSuchTool` 与冻结的错误类型及消息模式匹配。支持此合成负例符合预期。 | `manifest.json` 中 N01；`results.jsonl` 第 1 行；`artifacts/item-00001.json` |
| item-00002 / N02 | completed / fail | 请求温度 40，冻结预期要求 `-32602` 及温度越界错误消息；记录却返回 `result.isError=false`、`result.success=true`，未出现预期错误。 | `manifest.json` 中 N02；`results.jsonl` 第 2 行；`artifacts/item-00002.json` |
| item-00003 / P01 | completed / pass | 合成工具列表包含 `HvacService.getTemp`、`HvacService.setTemp` 及参数结构定义，满足本用例的冻结检查。只覆盖这份样例列表，不能据此证明真实发现接口或完整 8 服务目录。 | `manifest.json` 中 P01；`results.jsonl` 第 3 行；`artifacts/item-00003.json` |
| item-00004 / P02 | completed / pass | 设置 22 的合成响应包含 `structuredContent.success=true`，附带独立 `getTemp` 后置条件记录，读回值为 22。 | `manifest.json` 中 P02；`results.jsonl` 第 4 行；`artifacts/item-00004.json` |
| item-00005 / P03 | completed / pass | 设置下边界 16 的合成响应成功，附带 `getTemp` 后置条件记录，读回值为 16。 | `manifest.json` 中 P03；`results.jsonl` 第 5 行；`artifacts/item-00005.json` |
| item-00006 / P04 | completed / pass | `MCPVoiceService.setAcSwitch(value=1)` 的合成响应满足 `structuredContent.success=true`；该用例未设置状态回读后置条件，不能扩展为开关实际生效或跨服务路由隔离已验证。 | `manifest.json` 中 P04；`results.jsonl` 第 6 行；`artifacts/item-00006.json` |
| item-00007 / P05 | not_run / unassessed | 目标为读取 `dds://Hvac_Status_topic`。`response_raw=null`、`trace_complete=false`，原因是 `fixture_missing_evidence`。没有足够执行证据，保持无法判断。 | `manifest.json` 中 P05；`results.jsonl` 第 7 行；`artifacts/item-00007.json` |
| item-00008 / P06 | completed / pass | 设置上边界 30 的合成响应成功，附带 `getTemp` 后置条件记录，读回值为 30。 | `manifest.json` 中 P06；`results.jsonl` 第 8 行；`artifacts/item-00008.json` |

### P05：唯一未执行、未完成判定的计划项

P05 有一条占位结果记录和对应 artifact，但没有资源读取响应。不能把“存在结果文件”视为已执行，不能把缺证据改判为通过，也不能据此宣称资源接口存在功能故障。冻结用例备注还标明真实设备资源入口尚未接入，但本批次记录的直接原因是 `fixture_missing_evidence`；不得擅自替换为已经验证的真机故障原因。

后续需要为该冻结计划项补充可追溯的执行及响应证据，再评估列表非空、目标 URI 匹配等断言。新证据应独立留存并关联原批次，不修改本夹具掩盖缺失。本轮未补跑。

### N02：已执行失败，不属于未执行项

N02 的 `fail` 有明确依据：温度 40 超过冻结示例最大值 30，响应却未提供预期越界错误。`summary.json.failure_categories.assertion_failed=1` 与此对应。不能因响应写着“成功”就把负例改为通过。

此记录没有 N02 的状态回读；**无法判断温度是否真的变为 40、是否被截断到允许范围，或根本未生效**。更不能将人工合成响应写成真实车机存在同样缺陷。

若后续另行获得真实设备验证授权，应先核实真实工具契约及现场状态恢复方法；遇到同类异常成功时保留请求、响应与失败证据，通过已核实的只读工具回读实际状态，区分接受、截断或未生效，再按现场已确认方法恢复。业务预期应在新测试前冻结，不得按结果倒改。本轮未发起回读、恢复或重试。

## 4. 数据来源与可支持的结论

### 来源核对

全部 8 条结果及 artifact 均声明：

- `channel="replay"`；
- `source_type="synthetic"`；
- `provenance.source_run_id="synthetic-v2"`；
- `provenance.skill_eval_fixture="manually_constructed_mixed_outcomes_not_device_evidence"`。

因此，这是**人工构造的混合判定夹具**。批次名称中的 `replay-smoke`、时间戳以及 `trace_complete=true` 等字段不构成真实设备执行证明。P02/P03/P06 的回读记录同样标记为 synthetic。

`manifest` 保存 Python 版本、评测器源文件哈希、录制哈希和服务配置中的基线提交；这些字段只说明快照记录了哪些标识。本轮未读取评测器源码或原始录制文件来复算哈希，未核实设备二进制与基线的对应关系。`device_serial` 为空，`models`、`model_refs`、`tools` 均为空，也不存在真实模型调用证据。

### 本批证据能够支持

1. 固定 8 项计划下，当前夹具结果是 6 通过、1 失败、1 无法判断；计划内通过率 75.0%，判定覆盖率 87.5%。
2. 结果、逐项 artifact 和报告汇总在本次静态核对范围内一致；能定位 N02 的预期错误缺失与 P05 的执行证据缺失。
3. N01、P01、P02、P03、P04、P06 的所存合成响应与各自冻结判据相符；P02/P03/P06 还包含符合预期的合成状态回读。
4. 本夹具可用于检查混合判定、未执行项和分母口径的报告解读行为。本轮完成的是这一份证据的读取及一致性核对。

### 本批证据不能支持

- 真实车机工具可用、真实温度或开关状态改变、真实资源读取成功、完整工具发现或 8 服务覆盖。
- 真实服务存在 N02 同类越界缺陷，或 P05 资源接口已经功能失败。
- 模型级（L2）工具选择和调用能力、双模型接通、真实模型 API 调用成功，或任何 IDE（集成开发环境）／客户端适配通过。
- 当前评测器重新运行可复现这些结果、评测器全部实现正确、完整回归通过。本轮未运行评测器，人工构造的结果也不能替代独立执行证据。
- Skill 整套评测通过、相对其他版本有稳定增益、导师验收或公司项目验收通过；这里只完成一个指定场景。
- 真实设备性能、模型 token 用量、成本或本轮总耗时。全部主记录 `latency_ms=null`，摘要有效时延样本为 0；`replay_wall_ms` 的 0/1 只是所存回放字段，不得作为真机耗时。本轮 token 和总耗时未知，未估算。

## 5. 本轮交付状态

已在本组 `outputs/` 保存本解读、访问记录和本地静态核对命令的原始标准输出。仅创建这些输出文件；夹具、Skill、源码和上层记忆均未修改。未重跑工具、安装依赖、连接设备/API 或执行版本提交。
