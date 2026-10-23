# Skills Creator 整改记录

Skill：`skills/mcp-eval`。本记录按框架要求保留检查方式、日期、问题、修改与复核证据。

**当前状态（2026-10-23）：结构检查、当前版本5正向＋2负面完整行为集验证已有证据；自动触发、用户反馈和导师认可未完成。各轮范围与限制分别保留，不把本轮评分或结构检查当完整验收。**

## 检查与整改条目

### 2026-10-16 第 1 轮：结构与可用性检查

- 检查方式：`skill-creator/scripts/quick_validate.py`；`check_env.sh` 实机执行。
- 结果：结构校验通过（"Skill is valid!"）；环境检查脚本输出符合预期（依赖 OK、密钥未设置时 WARN 且不显示值）。

### 2026-10-16 第 2 轮：触发与效果评测（3 用例 × 有/无 Skill 对照）

- 检查方式：定义 `evals/evals.json`（3 个真实用户场景），并行运行"有 Skill"与"无 Skill 基线"代理，按断言评级。
- 结果：3 用例双方均全部通过。
- 发现 F1：断言在本轮不具区分度——README、报告模板和判定器注释已包含相同纪律，基线代理自行探索也能答对。Skill 的实际价值在**触发纪律与流程收敛**（有 Skill 的代理直接执行正确命令、无需探索；且以 check_env.sh 开头）。
- 处理：保留现有内容（无事实错误），在 fix-log 如实记录该局限，不夸大 Skill 的增量效果。

### 2026-10-16 第 3 轮：区分度评测（负面发现场景）

- 检查方式：新增场景"N02 越界参数实际成功，如何判定与写报告"，双面对照。
- 结果：双方均正确判定 fail 并识别为有效评测发现。
- 发现 F2（真实 bug，由基线代理实测发现）：`mcp_eval checklist` 生成的批次命令缺 `PYTHONPATH=src` 前缀，照抄执行会失败。
- 修改：`runner.py` 上机清单中 L1/L2 批次命令补前缀；L2 步骤补密钥提醒。
- 复核：`PYTHONPATH=src python3 -m mcp_eval checklist` 输出已含完整前缀；72 项单测回归通过。

### 待执行

- 官方 Skills Creator 完整检查（description 触发优化依赖 claude CLI，本机不可用）；提交导师 review 前在具备条件的环境补做，或按导师指定方式检查。
- description 正反触发用例（should/should-not-trigger）已在 SKILL.md description 中以文字明确，量化触发评测待补。

## 导师评审

尚未提交评审，未获得评审结论。

## 2026-10-16 整改复测（iteration-2）

### 已修订内容

- SKILL.md补充CRITICAL证据规则、执行与解释自由度、先--help再黑盒执行要求。
- 明确不能将API错误/缺失轨迹视为正确不调用；不能将--mcp all当只读发现；device标签须结合来源证据。
- check_env.sh实现--help、非法参数处理、可选解释器；只检查本机依赖，不声称设备/API已就绪。
- evals.json补齐4个场景；另提供5正向＋5反向的触发设计。触发设计尚未在真实自动选择环境测量。

### 本轮实际检查

| 检查 | 结果与来源 |
|---|---|
| quick_validate | 使用当前安装的 skill-creator/scripts/quick_validate.py，输出 Skill is valid!；其能力仅为元数据/结构检查 |
| 脚本黑盒 | --help及独立venv解释器下的环境检查运行通过，未打印密钥 |
| 两场景行为对照 | eval2（缺失证据）、eval3（设备准备）分别有/无Skill；输出目录隔离，基线禁止读取Skill且访问清单已检查 |
| 主要语义评分 | 两组各6/6；不证明增量效果，更不能推导自动触发率或速度优势 |
| 时长与token | Task返回没有提供，记录null；没有填0或估算 |
| 已知输出局限 | with_skill的eval2引用了不存在的第9条编号，主体判定正确；保留原输出，引用精度仍需人工反馈 |

证据入口：[iteration-2](../skills/mcp-eval-workspace/iteration-2/README.md)、[benchmark.json](../skills/mcp-eval-workspace/iteration-2/benchmark.json)、[静态复核页面](../skills/mcp-eval-workspace/iteration-2/review.html)。原始回答、访问说明、grading和timing分别位于对应运行目录；context-snapshot保存当时读取上下文。

### 对旧记录的更正

旧“无Skill”组读取过Skill资料，因此不作为干净的无Skill对照；旧并行运行写同一回放目录，证据不隔离。旧“流程更快”的结论缺少时长数据。旧复核条目中的72项数字与当时75项输出不一致，不能作为准确测试计数。本次程序整改末次完整测试为114项，详见[整改记录](../docs/remediation.md)。

框架没有规定只有某个CLI才可完成所有检查。下一步应明确导师认可的检查方式并补齐自动触发、剩余行为场景和人工反馈；在此之前T09保持部分完成。

## 2026-10-19 增补

