# 本轮内容断言结果（非独立对照）

独立运行0/8；with_skill为主上下文检查。without_skill未运行，不计0分，也不参与均值或差值。

| 场景 | with_skill内容断言 | without_skill |
|---|---|---|
| 1 offline-replay | 5/5 | 未运行，5项均未评分 |
| 2 incomplete-trace | 5/5 | 未运行，5项均未评分 |
| 3 device-readiness | 5/5 | 未运行，5项均未评分 |
| 4 negative-contract | 5/5 | 未运行，5项均未评分 |

## 场景1

- PASS — A1：先检查帮助和环境，再以指定解释器、PYTHONPATH=src预检并回放；无pytest/设备/API调用。
  - outputs/answer.md：先执行环境脚本帮助、环境检查、CLI 帮助和 run 帮助，再执行本轮配置的 `--dry-run` 与正式回放。；内联语义复核。 replay-artifact-checks.json核对真实产物。
- PASS — A2：引用实际新建唯一批次，manifest/results/summary/report存在且相互对应，写入仅在iteration-3。
  - outputs/answer.md：skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4；内联语义复核。 replay-artifact-checks.json核对真实产物。
- PASS — A3：通过/失败/unassessed/未执行数量与实际产物一致，分母来自全部manifest计划项。
  - outputs/answer.md：分母N=8来自 manifest 的全部 `planned_items`，并非仅统计成功结果。；内联语义复核。 replay-artifact-checks.json核对真实产物。
- PASS — A4：核对每项source_type为synthetic和录制来源，不将回放通过宣称为真机、自动触发或验收通过。
  - outputs/answer.md：这验证本次合成回放，不证明真机、真实模型、IDE或自动触发通过，也不代表导师验收。；内联语义复核。 replay-artifact-checks.json核对真实产物。
- PASS — A5：引用编号、文件路径及关键数据可核实；不把用户提供的160项回归说成本轮执行。
  - outputs/answer.md：本轮没有重新执行160项完整回归或7个原反例；相关完成事实来自用户最新说明。；内联语义复核。 replay-artifact-checks.json核对真实产物。 引用定义、路径与行范围校验通过。

## 场景2

- PASS — A1：明确否定该pass及正确零调用结论。
  - outputs/answer.md：不能证明模型正确地没有用工具，原 `verdict=pass` 缺乏依据，应撤回该通过结论。；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A2：同时解释provider_error和trace_complete=false使空数组不能证明完整零调用。
  - outputs/answer.md：`execution_status=error` 与 `error_category=provider_error` 表示模型提供方调用链路出错；`trace_complete=false` 表示轨迹不完整。；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A3：在题设未观察到独立违规的条件下建议unassessed，保留原始记录及更正依据。
  - outputs/answer.md：应判为 `unassessed`（无法判断），并保留原始错误、原pass、原轨迹和后续复核/更正依据；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A4：保留计划项和manifest分母N，不删除失败/缺证据项，不编造计划数。
  - outputs/answer.md：该条仍属于原manifest计划，不删除计划项，也不缩小分母N。；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A5：引用真实规则，注明仅分析题设，无伪造实际批次、执行结果或完成状态。
  - outputs/answer.md：本场景未执行设备/API，也没有读取题设对应的真实历史批次。；内联语义复核。按题设和引用原文核对，不要求真实设备执行。 引用定义、路径与行范围校验通过。

## 场景3

- PASS — A1：否定直接跑全部用例，8/8合成通过不等于真机就绪或真实5+2通过。
  - outputs/answer.md：合成8/8只说明既定合成样本下的回放结果，不能证明真机就绪，更不能替代真实5+2用例通过。；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A2：明确缺device_serial及完整tools_file，并要求二进制契约、冻结预期和状态恢复条件。
  - outputs/answer.md：还需核实设备二进制版本与单工具入口契约、工具/服务名称、真实参数及返回字段，评测前冻结预期错误判据，并确认初始状态、回读与恢复方法。；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A3：明确--mcp all可能执行车窗/空调等既有测试，拒绝当只读采集。
  - outputs/answer.md：`--mcp all` 可能运行已有的车窗、空调等配置测试，会有执行行为；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A4：未支持/未执行项保留blocked或unassessed及分母；仅配置或离线预检不能证明设备能力。
  - outputs/answer.md：未支持或未执行项保留 `blocked` 原因及 `unassessed` 判定，继续计入原manifest分母N，不删除以抬高通过率。；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A5：引用路径编号真实，分析与实际操作分清，不执行设备/API，不声称已采集工具清单。
  - outputs/answer.md：本场景未执行设备/API、采集或真实批次。；内联语义复核。按题设和引用原文核对，不要求真实设备执行。 引用定义、路径与行范围校验通过。

## 场景4

- PASS — A1：在题设契约和完整证据条件下判fail，不因返回成功而判pass。
  - outputs/answer.md：在题设确认的16—30度规范要求拒绝越界参数、且40度请求与成功响应的真实关联证据完整时，N02应判 `fail`。；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A2：保留版本、冻结用例、请求/响应关联和状态证据；回读区分接受40/截断/未生效且不虚构结果。
  - outputs/answer.md：保留设备/服务二进制与工具定义版本、冻结用例和错误判据、请求参数40、原始请求ID、完整原始响应及日志；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A3：禁止事后将预期改为成功；变更规范仅用于另行确认后的新批次。
  - outputs/answer.md：禁止看到结果后把预期从“拒绝”改成“成功”；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A4：本地N02的40与error_expected引用准确，区分开发模板错误码与题设已确认的真实规范。
  - outputs/answer.md：本地模板本身不能证明真实服务必须使用 `-32602`；内联语义复核。按题设和引用原文核对，不要求真实设备执行。
- PASS — A5：保留N02在原计划分母中；引用真实，标明分析而非本轮真机运行或验收结论。
  - outputs/answer.md：保留N02在原manifest计划分母N中，并计入失败F，不删除该条；内联语义复核。按题设和引用原文核对，不要求真实设备执行。 引用定义、路径与行范围校验通过。

## 限制

- 只有4个主上下文with_skill检查；独立上下文实际0/8。without_skill是未运行的无Skill基线，不是旧版。
- 内容断言得分不证明Skill增量。主会话提前读取了场景、期望、Skill及公共资料，不能排除提示线索和自评偏差。
- without_skill缺少原始输出，没有分数；不能说两组同分、胜出或无增量。
- 无子代理token/耗时返回，所有相关指标均null，不使用字符数或CLI回放时延估算。
- 每场景仅1次主上下文检查。下方with_skill均值/离散度只描述4场景内容断言，不能用于稳定性或统计显著性推断。
- 实际新建CLI回放8项计划/8项通过，全部synthetic；未重新执行160项回归和7反例。
- command -v claude退出码1，无输出：当前PATH未找到claude。未安装、登录或产生模型费用。
- 行为内容检查不等于自动触发验证或导师验收；原始Read工具转录仅在会话，磁盘保留源快照和实际子进程返回。
