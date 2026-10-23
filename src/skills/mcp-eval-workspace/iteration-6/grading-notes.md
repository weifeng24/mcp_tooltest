# iteration-6 独立评分与断言评议

评分日期：2026-10-23。评分单位为冻结断言，每条仅通过或不通过，不给部分分。

同日补充核查：场景1两组均存在未与执行日志关联的较早完成态批次，详见第8节。分数保持不变，但撤回“每组总共只执行一次”的过程认可；场景1分数仅针对答案明确引用的批次。

## 1. 总分与逐例结果

| 条件 | 通过 | 失败 | 总数 | 断言通过率 | 五项全通过的场景 |
|---|---:|---:|---:|---:|---:|
| `with_skill` | 35 | 0 | 35 | 100.00% | 7/7 |
| `without_skill`（无目标 Skill） | 32 | 3 | 35 | 91.43% | 4/7 |

两组相差 3 条断言，即 8.57 个百分点。差异是两次未执行帮助命令，以及一次配置初始状态/修改过程无法核验；本轮没有观察到两组在其余已评分业务结论上的差异。不能把这一差值解释为稳定增益。

| 场景 | 类型 | with_skill | without_skill | 不通过项 | 评分文件 |
|---|---|---:|---:|---|---|
| 1 `offline-replay` | 正向 | 5/5 | 4/5 | 无目标 Skill 第4条 | [with](eval-1-offline-replay/with_skill/grading.json) / [without](eval-1-offline-replay/without_skill/grading.json) |
| 2 `missing-evidence` | 负面 | 5/5 | 5/5 | 无 | [with](eval-2-missing-evidence/with_skill/grading.json) / [without](eval-2-missing-evidence/without_skill/grading.json) |
| 3 `device-not-ready` | 负面 | 5/5 | 5/5 | 无 | [with](eval-3-device-not-ready/with_skill/grading.json) / [without](eval-3-device-not-ready/without_skill/grading.json) |
| 4 `unexpected-success` | 正向 | 5/5 | 5/5 | 无 | [with](eval-4-unexpected-success/with_skill/grading.json) / [without](eval-4-unexpected-success/without_skill/grading.json) |
| 5 `report-interpretation` | 正向 | 5/5 | 5/5 | 无 | [with](eval-5-report-interpretation/with_skill/grading.json) / [without](eval-5-report-interpretation/without_skill/grading.json) |
| 6 `frozen-report-rebuild` | 正向 | 5/5 | 4/5 | 无目标 Skill 第5条 | [with](eval-6-frozen-report-rebuild/with_skill/grading.json) / [without](eval-6-frozen-report-rebuild/without_skill/grading.json) |
| 7 `preflight-plan` | 正向 | 5/5 | 4/5 | 无目标 Skill 第1条 | [with](eval-7-preflight-plan/with_skill/grading.json) / [without](eval-7-preflight-plan/without_skill/grading.json) |

正向断言：25/25 对 22/25；负面断言：两组均 10/10。合计完成14个指定评分单元（7场景×2条件）的70条评分，67条通过、3条不通过。评分单元数不等于底层命令执行总次数；此处的“正向/负面”采用 `evals-frozen.json` 的场景分类，不是内部 L1 用例的分类。

## 2. 评分方法与已核查证据

