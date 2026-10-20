# 2026-10-16 审查整改记录

状态：**可在本机验证的实现问题已整改并通过回归；真机及最终验收仍未完成。** 本轮没有commit/push、没有修改公司`/data`源码、没有真实设备或收费模型调用。

复审更新（2026-10-19）：本文件记录上轮整改，不能代表所有缺陷已关闭。复审在123项回归通过时另发现5项遗漏；随后已按用户要求修复，160项回归及原7个反例验证通过。当前证据见[新整改记录](remediation-2026-10-19.md)，原[复审报告](reviews/2026-10-19/requirements-review.md)保留历史结论。

最新补充（2026-10-19）：已新增只读注册定义快照采集，末次完整回归为123项。原10-16验证记录保留，新增内容及边界见末节。

## 1. 2026-10-16 验证结果

| 检查 | 实际结果 | 证据 |
|---|---|---|
| 独立Python环境 | 标准venv因ensurepip缺失失败；使用`--without-pip`＋宿主pip安装到venv目录成功，未修改系统已安装包 | README替代步骤；验证JSON中的prefix/dependencies |
| 完整回归 | **114 passed** | [pytest输出](../tests/results/remediation-2026-10-16/verification-20261016T104008355598Z/pytest.txt) |
| CLI | help、dry-run、show-call、checklist、run、rebuild均已离线执行 | [验证目录](../tests/results/remediation-2026-10-16/verification-20261016T104008355598Z/) |
| 合成回放 | 8条计划均通过（6正向＋2负面），独立回读包含在任务验证内 | [报告](../tests/results/replay-smoke-20261016T104010259990Z-6991e571/report.md) |
| 报告重建 | 重建前后summary哈希一致；批次不覆盖旧目录 | [verification.json](../tests/results/remediation-2026-10-16/verification-20261016T104008355598Z/verification.json) |
| Skill结构与脚本 | quick_validate通过；--help和本机环境检查执行通过 | [fix-log](../skills-creator/fix-log.md) |
| Skill有限行为复测 | 两个场景、两组各6/6主要语义检查；未证明增量收益，未测自动触发 | [可视化复测](../skills/mcp-eval-workspace/iteration-2/review.html)、[分析](../skills/mcp-eval-workspace/iteration-2/analysis.md) |

合成回放不构成车端测试结果；historical DeepSeek冒烟仅为真实模型＋模拟工具。本次没有重新调用真实API，Kimi配置仍待核实。

## 2. R01—R11 的处理

| 审查项 | 整改 | 回归/边界 |
|---|---|---|
| R01 配置未被消费 | 改为显式`--toolscall`传完整名称和JSON参数；不覆盖系统配置；无参工具省略空JSON避免arg0回退 | `test_execution_reliability.py`检查命令契约；设备二进制仍待核实，发现/资源动作blocked |
| R02 响应关联错误 | 完整对象解码、多行支持、请求回显排除、请求id关联、冲突拒绝、stdout/stderr保留 | 同测试文件覆盖请求/响应/多行；实际设备日志待采集 |
| R03 模型假通过 | 区分决策和执行；匹配完整工具、参数、业务返回、最终回答及独立回读；达到上限不能通过 | `test_regressions.py`、`test_model_loop.py`、`test_api_smoke.py` |
| R04 缺失证据当零调用 | 增加trace_complete；API/基础设施错误为unassessed；已观察禁止调用保留fail | `test_regressions.py`的provider_error、缺轨迹、后续错误反例 |
| R05 超时未约束执行 | 共享截止时间，剩余预算传入请求/执行；响应返回后、每次下发前重检；轮数与调用数独立限制 | `test_model_reliability.py`；本机超时不声称远端已停止 |
| R06 覆盖旧证据/分母缩小 | 唯一批次、固定manifest、异常逐项记录、中断保存not_run、报告从计划补缺项 | `test_run_integrity.py`；原有回放产物未覆盖 |
| R07 回放折叠与串ID | 每请求队列顺序消费，耗尽blocked；当前与源身份分离；索引后置和L2内嵌调用 | `test_execution_reliability.py`、重复批次测试 |
| R08 预检/采集契约 | 预检全部引用与唯一ID，支持原始result.tools；清单取消危险的“--mcp all只读采集”说法，保持工作目录 | `test_run_integrity.py`、`test_cli.py`；完整发现入口未闭环 |
| R09 证据与用量 | 保存逐轮消息/原始回复/调用ID/执行记录；用量逐轮累加、未知不补零；完整日志、输入与源码哈希 | `test_model_reliability.py`及manifest/artifacts；真实用量/性能待实际运行 |
| R10 断言校验宽松 | 类型化必填参数、业务返回字段、严格JSON相等、Schema合法性检查和唯一工具名 | `test_config.py`、`test_regressions.py`；真实判据仍需业务确认 |
| R11 报告错列 | 分组键管道符转义，补逐项身份/来源/证据 | `test_run_integrity.py`及生成报告 |

