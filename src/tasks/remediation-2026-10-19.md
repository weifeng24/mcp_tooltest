# 10-19复审整改执行计划

**目标：**修复C01—C05，保存可重复验证证据，并推进无需真机的交付准备。

**设计：**保留现有配置、通道和记录结构。判定器统一检查执行成功条件；执行器通过可选检查点回调保存部分记录。真实设备、模型及导师验收结论依赖实际证据。

**技术：**Python 3.10、pytest、jsonschema；既有项目内venv。

**依据：**[复审报告](../docs/reviews/2026-10-19/requirements-review.md)、[设计](../docs/design.md)、用户“按照你的计划执行”。用户本轮确认车机项目与用机安排尚未确认。

## 约束

- 工作目录为交付区根目录；源码位于`src/mcp_eval/`，测试位于`src/tests/`。
- 旧审查、录制与结果保留；本轮证据位于`tests/results/remediation-2026-10-19/`。
- 用户未要求commit/push。已有未提交整改保留，本轮不重置工作树。
- 实时工具发现目标及真实至少5＋2不因离线整改而取消。

## 1. 判定和提供方边界（C01/C03/C04）

文件：`src/mcp_eval/judge.py`、`providers/openai_compat.py`；新增`src/tests/test_review_judgement.py`。

- [x] 先写并运行失败测试：错误主结果/回读不得通过；回读身份错误不得通过；22与22.0相等而True与1不等；非法空tool_calls归为提供方错误。
- [x] 实现统一成功条件、递归JSON值比较和严格tool_calls类型检查。
- [x] 运行新测试与既有判定/模型测试，保存结果。

关键契约：

```python
assert json_equal({"temperature": 22}, {"temperature": 22.0})
assert not json_equal(True, 1)
# tool_calls仅允许契约支持的missing/null/list；{}、false、0、空串均拒绝。
```

## 2. 执行检查点与任务时限（C02/C05）

文件：`runner.py`、`model_loop.py`；新增`src/tests/test_execution_checkpoints.py`。

- [x] 先复现主调用后回读异常/中断、模型第二轮中断、末次调用超期。
- [x] `_execute_item(..., checkpoint=None)`与`ModelLoop.run_case(..., checkpoint=None)`在外部调用之前/之后提交部分EvalRecord。
- [x] 编排器将检查点写入当前item的artifact；发生异常时保留最新部分记录，只有未开始的计划项使用not_run。
- [x] 在主调用与每条后置调用返回后检查单调时钟截止时间。
- [x] 验证部分结果能够报告重建，负面控制的已观察违规不因中断丢失。

关键测试判据：主调用成功后中断，结果仍包含主response，execution_status不为not_run，trace_complete为false；模型已执行工具记录仍存在；超期不能pass。

## 3. 验证与交付准备

- [x] 全量pytest及离线CLI/回放/rebuild验证；保留旧审查证据，使用新目录。
- [x] 统一L2配置的工具目录来源说明；记录设备项目尚未确认。
- [x] 建立真实用例冻结表，明确第五条正向候选及实时发现缺口，不编造工具契约。
- [x] 依据已验证事实充实结题报告；真实成绩、导师意见保留未完成状态。
- [x] 核对Skill结构及操作约束；没有真实自动触发环境时记录具体阻塞。
- [x] 更新README、任务状态、整改记录和memory。

10-20补充：Skill已完成四场景有限对照与局部整改复测；新版全场景重测、真实自动触发及用户/导师反馈仍待完成。真实设备任务受项目/窗口未确认阻塞。

验证命令使用当前交付区的`tests/results/remediation-2026-10-16/.venv/bin/python -B -m pytest`；pytest临时目录由`pytest.ini`限制在交付区。每个逻辑修改完成后先运行相关测试，最终统一全量检查。