- 先阅读指定 `agents/grader.md`，再完整读取 `evals-frozen.json`；14 份 `grading.json` 保留每组原始五条 expectations 的文本和顺序。
- 完整阅读全部 14 份 `outputs/answer.md` 及各组访问日志。场景3、4、6的部分 `access-log.md` 位于 mode 根目录，其他位于 outputs；没有因日志位置不同遗漏评分依据。
- 对要求执行的条目核对实际命令记录、现存 stdout/stderr、已有退出码及生成内容。命令帮助须有实际调用证据；阅读 README、源码或看到 `--help` 字样不算执行帮助。生成清单中的 adb 指令和 dry-run JSON 中的远端 argv 不算实际调用。
- 对场景1两组的新批次，以及场景5、6共四份指定批次，独立静态解析 manifest/results/summary/report 和每批8份 artifact，核对计划身份、计数、来源、文件对应关系；未重跑产品或任何执行脚本。
- 场景1答案引用的新批次分别为 `replay-smoke-20261023T073041689863Z-ee5b5d7f`、`replay-smoke-20261023T073015149014Z-a8a1fdbc`，两者均为8 pass，均不同于 `execution-contract.json:106` 的 bootstrap 批次。两组还各保存另一套较早的完成态产物，初评分未核对其与命令的关联；本次补核查已登记该遗漏，不再将引用批次等同于副本全部执行历史。
- 场景5、6均为固定计划8项、6 pass/1 fail/1 unassessed，结果逐项与 artifact 相同；manifest/results/冻结录制的当前哈希与准备阶段清单一致。场景6的前后哈希也独立复核：with 29个受检文件相同，without 35个受检文件中仅允许的 summary/report 两项变化，33个受保护文件相同。
- 场景2、4的原 fixture 当前字节与对应初始哈希相同；场景7两组当前配置仅序列号不同于当前主配置。后者只验证当前状态，不证明历史修改过程。
- 14份评测器副本与 `engine-hashes.json` 匹配；7份 with_skill 副本、`skill-snapshot` 和当前目标 Skill 与 `skill-hashes.json` 匹配。正文 `SKILL.md` 的 SHA-256 为 `2ea3176ad2b88d38168aded0f6b50f38de92d996ac5d9c95e5f06ca8a9111b9b`。结合 `execution-contract.json:9-12`，本轮定位为稳定 Skill 的覆盖扩展，不表述为正文修订后的增益验证。
- 无法核验按不通过处理；复合断言任一必要部分缺证据，整项不通过。未因答案长度、额外源码阅读、额外本地判定核验或额外问题分析加分。
- `timing.json:2-5` 在14组中均为 null 计量值及占位原因，已原样纳入评分文件；未发现独立 metrics.json。token、总耗时和成本未知，不填零、不估算。

## 3. 失败项

### F1：场景1 without_skill，第4条

冻结断言：**执行前查看命令帮助并保存输出依据**。

`eval-1-offline-replay/without_skill/outputs/access-log.md:71-122` 已保存的终端清单列出目录检查、正式 run、归档、diff 和 sha256sum；`:38-42` 记录阅读 CLI 实现等源码。没有可核验的 `--help` 调用或帮助输出，不能将阅读实现补算为帮助执行。补核查发现该日志未覆盖较早批次，因此此处限定为“已保存清单未证明帮助调用”，不把该清单称为完整命令历史。

实际回放及其 8/8 结果、新批次读取和 synthetic 来源解释均有证据，其他四条通过。

### F2：场景6 without_skill，第5条

冻结断言：**执行前查看帮助，并引用实际summary/report路径**。

`eval-6-frozen-report-rebuild/without_skill/access-log.md:34-51` 与 `outputs/check_rebuild.py:61-69` 显示直接调用一次 rebuild，没有帮助调用或帮助输出。`outputs/answer.md:7-8` 引用的实际报告路径正确，但复合断言前半部分未满足，整项不通过。

实际 rebuild、6/1/1 统计、冻结输入及哈希保留均可核验，不能把流程扣分解释为报告重建未完成。

### F3：场景7 without_skill，第1条

冻结断言：**仅在本组副本填写演练序列号，实际生成checklist与capture-catalog --dry-run输出**。

配置初始状态和填写过程缺少足够证据，判不通过。两项输出确实存在，单独满足的后续断言仍正常评分，详见下一节。

## 4. 重大证据疑点：场景7的初始状态与修改过程

### 已知且可复核

1. `../prepare_iteration6.py:80-95` 为每组建立独立副本，`:85-86` 复制主 `configs`；没有场景7预填序列号分支。`:95` 的初始哈希只覆盖 fixtures，不覆盖配置。
2. 当前主配置 `../../../configs/servers/ark_mcp_service.json:5` 的序列号为空；准备阶段生成的本组 `sandbox/fixtures/report-batch/manifest.json:102-107` 也保存空 server 序列号。它们支持准备来源为空的疑点，但不能代替本组准备完成时的完整配置快照。
3. `eval-7-preflight-plan/without_skill/outputs/answer.md:7`、`outputs/access-log.md:7,55`、`outputs/commands.json:35-38` 均声称“初读已为演练值，未编辑”。这些是同一次执行的过程说明，没有原始初读转录、准备完成快照或修改事件提供独立衔接。
4. 该组当前 `sandbox/configs/servers/ark_mcp_service.json:5` 确为 `SYNTHETIC-SERIAL-NOT-A-DEVICE`。当前值及运行后的复读不能证明该值何时、如何形成，也不能证明填写操作仅影响本组。
5. with_skill 组有独立 `outputs/server-before.json:5`、前后哈希、`10-server-diff.stdout.txt:7-8` 及对应修改记录，足以支持该组评分；这些文件不能替代 without_skill 的缺失过程证据。

