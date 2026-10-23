# 冻结批次报告重建结果

## 1. 结论与产物

已使用本批次冻结的 manifest 和既有 results 重建 `summary.json`、`report.md`。计划共 **8 项：6 项通过、1 项失败、1 项无法判断**。本次重建完成，不代表批次全部通过。

- 批次：`sandbox/fixtures/rebuild-batch/`。
- `run_id`：`replay-smoke-20261023T071912756704Z-a8c6923f`。
- [重建 summary](../sandbox/fixtures/rebuild-batch/summary.json)。
- [重建报告](../sandbox/fixtures/rebuild-batch/report.md)。
- [实际命令、退出码及 stdout/stderr 索引](commands.md)。
- [访问记录及额外访问说明](../access-log.md)。
- [哈希逐文件校验](10-immutable-check.stdout.txt)、[统计与证据独立核验](11-verify.stdout.json)。

## 2. 实际执行

首先读取本组 `skills/mcp-eval/SKILL.md`，依项目约束补读上层索引及当前记忆。随后核对目标批次和报告规则、保存前哈希，再查阅脚本帮助、完成本机环境自检，执行一次 `rebuild`，读取产物并保存后哈希及独立核验结果。

执行位置为开发机 Ubuntu Bash，本组 `sandbox/`，使用用户指定解释器：

```bash
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -m mcp_eval rebuild fixtures/rebuild-batch > ../outputs/07-rebuild.stdout.txt 2> ../outputs/07-rebuild.stderr.txt
```

这是助手已执行的命令，用户无需重复执行。`PYTHONPATH=src` 指向 sandbox 内产品包；`PYTHONDONTWRITEBYTECODE=1` 禁止生成 Python 字节码缓存。标准输出保存至 `07-rebuild.stdout.txt`，标准错误保存至 `07-rebuild.stderr.txt`。

本次命令退出码为 **0**，stdout 给出本组两份报告路径，stderr 为空。该退出码仅证明重建入口执行完成。自检只证明本机基础环境可用，adb 命令存在不代表已连接设备。

## 3. 计划、判定与证据

计划分母来自 manifest 的 `planned_items`，结果8行对应8个唯一计划项；8份 artifact 与对应 results 记录完全一致。全部为 L1（工具接口层）合成回放，模型字段为 `null`，重复序号均为0。

| 分组 | 计划 | 通过 | 失败 | 无法判断 | 计划内通过率 | 判定覆盖率 |
|---|---:|---:|---:|---:|---:|---:|
| 负面 | 2 | 1 | 1 | 0 | 1/2 = 50% | 2/2 = 100% |
| 正向 | 6 | 5 | 0 | 1 | 5/6 ≈ 83.33% | 5/6 ≈ 83.33% |
| 合计 | **8** | **6** | **1** | **1** | **6/8 = 75%** | **7/8 = 87.5%** |

已判定项通过率为 `6/7 ≈ 85.71%`，不能替代计划内通过率。未执行、证据不足项保留在分母中；`observed=8` 表示有8条结果记录，不表示8条均已执行或通过。

| item | case | 记录状态 | 判定 | 本批依据 |
|---|---|---|---|---|
| item-00001 | N01 | completed | pass | 未知工具错误符合冻结断言 |
| item-00002 | N02 | completed | fail | 温度40的越界请求返回成功，预期错误未出现 |
| item-00003 | P01 | completed | pass | 合成工具列表满足冻结断言 |
| item-00004 | P02 | completed | pass | 合成设置22及其回读满足断言、后置条件 |
| item-00005 | P03 | completed | pass | 合成下边界16及其回读满足断言、后置条件 |
| item-00006 | P04 | completed | pass | 合成开关响应满足冻结断言 |
| item-00007 | P05 | not_run | unassessed | `fixture_missing_evidence`；无响应且轨迹不完整 |
| item-00008 | P06 | completed | pass | 合成上边界30及其回读满足断言、后置条件 |

逐项证据位于批次的 `artifacts/item-00001.json` 至 `item-00008.json`，相对路径见生成报告。

### 需要保留的问题

1. **N02 的失败有明确证据。** 冻结用例要求错误码 `-32602` 并匹配温度越界原因；记录返回 `result.isError=false`、`result.success=true`。因此保留 `fail`，不倒改期望。此记录为人工构造样本，不能据此宣称真实车机存在同样缺陷。成功响应也不证明温度实际变为40。
2. **P05 证据不足，保持无法判断。** 原始记录为 `not_run`、`response_raw=null`、`trace_complete=false`，不能转为通过，也不能移出计划。若后续需要验证资源读取，应在另行获准的真实批次中补齐入口与完整证据。
3. **原 manifest 的执行元数据存在不一致。** `attempted_items=8`，但逐项结果只有7项 `completed`，P05 为 `not_run`。本次按8个冻结计划项报告分母，明确区分8条记录与7项已尝试状态；保留 manifest 原文及哈希。后续由 fixture 维护方核对该字段，不静默修正原始输入。