R01/R02/R08的错误实现已移除，但完整设备发现和资源采集功能尚未实现，不能标作真机能力完成。当前device模式支持已核对源码的单工具调用，实际设备版本与该契约是否一致仍需上机。

## 3. 测试过程与兼容变化

- 先将审查反例写入回归测试：首次判定组7失败/1通过、模型可靠性5失败、执行/回放7失败、批次完整性6失败；随后针对根因修复。后续新增了嵌套回读回放、远端执行未知状态和业务返回字段反例，均先确认失败再修复。
- 原测试中的成功样例补齐完整轨迹、合法错误消息和执行字段；原来“未知断言算被测失败”等错误预期改为评测器配置错误/unassessed。未通过跳过测试消除问题。
- 单元测试不再覆盖项目固定回放结果；所有测试临时目录在交付区内。
- 数据格式为schema_version=2。旧录制缺少来源/轨迹字段时不会自动升级为可信记录；旧报告仍作为历史保留。
- P06独立覆盖上界30；旧repeat不改变参数。M02/M04需人工复核，不能用自动pass填补。
- API冒烟脚本改为有状态的mock并以verdict决定退出码，补上真实结果与模拟结果的边界。

历史`review-2026-10-16/reproduce.py`用于审查基线快照，不是整改后的回归入口。当前验证入口为`src/tests/`和`scripts/verify_offline.py`。

## 4. 任务与交付缺口的处理

| 缺口 | 本轮处理 | 尚待完成 |
|---|---|---|
| A01 IDE范围差异 | proposal明确模型配置不能替代IDE，保留用户首版取舍 | 导师确认该差异的验收方式；没有新增L3实现 |
| A02 真实工具集与判据 | 建立候选工具目录，撤回“已覆盖8服务”，补具体回读/上界/错误类型 | 实际工具定义、确认人、状态恢复与设备绑定 |
| A03 量化目标 | 固定分母、逐轮用量、分组时延与实验控制方案 | 正式真机批次、基线及对比数据 |
| A04 Skill证据 | 补help、CRITICAL、自由度、正反触发设计；复测输出/评分/访问说明隔离保存 | 自动触发、其余场景、用户反馈及导师认可；引用编号精度仍需复核 |
| A05 进度过度声明 | 重写todo/midterm/README，明确离线完成与真机待验证 | 中期正式检查、完整结题与答辩材料 |

## 5. 下一步的硬条件

1. 10-19/20核对设备二进制及`--toolscall`输出，先做一条真实读取与一条可恢复设置。
2. 取得完整工具定义，冻结名称、参数、返回字段、错误判据和恢复方法；发现/资源接口仍缺失则明确延期或范围调整。
3. 补真实至少5＋2和有控制变量的对比；第二模型接入未经验证时保留未执行。
4. 补齐Skill自动触发/行为证据、人工反馈、导师验收及最终演示。

本轮结论只限上述本机整改与验证，不宣称已完成全部课题产出或公司验收。

## 6. 2026-10-19：补齐注册目录的只读采集

- 核实Ark源码dump配置及RouteManager导出完整原始定义的实现，新增`capture-catalog`。
- 按明确服务范围读取现有tools/resources文件，保存原文、stderr、哈希、每文件状态与名称别名；不修改设备配置、不执行ToolsCall。
- 修正对旧--svcmap文档的依赖：当前实现返回逻辑名，不能猜数字serviceId。已有前缀保留，无前缀使用服务名别名并保留待真机核实标记。
- 快照显式标记新鲜度未知、非原子采集、没有测试实时tools/list和资源值读取。目录快照可以支持工具集整理和L2输入准备，但不会让P01/P05的实时device动作自动通过。
- 本机NDK存在，但所选Ark树的对应SDK路径未找到；Dora库与目标设备是否匹配未知。实时客户端探针仍需先确认实际项目/SDK，不能跨树推定可用。

末次独立环境验证：[verification-20261019T080940766650Z](../tests/results/remediation-2026-10-16/verification-20261019T080940766650Z/verification.json)。**123项测试通过；合成回放8/8；报告重建一致；采集dry-run显示只读文件计划、executed=0。**

操作与源码依据见[catalog-capture.md](catalog-capture.md)。真实设备文件存在性、权限、版本、新鲜度和别名执行仍待验证。下一步需确认借用车机属于Ark、Dora或其他项目。