### 判定与归因边界

- 保留“准备来源为空”与“自述初读已为演练值”之间的证据断点；第1条不通过，相关 process claim 标为 `verified=false`。
- 不将缺证据直接认定为造假、跨组修改或共享文件；不推断是谁、何时修改，也不把两组当前值相同当作共享写入证据。
- `without_skill/outputs/commands.json:19-32` 保存两条实际产品命令及退出码0，`checklist.stdout.md:5-6` 保存合成序列号，`catalog-plan.stdout.json:1-27` 保存限定服务的两个文件计划及 `executed=0`。这部分证据可以独立支持第2—5条。
- 本项是评测证据完整性问题，不是新发现的 MCP 产品缺陷。本轮未确认其他新增重大产品问题。

## 5. 冻结断言的区分度与覆盖盲区

本节只评议本轮断言，不修改冻结输入或追加扣分标准。

| 位置 | 已观察到的区分度/盲区 | 后续评测可采用的改进 |
|---|---|---|
| 场景1第4条、场景6第5条 | 两项实际区分了是否执行帮助，但两组最终回放/重建结果、输入完整性和来源解释均正确。差值主要反映流程遵循，尚未证明任务效果改善 | 选取 CLI 参数或版本确有歧义的场景，检查帮助内容是否用于正确构造命令；分别报告流程分和任务结果，不以更长答案替代效果 |
| 场景1第1条及批次选择 | 两组均存在答案和命令日志未关联的较早完成态批次；“实际执行一次并引用”未明确检验整个副本恰好执行一次、所有批次披露或首次尝试结果 | 后续预先冻结批次选择规则、初始结果目录快照及命令到批次的独立关联记录；完整保存额外批次，不用事后删除或选择产物改变分母 |
| 场景7第1条 | 配置转换、写入隔离、checklist 和 dry-run 四件事合在一条，最终配置状态无法证明过程；准备脚本缺少 server 初始哈希使断言难以完整核验 | 从独立准备阶段冻结全部必要输入及解析后路径，保存原始初读/写入事件；将转换、隔离和产物拆成可定位的检查。新规则只能用于后续轮次 |
| 场景2 | 题面直接给出 provider_error、不完整轨迹及旧错误判定；固定拒绝旧 pass 即可能得到高分，未检验正当不调用与已观察违规的区别 | 成对加入完整正常不调用、禁止调用决策已出现后再报错、轨迹缺失三类记录，要求分别判 pass/fail/unassessed；避免形成“凡报错都无法判断”的错误泛化 |
| 场景3、7 | 缺设备号、缺真实目录或离线演练边界在题面明确提示；没有验证自动识别隐蔽就绪问题。禁止外部调用主要依赖执行者保存的命令日志和已知分支 | 加入字段齐全但设备身份/二进制不匹配、只含工具名摘要等近似情景；由独立包装器保存命令、返回码、子进程/网络事件及写入范围，增强负面行为证据 |
| 场景4 | 只验证“建议回读/恢复”的分析文字，没有检验实际状态分支或恢复失败后的行为 | 使用离线模拟回读为40/30/原值、回读失败、恢复方式未确认等分支；区分建议覆盖与真实设备验证 |
| 场景5、6 | 简单固定8项、各一次、无模型；P05仍有占位行。未覆盖整条结果丢失、重复/计划外身份、多模型、多重复次数的统计 | 预先构造相应变体，以 manifest 的唯一计划身份核验分母和统计，不只核对摘要数字 |
| 场景6第3条 | 当前配置/用例与冻结版本一致，正确输出本身无法区分是否误用当前版本；哈希不变只能证明没有改写原文件 | 预置当前用例/配置与冻结版本不同，验证重建仍消费原批次；同时保留 manifest/results 哈希检查。本轮正式 rebuild 分支确实读取冻结输入，所以按现有证据通过 |
| 所有来源类断言 | synthetic 标签及边界解释有必要，但标签正确不等于来源链完整，不能证明真实执行、自动触发、稳定收益或客户端兼容性 | 增加来源链一致性和实际边界断言；将功能行为、自动触发、真实系统验证及业务收益分别取证 |

