# Skills Creator 整改记录

Skill：`skills/mcp-eval`。本记录按框架要求保留检查方式、日期、问题、修改与复核证据。

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