Skill正文增加注册定义快照采集的入口与边界，强调它不等同于实时发现/资源读取。对应CLI及数据契约已纳入123项离线回归；这不是新的Skill自动触发/行为对照结果，既有两场景复测仍按10-16快照解释。

## 2026-10-19/20：iteration-3—5

### iteration-3：单上下文降级检查

验证代理没有子代理工具，完成4场景自检20/20，并明确without_skill未运行。该轮不是独立对照，不能引用为有/无Skill增益。原始输出、实际合成回放和限制保存在[iteration-3](../skills/mcp-eval-workspace/iteration-3/README.md)。

### iteration-4：四场景有限独立对照

主会话实际启动8个独立上下文，4场景分别有/无目标Skill。两个回放使用不同新批次，均8/8且来源synthetic。答案与访问记录独立保存，逐项评分有证据引用。

| 场景 | 有Skill | 无Skill | 发现 |
|---|---:|---:|---|
| 离线回放 | 5/5 | 4/5 | 无Skill未先执行帮助 |
| 历史错误及缺失轨迹 | 5/5 | 4/5 | 无Skill保留原记录，但未明确计划分母 |
| 真机准备 | 5/5 | 5/5 | 两组均正确识别设备/工具输入及非只读命令限制 |
| 越界输入被接受 | 4/5 | 4/5 | 两组均正确判fail，但漏掉回读与现场恢复建议 |

总计19/20与17/20。基线未读取目标Skill或其他组答案，但场景1—3的基线按项目规则读到了历史摘要；不能声称完全盲评。每场景每组仅一次，耗时/token为null，不能证明稳定增益或速度优势。证据与官方页面见[iteration-4](../skills/mcp-eval-workspace/iteration-4/README.md)。

### iteration-5：遗漏整改与局部复测

- 问题：失败判定正确，但未给出副作用状态核对及恢复方向。
- 修改：Skill正文与排错表增加通用的“判定与状态分开、独立回读、按确认方法恢复”规则，并解释中断检查点与尝试项数。
- 验证：相同场景4及冻结断言，新版5/5，旧版快照3/5；旧版还未明确保留规范/工具版本。原输出保留，结果见[iteration-5](../skills/mcp-eval-workspace/iteration-5/README.md)。
- 限制：新版仅对受影响场景做局部复测，没有重新运行全部四场景。不能将局部5/5与旧轮次结果拼接成新版整套通过。

### 环境与后续

当前Skill的quick_validate及环境脚本帮助/自检通过。2026-10-20再次检查`command -v claude`未找到命令，未安装或登录；现有自动触发评测脚本尚不能执行。框架要求的触发精度、用户反馈、导师接受的Creator检查方式和整改认可仍待闭环。

## 2026-10-23：公司答辩模板对照（未新增评测执行）

用户确认新HTML模板由公司提供。模板04明确要求展示Skill至少5条正向＋2条负面行为用例及实际输入输出；当前`evals/evals.json`的4场景不足，需扩充并以同一最终版本完整验证。已有5＋5触发设计、代码回归数量和L1工具用例不能抵算Skill行为案例。现有评分/限制继续按各轮记录解释，详见[模板分析](../docs/defense-template-analysis.md)。

## 2026-10-23：iteration-6补齐本地行为验证

- 依据：用户要求完成本地可完成部分。冻结当前正文、脚本、参考资料和7场景输入，正文不变；5正向为回放、异常分析、报告解读、重建、预检计划，2负面为缺证据与设备未就绪。
- 执行：14个有/无目标Skill独立上下文，独立评分者逐条核对回答、原始输出和产物；主会话另校验输入与源码哈希、批次统计和报告生成。
- 结果：有Skill35/35，7场景均5/5；无目标Skill32/35。两项未先查看帮助、一项配置修改过程证据不足，未证明核心业务结论或效率增益。
- 结构：官方quick_validate通过；脚本帮助/本机环境检查已有实际输出。官方查看器已生成，可查看14份输出与Benchmark。
- 限制：上层索引/记忆与通用Skill影响无法剥离，非完全盲评；worker模型ID、token与总时长未知。场景1另有未关联命令日志的较早批次，不能声称总共仅执行一次；基线场景7初始配置至修改过程仍有证据断点。原始产物全部保留，不用补写日志掩盖。
- 入口：[iteration-6](../skills/mcp-eval-workspace/iteration-6/README.md)、[独立评分说明](../skills/mcp-eval-workspace/iteration-6/grading-notes.md)、[官方复核页面](../skills/mcp-eval-workspace/iteration-6/review.html)。

### 自动触发与反馈

已新增10正向＋10近似反向查询和只读环境检查；当前检查为`blocked_missing_claude_cli`，授权未核验，没有触发率结果。准备材料见[trigger-readiness.md](../skills/mcp-eval-workspace/trigger-readiness.md)。官方静态查看器可查看输出/评分；直接以file方式打开时尝试本地反馈API的console警告已记录，反馈提交使用其下载回退路径。用户反馈及导师review尚未取得。