### 夹具来源差异：当前断言未完整覆盖

`../prepare_iteration6.py:39-63` 先复制8项全通过回放，再人工修改 N02 响应与 P05 执行证据，重写 results/artifacts/report；原 manifest 执行计数及 recording-input 沿用。由此：

- report/rebuild 两批的 `manifest.attempted_items=8`，而当前结果为7条 completed、P05 not_run；不能将元数据读作8项都完成。
- 原 recording-input 的 N02 是预期错误，P05有资源响应；派生 results 的 N02为成功响应导致 fail，P05为空响应导致 unassessed。`eval-5-report-interpretation/without_skill/outputs/check-report.stdout.json:388-442` 具体保存了差异。
- 这是已标注人工构造的 fixture 设计事实，不是本轮执行者制造的真实设备缺陷或新的回放器故障。固定断言未要求完整比较这条来源链；主动揭示差异不额外加分，未逐项描述差异也不追加扣分。
- 这些结果支持“解读/重建人工混合结果”，不支持“原录制未经变更直接回放得到6/1/1”。未来应把这种区别纳入明确断言，避免仅靠来源标签就获得过宽结论。

## 6. 对照实验与结论边界

- 两组均按上层规则读取根索引与记忆，含历史回归、旧 Skill 对照分数及项目提示；部分组还读取 DECISIONS 或上层 README。例见场景1两组 `outputs/access-log.md:13-19`、场景7两组的上下文披露。
- 两组均可能加载通用流程 Skill，实际日志显示使用了 using-agent-skills、verification-before-completion 等，with 多组还加载 skill-creator，without 场景4加载 debugging-and-error-recovery。`without_skill` 的准确含义是“未加载目标 mcp-eval Skill”，不是“无任何 Skill”。通用上下文也未完全统一，无法剥离其影响。
- 评分者知道组标签和用户提示的重点疑点，因此评分本身也不是盲评。所有判定仍以冻结断言和可核查文件为依据，不把用户提示替代文件证据。
- `execution-contract.json:9-13` 的 `runs_per_configuration=1` 是实验安排，不是实际命令次数审计。场景1额外批次尚未解释，不能声称“各组实际只执行一次”或“没有重复运行”，也不能将这些未关联产物作为受控重复实验。独立可写副本非操作系统沙箱且可能共享历史；7个场景与35条相关断言不构成35个独立重复实验，没有随机化或稳定性估计，不能声称统计显著、稳定增益或可泛化收益。
- 本轮是5正向＋2负面场景的稳定 Skill 覆盖扩展。with_skill 35/35仅说明这批已保存执行满足冻结断言，不代表自动触发验证、真机/真实API或IDE评测、导师认可及正式验收完成。
- 自动触发未验证，token与耗时未知；没有效率、成本或速度提升证据。
- 现有访问日志并非完整的宿主原始转录或操作系统级追踪。未连接设备/API的判定依所存命令、实际输出和已核对程序分支作出，不能外推为独立审计已覆盖所有潜在外部访问。

## 7. 评分交付与完整性

- 本评分只新增14份 mode 级 `grading.json` 与本文件；没有修改答案、输入、执行输出、主项目或中央记忆。
- 评分期间只进行文件阅读、JSON统计/身份核对及哈希计算；没有执行产品、fixtures、准备脚本、原执行者辅助脚本、修复或重新评测流程。
- 初次评分写入前后均核查当时 iteration-6 原有文件1399份（排除评分文件名）；按“相对路径→SHA-256”字典排序序列化计算的内容总摘要均为 `f56995a6f11bb171b15ce38ed87249bc16e370d847a392116ec7ca2b734e9844`。这是初次评分时的内容保全记录，不证明执行过程完整，也不作为主会话后续新增汇总文件后的目录数量断言。
- 已静态验证14份评分JSON可解析、70条断言文本/顺序与冻结文件完全一致、布尔结果和汇总相符、timing字段与原文件一致，以及本文件14个评分链接有效。该验证没有导入或执行产品代码。
- 每份 grading.json 的证据路径相对该 mode 目录；本文件的路径相对 iteration-6 根目录。相邻源码/主配置引用保留明确的 `../` 层级，用于定位证据，未将其列入可写范围。

