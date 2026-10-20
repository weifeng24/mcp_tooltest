# iteration-3：当前Skill行为内容检查

日期：2026-10-19。对象：当前工作树中的 `skills/mcp-eval/`。基线定义：`without_skill`，不是旧版本Skill。

**请求的8次独立并行对照未完成。** 当前会话没有子代理或独立上下文接口，实际独立运行0/8。按skill-creator无子代理降级流程，完成4个主上下文with_skill检查；without_skill均未运行。本目录可以复核内容与本次离线执行，但不能证明Skill增量、速度、稳定性、自动触发效果或导师验收。

## 1. 结果

每场景保留原prompt和expectations，并在 `eval_metadata.json` 展开5个客观断言。正文答案在执行或分析之后首次写入；没有提前预写代理答案，也没有从历史对照复制答案。评分是同一主上下文内联复核，不是盲评。

| 场景 | with_skill（主上下文） | without_skill | 主要核对项 |
|---|---:|---|---|
| 1 offline-replay | 5/5 | 未运行，5项未评分 | 帮助/环境、实际新批次、全部计划分母、synthetic来源、引用及执行范围 |
| 2 incomplete-trace | 5/5 | 未运行，5项未评分 | 否定旧pass、提供方错误与不完整轨迹、unassessed、分母、分析边界 |
| 3 device-readiness | 5/5 | 未运行，5项未评分 | 合成不代表真机、缺身份/定义、--mcp all有执行行为、阻塞与分母、引用 |
| 4 negative-contract | 5/5 | 未运行，5项未评分 | 条件成立判fail、版本/请求/响应/状态证据、不倒改预期、模板边界、分母 |

本轮内容断言没有FAIL；**独立执行与基线隔离两项请求条件未满足**，未隐藏该缺口。没有baseline分数，不能写“两组同分”，也不能写“已证明有增量”或“已证明无增量”。场景提示和公共README本身包含许多规则，只有真正隔离的基线才能检验Skill区分力。四场景单次主上下文自评也不能说明方差或可重复性。

## 2. 实际离线批次

批次ID：

`skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4`

相对本目录位置：

`evidence/replay/skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4/`

实际计划8、执行8、pass8、fail0、unassessed0、未执行0；6正向、2负面，全为synthetic。已对照manifest、逐项结果、summary、report、8个artifacts及录制哈希；8条结果与8条计划逐一对应。详细机器检查为 `logs/replay-artifact-checks.json`。

执行器使用现成CLI，没有执行pytest或重建任何旧批次。回放配置仅在本目录复制并更改run_id/output_dir；源码、现有配置、Skill正文和参考、既有结果及memory均不作为本轮写入目标。

## 3. 产物索引

- [官方静态审阅页](review.html)：由skill-creator自带 `eval-viewer/generate_review.py --static` 生成，展示4份实际答案和断言。没有传入previous-workspace，未加载历史答案。
- [逐项断言与汇总](benchmark.md)、[结构化结果](benchmark.json)、[分析条目](analysis.json)。
- `eval-*/eval_metadata.json`：原场景与本轮断言。
- `eval-*/with_skill/outputs/answer.md`、`access-log.md`：实际主上下文输出与访问记录，输出目录只有这两项。
- `eval-*/with_skill/grading.json`：使用 `text/passed/evidence` 字段，附引用路径、哈希及未满足的独立性条件。
- `eval-*/without_skill/status.json`：未运行原因及每项not_run，不生成虚构答案或0分grading。
- `eval-*/{with_skill,without_skill}/timing.json`：token、耗时均null。
- [上下文边界](context/access-boundary.md)、`context/execution-context.json`、`context/input-snapshots.json`：上下文披露、版本、输入内容与SHA-256。
- `context/answer-hashes.json`：首次评分时的原始答案哈希；完成检查再次核对，答案未按评分结果改写。
- `context/outside-before.json`、`outside-after.json`、`write-boundary-check.json`：本轮目录外Git已跟踪和未忽略文件的前后哈希比较。
- `logs/*.json`：实际子进程argv、cwd、环境覆盖、退出码、stdout/stderr和验证结果。
- `scripts/`：本轮证据收集及评分展示脚本。

## 4. 版本与数据口径

- 会话模型：`openai/gpt-6-astra`；执行方式：OpenCode主上下文降级检查。
- Git HEAD：`5e10eef421602fc468b616680f2bba7da35f659e`，存在既有未提交修改，不能只用HEAD代表被测代码。初始git状态已保留。
- 解释器：项目指定venv，Python 3.10.12；环境查询jsonschema 4.26.0、pytest 9.1.1。没有运行pytest测试集。
- 当前Skill、reference、eval、公共输入及skill-creator文件的SHA-256在 `context/input-snapshots.json`；CLI实际使用的引擎文件哈希和冻结输入在本次manifest。
- 用户提供的新事实为C01—C05已修复、完整回归160passed、8合成回放及7原反例修复验证通过。本轮仅重新执行自己的8项合成回放，未重新执行完整回归或原反例。旧README/memory状态未改写。

官方聚合器的 `calculate_stats` 被程序调用，仅汇总实际内容断言分数。没有调用会将字符数替代token的默认加载路径。无观测数据的时间/token和基线统计在benchmark.json保持null；delta为null，不把缺失填0。

`benchmark-viewer.json` 是只用于官方查看器的显示投影，将整组未知统计对象变为null，避免其模板对null调用 `toFixed()`，或把未知基线渲染成0%。实际分数及原始benchmark.json未改。查看器头部每配置次数可能显示“?”，因为没有统一的已完成次数；实际次数以此页及metadata的with_skill=1/场景、without_skill=0为准。

评分后仅规范了grading中claims.evidence为字符串，并将结构化引用检查放入citation_checks；没有改变任何答案、断言或得分。最终查看器再次由官方生成器生成。

## 5. 无法完成项

1. **8次独立并行执行与无Skill隔离基线**：当前工具列表没有对应接口。并行文件工具不等于并行代理；没有用主上下文冒充基线。
2. **真实自动触发**：`command -v claude` 退出码1，stdout/stderr为空，仅能断言当前PATH未找到命令。没有自动安装、登录、检查账户或发起收费请求。可用性检查不是触发实验。
3. **完整原始代理转录**：没有子代理运行，也没有会话导出工具。命令原始返回完整落盘；Read等原始工具返回仍在主会话，磁盘源快照和人工访问记录不冒充原始代理转录。
4. **用户审阅和导师验收**：没有收到反馈或验收证据；四场景内容得分不能代替这些步骤。静态页已生成，未宣称完成浏览器运行验证。

## 6. 建议同步到fix-log的摘要（本轮未修改fix-log）

> 2026-10-19：使用官方skill-creator的grader/analyzer/schemas对现有4场景进行iteration-3检查，未修改Skill。当前会话缺少独立子代理接口，8次独立对照未完成，改为4次主上下文with_skill检查，内容断言均5/5；without_skill未运行，不能评价增量。独立新批次合成回放8/8，分母8、全部synthetic；引用、产物与来源已核对。token/耗时未知，保持null。当前PATH未找到claude，真实自动触发受阻。官方review.html、原始命令返回、哈希与边界说明已归档。需另补独立行为对照、用户反馈、自动触发和导师验收，不能登记“Skill完整整改验收通过”。用户另提供160项回归和7个原反例修复验证通过，本轮未重跑。