如后续真实设备出现 N02 类异常，应先按已核实的只读工具回读状态，再按现场已确认的方法恢复；本次仅处理合成历史文件，没有发起回读、恢复或重试。

## 4. 原始输入未变的依据

SHA-256 前后核对覆盖 **29 个受检文件**：

- 11 个批次原始文件：manifest、results、冻结录制副本和8份 artifact。
- 14 个产品 Python 源文件；其哈希也全部匹配 manifest 的 `engine_sources`。
- 4 个 Skill 相关文件：主说明、两份引用文档、自检脚本。未读取或处理 `evals/` 的内容。

[前哈希](01-immutable-before.sha256) 与 [后哈希](08-immutable-after.sha256) 完全一致，`sha256sum --check` 的29项全部成功。批次前哈希还与本组预置 `input-hashes-before.json` 对应条目一致；只使用其中 `rebuild-batch/` 的哈希。

| 原始文件 | 前后相同的 SHA-256 |
|---|---|
| `manifest.json` | `faaafffd0ce90e3b9c36f7de9e3738162f6c5f7df6aa375be7ecc63032930783` |
| `results.jsonl` | `ffbd14e2592447e0a165a6e0520a092d3095e654fd6c0fde8faab81b7f369626` |
| `recording-input.jsonl` | `0a18cffdb92afe1d683d88177f3821f27240bbcac5506d57457ce588e8bcc848` |

录制副本哈希与 manifest 的 `recording_sha256` 相同。冻结用例及配置嵌入 manifest，因此该文件字节不变也覆盖了其中的冻结输入；本次没有以当前 `tests/cases/` 或 `configs/` 替换它们。

允许更新的两份派生产物已变化，依据见 [报告前哈希](02-reports-before.sha256) 与 [报告后哈希](09-reports-after.sha256)：

| 文件 | 重建前 SHA-256 | 重建后 SHA-256 |
|---|---|---|
| `summary.json` | `8d2e984bb434331a3e9f7ad30eb47f68c1c9f8a329d7c70b9c82070d6489d66a` | `9a22ceefb2eec421b0eda479e857617b9a93c794953c6dcce486b8ea509d66d1` |
| `report.md` | `9433d926cb9adf66d24a40f10df130e68325656e8b5a675782817aaa53dcad6e` | `3a4472d5525e1868cff5beeeed0249684b7af88183087fd55dbd5f3352223b39` |

原 summary 为 `{"stale": true, "total": 999}`，原报告仅含 `# STALE：请从冻结批次重建`。本次通过正式重建入口替换这两份占位产物，未手工编辑统计或原始判定。

## 5. 重建是否等同重新调用工具

**不等同。** `rebuild` 根据既有批次的冻结计划、用例和结果重新计算报告，保留同一 `run_id`。本次没有运行 `run`、重放录制、调用 MCP 工具、请求模型 API 或连接设备，也没有生成新一轮工具执行证据。命令帮助和 README 明确说明了该入口的语义，实际命令及原文件哈希与此一致。

全部记录 `source_type=synthetic`，且 provenance 明示 `manually_constructed_mixed_outcomes_not_device_evidence`。因此本次证明的是该人工构造批次的报告能够按冻结证据重建、原始输入未被修改，不证明真实工具、车机状态、模型能力、IDE 适配或 Skill 整套验收通过。

全部 `latency_ms` 未知，报告的时延样本数为0、统计值为 `null`；原记录中的 `replay_wall_ms=0` 不能替代真实工具时延。本次会话总 token 与总时长没有可靠测量，保持未知，不估算，不将0作为缺失值。

## 6. 访问与写入边界

额外访问包括项目根 `docs/README.md`、`memory/CURRENT.md`，全局 `skill-creator`、`verification-before-completion` 两份流程 Skill，以及用户指定 Python 解释器和运行时依赖。上层必读材料、sandbox README 含历史摘要；本组哈希索引含其他 fixture 名称与哈希，文件名搜索返回 Skill 的 `evals/` 路径。这些附带可见信息均已在访问日志中说明，未追踪读取其他组、历史评测文件或具体评分标准。

所有写入位于本组根目录：本批 summary/report、`outputs/` 证据及本组 `access-log.md`。未安装包、修改产品源码/Skill/manifest/results、提交代码或更新上层记忆。用户无需补做操作即可查阅本次产物。