## 8. 补充核查：场景1的额外较早批次

### 8.1 目录与完成态产物

以下批次均位于 `eval-1-offline-replay/<条件>/sandbox/tests/results/<批次ID>/`，全部保留。

| 条件 | 本轮评分使用的答案引用批次 | 额外较早批次 | 较早记录的 timestamp |
|---|---|---|---|
| with_skill | `replay-smoke-20261023T073041689863Z-ee5b5d7f` | `replay-smoke-20261023T072335541722Z-d3d3c6a0` | `2026-10-23T15:23:35+08:00` |
| without_skill | `replay-smoke-20261023T073015149014Z-a8a1fdbc` | `replay-smoke-20261023T072249272703Z-4501ac0a` | `2026-10-23T15:22:49+08:00` |

已对四批文件独立静态核对：每批13个文件，包括 manifest、results、summary、report、冻结录制及8份 artifact。较早两批不是空目录或占位报告：

- 各自 `manifest.json:3-5,346-347` 保存不同于引用批次及 bootstrap 的 run_id、`state=finished`、`recorded_items=8`、`attempted_items=8`；计划8项的身份与结果一一对应。
- 各自 `results.jsonl:1-8` 均为 `completed/pass`、`source_type=synthetic`、`channel=replay`、`trace_complete=true`；8份 artifact 与对应结果对象相等。P02/P03/P06保留22/16/30的合成后置回读。
- 各自 `summary.json:4-11,45-49` 和 `report.md:3,11-28` 均为计划8、通过8、失败0、无法判断0，与实际记录相符。
- 录制 SHA-256 与各自 manifest 及本组输入录制一致；manifest 的14个评测器源码哈希与冻结清单相同。以上证明额外存在内容完整、一致的完成态回放记录，不只是目录名不同。

### 8.2 准备脚本不能解释这些副本内批次

`../prepare_iteration6.py:11,39-42` 在主交付区 `ROOT` 执行 bootstrap，再将结果复制到 `iteration-6/input-snapshot/fixtures/report-batch`；`:80-95` 建立各组副本时只复制 `tests/cases`，以及源码、配置、录制、文档和 fixtures，没有复制或创建 `sandbox/tests/results` 的分支。bootstrap 的 run_id 另见 `execution-contract.json:106`，与上述四个 run_id 均不同。

因此不能把较早批次解释成准备脚本正常复制的 sandbox 结果，也不能把它们算作同一 bootstrap 的原样归档。没有关于其他创建行为的证据时，不进一步推断生成主体或原因。

### 8.3 能否关联真实执行命令

- **with_skill：** `outputs/05-replay.execution.json:2-18` 与 `outputs/05-replay.stdout.txt:93-104` 能关联到答案引用的073041批次；`outputs/access-log.md:89-99,115-125` 也只对应该批次。`outputs/00-locations.stdout.txt:4` 在所列正式命令前已显示 `tests/results` 存在，目录时间显示15:23，但它没有列出批次名，不能定位早期启动命令。
- **without_skill：** `outputs/access-log.md:88-95` 与 `outputs/01-replay.stdout.log:93-104` 能关联到答案引用的073015批次；`:65` 明确没有枚举其他批次。`outputs/00-directory.stdout.log:8` 也已显示 `tests/results` 存在，目录时间显示15:22，但不能据此识别执行者或具体启动事件。
- 两组 `outputs/` 内检索完整较早批次ID及短ID均未找到匹配；现存命令清单、stdout及返回码记录没有与它们建立关联。`task-receipts.json:8-9` 仅记录任务级 completed 与 task_id，没有批次级命令或进程记录，不能补足这条链。
- **结论：** 文件层面有另外两套独立完成态回放产物；进程层面无法核验它们对应的启动命令、退出码、调用主体、是否属于同一次代理任务或是否重试。实际命令总次数仍未核实。既不能把这些产物忽略为“没有额外执行证据”，也不能擅自将四个目录转换成已审计的四次进程调用。

