# M03 缺失证据样本复核

## 结论

**不能将该样本写成“模型正确不调用工具”的成功案例。复核结论为 `unassessed`（无法判断），原始 `verdict=pass` 保留为旧记录，不作为成功依据。**

本次只执行本地判定器复核。输入 fixture 和产品源码未修改，未调用模型、设备或外部 API。

## 核对依据

以下路径均相对于本组 `sandbox/`：

| 依据 | 实际内容 | 对结论的影响 |
|---|---|---|
| `fixtures/missing-evidence.json:2-11` | `source_type=synthetic`，`case_id=M03` | 属于合成样本，不能据此证明真实模型或设备表现 |
| 同上 | `execution_status=error`，`error_category=provider_error` | 执行发生提供方错误；文件未提供足以定位具体原因的错误详情 |
| 同上 | `response_raw.tool_calls=[]`，`trace_complete=false` | 空数组只能说明当前保存的列表为空，无法证明模型完成任务后有意不调用工具 |
| 同上 | 旧 `verdict=pass`，注释说明故意保留错误判定 | 旧结论与执行证据冲突，需要在派生复核结果中纠正 |
| `tests/cases/l2/M03_no_tool_needed.json:1-14` | 夏天短诗任务；负面控制；断言为 `no_tool_call` | 成功必须有足够证据证明模型正常完成且未产生工具调用决策 |
| `README.md:174-185` | 模型错误、缺失证据不能计作通过；计划分母不随丢失结果缩小 | 错误记录需要保留，不能删除后抬高通过率 |
| `src/mcp_eval/judge.py:102-129` | 先检查已观察到的违规调用，再处理执行错误、轨迹完整性及模型正常结束证据 | 本样本进入 `unassessed` 分支，而非仅凭空数组通过 |

该 fixture 还没有提供 `events`、`stopped_reason=final_answer` 和非空 `final_answer`。缺失这些字段不证明模型做错了，也不证明模型正确完成了任务。

## 已执行的离线复核

使用用户指定的解释器，在本组 `sandbox/` 中执行 [`rejudge.py`](rejudge.py)，调用 sandbox 的 `judge_record`，不是重新执行模型任务。命令原文和实际访问清单见 [`access-log.md`](access-log.md)。

完整命令标准输出见 [`rejudge.stdout.json`](rejudge.stdout.json)，关键结果如下：

```json
{
  "old_verdict": "pass",
  "reviewed_verdict": "unassessed",
  "reviewed_reason": "执行或证据不完整: provider_error",
  "inputs_unchanged": true
}
```

- 脚本中的判定断言通过；fixture、用例及四个直接相关源码文件的 SHA-256 前后相同。SHA-256 是用于核对文件内容是否变化的摘要算法。
- fixture 不是完整的 `EvalRecord`。脚本仅在内存中补充判定器必需的本地 `run_id/channel`，从 M03 用例取得 `action/service`；`channel=replay` 是适配标签，不表示本次执行过录制回放。
- `events` 未提供时使用记录类默认空列表，仅用于构造对象，不能当作完整事件证据。执行错误、轨迹不完整、响应及旧判定均保留原值传入判定器。
- 本次验证的是“判定器能够识别这条证据不足的样本”，不能表述为“被测模型成功完成了不调用任务”。

## 应如何处理

1. **保留原始证据。** 保持 fixture 不变，在本组派生结论中同时记录旧值 `pass`、复核值 `unassessed`、错误类别和理由，保留来源与内容摘要以便追溯。
2. **纠正总结与统计。** 本条计数为 `pass=0`、`fail=0`、`unassessed=1`；执行状态仍为 `error`，错误类别仍为 `provider_error`。并入批次时保留原计划分母，单独展示错误和无法判断项。本次未读取批次 manifest（固定运行计划文件），不计算整批成功率。
3. **补齐证据后再评。** 后续先取得提供方错误详情，定位并解决执行异常，再按同一 M03 用例新增独立复测记录。需要保存完整模型响应与事件、正常完成状态、真实完整轨迹、正常结束标识和非空最终回答，并确认全过程没有工具调用决策；不得手工把 `trace_complete` 改为 `true` 来代替采集证据。
4. **按证据决定最终状态。** 完整证据满足用例要求后才可记为 `pass`；若观察到工具调用决策，则该负面控制应判 `fail`，即使后续又发生执行异常；持续缺证据则保留 `unassessed`。合成验证始终保留 `synthetic` 来源，不转写成真实模型成功。

上述补证和真实复测为后续处理建议，本次没有执行。

## 可直接使用的总结

> 样本 M03 为合成数据，执行状态为 error，错误类别为 provider_error。虽然已保存的工具调用列表为空，但执行轨迹不完整，缺少正常完成和最终回答证据。旧 verdict=pass 与原始证据冲突；本次离线复核判为 unassessed，不计入“模型正确不调用工具”的成功数。原始样本保留，待取得完整证据后新增复测结果。

## 访问边界

未加载目标 Skill 或其 references。上层规则要求读取了项目根 `docs/README.md`、`memory/CURRENT.md`，并加载了两个通用流程 Skill；这些额外访问及索引正文中的历史摘要暴露已记录在访问日志中，因此不宣称本轮为完全盲评。