### 8.4 对“只执行一次”说法的处理

- with_skill 的 `outputs/answer.md:5` 称1次正式评测，`outputs/access-log.md:144` 称“唯一正式 run”；without_skill 的 `outputs/answer.md:29` 明确“只执行了这一次评测”，`outputs/access-log.md:85,95` 称唯一、共1次。
- 若这些表述仅描述答案引用的那一次命令，其执行和结果有证据；若作为整个副本总执行次数及过程完整性的声明，则无法与额外完成态产物相互解释。已在两份 grading.json 的 `claims` 中将“总共只有一次”的 process claim 标为 `verified=false`，并增加 `grading_scope.total_execution_count_verified=false`。
- 原答案和执行日志保留原文。撤回初评分中“唯一正式 run”的认可；初评分只检查了答案引用批次，未覆盖所有结果目录与日志的关联，这是评分检查范围的遗漏，不以当时哈希保全代替过程核验。
- 不推测是谁创建、是否由 harness 重试、是否属于其他上下文，也不据此指认伪造或跨组写入。

### 8.5 冻结五条断言是否改变

本次按用户明确限定，仅对答案引用的批次评分；不改断言原文、不选择较早批次替换、不合并成16项分母、不新增评分单元。

| 冻结断言 | 补核查后的裁定 |
|---|---|
| 实际执行一次回放并引用本组新批次路径 | 两组仍通过。引用批次有命令、输出及产物关联，满足实际执行一批的要求。原文未明确“整个副本总共只能执行一次”或“全部批次均须关联”；额外批次的过程疑点另记为未验证 claim，不能事后追加总次数扣分项 |
| 准确报告计划8、通过8、失败0、无法判断0 | 两组仍通过。计数针对各自明确引用批次，经独立复核一致；没有将额外批次删去后重算或合并分母 |
| 明确synthetic来源，不作真机结论 | 两组仍通过。答案和引用批次来源相符；额外两批也为synthetic，但不据此证明其启动过程 |
| 执行前查看命令帮助并保存输出依据 | with仍通过、without仍不通过。with现有顺序记录支持引用批次前的帮助；不外推为较早批次也查看过帮助。without没有可核验的帮助调用，未知早期过程不能补算通过 |
| 读取本次manifest、results及summary/report，而不是旧固定目录 | 两组仍通过。现存读取记录和答案均指向各自引用的新批次，未以较早目录替代。本条未要求审计整个副本的所有结果目录 |

场景1维持5/5对4/5；总分维持35/35对32/35。分数覆盖引用批次的五项行为，不代表原答案的每一条过程声明均真实或完整。

### 8.6 新增方法限制与保全范围

- 当前只能汇报“指定批次的评分结果”，不能汇报“首次尝试成绩”“每组总共只执行一次”或已核实的总命令数。
- `runs_per_configuration=1` 只能保留为计划安排；额外批次缺乏命令关联和任务归属，无法作为受控重复观测，也不能用来声称稳定性改善。原小样本、非盲评、通用Skill上下文及未知token/耗时限制继续成立。
- 未来若需核验一次性执行，应预先冻结结果目录初态、批次选择规则和每次命令/返回码/批次ID的独立关联；本轮不以新增规则追溯扣分，也不删除未解释产物改变统计。
- 本次补核查只更新本文件与场景1两份 grading.json。主会话正在维护的 artifact-checks、benchmark 等汇总未作为早期执行命令的替代证据，也未由本评分者修改。
- 补核查写入前，对场景1两组除 grading.json 外的全部原文件建立内容摘要：with 147份，摘要 `5ae82329cfcc92ed5d6bd5786d9f58d55432ed4914344f4b54568f195d6fc3fa`；without 143份，摘要 `856ed71c7ffb4441479b218b2e9c0dec8da9076948e1c28e14edfc341625f1e9`。范围包含两个较早批次的全部26份文件、答案、日志和引用批次产物。
- 补核查写入后再次复算，两组原文件数量和摘要均相同；70条冻结断言文本、结果布尔值与汇总再次核对通过，总分未变，两项“总共仅一次”的过程声明均为未验证。本文件14个评分链接有效。
