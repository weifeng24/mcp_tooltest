# Code Review 质量审查报告 · {{REPO}} / {{MODULE}}

> THUNDERSOFT · CONFIDENTIAL
> 兜底 Markdown 模板, 用于 Gerrit / GitLab MR / GitHub PR 评论区粘贴。HTML 是主交付物。

## §1 项目概览

| Field      | Value           |
| ---------- | --------------- |
| Repository | {{REPO}}        |
| Module     | {{MODULE}}      |
| Branch     | {{BRANCH}}      |
| Commit     | `{{COMMIT}}`    |
| 审查时间   | {{TIMESTAMP}}   |
| Reviewer   | {{REVIEWER}}    |
| 扫描模式   | {{SCAN_MODE}}   |
| 应用规则   | {{APPLIED_RULES}} |

## §2 总体评分

**综合评分: {{TOTAL_SCORE}} / 10  →  {{GRADE}} 级  →  CL 评分 不适用；本地复审结论为Request changes**

| Critical | Major | Minor | Q/Praise |
| -------- | ----- | ----- | -------- |
| {{COUNT_CRITICAL}} | {{COUNT_MAJOR}} | {{COUNT_MINOR}} | {{COUNT_QUESTION}} |

> **评审边界**: 本报告只覆盖 **编码规范 / 设计规范 / 历史 Bug Root Cause 逻辑检查**; 不覆盖架构设计 / Bug Fix / 功能验收。


**Request changes：新增2项问题（P1一项、P2一项），4个离线反例复现。模板分数不代表合入批准或演练成绩。** 修复片段未应用，仅核对语法。需求与验收覆盖见 [主审查报告](requirements-review.md)。

## §3 各维度评分

{{DIMENSION_TABLE_MD}}

维度二、八为 N/A：无共享锁模型，不实现 Android AIDL/Binder；adb 调用契约另查。

## §4 严重等级分布

P0={{COUNT_CRITICAL}}；P1={{COUNT_MAJOR}}；P2={{COUNT_MINOR}}；P3={{COUNT_QUESTION}}。图表见 HTML。

## §5 问题汇总

| # | 严重 | 规则 | 维度 | 检查项 | 位置 | 修复建议 |
|---|---|---|---|---|---|---|
{{ISSUE_TABLE_MD}}

## §6 问题详情

### R23-C01 · 非有限数值可通过参数校验并进入工具执行（P1）

- 位置：[src/src/mcp_eval/providers/openai_compat.py:101](../../../src/mcp_eval/providers/openai_compat.py)
- 规则：4.21
- 严重等级：major

模型参数使用默认json.loads；NaN被解析为float，带minimum=16/maximum=30的number Schema仍接受它。离线反例观察到validation_errors=0且执行器收到一次NaN参数。L1配置也接受NaN，device.command_for_case产生包含NaN的非标准JSON命令。此处只复现本地下发边界，不声称真实设备接受或执行了非法参数。关联位置：config.py:166、model_loop.py:207、device.py:88。

**原代码／修复后（未应用）：**

```diff
--- 原代码摘录
+++ 修复建议（未应用）
@@ -1,3 +1,7 @@
-arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
+def reject_nonfinite(token):
+    raise ValueError(f"非标准JSON常量: {token}")
+
+arguments = json.loads(raw_args, parse_constant=reject_nonfinite) if isinstance(raw_args, str) else raw_args
+json.dumps(arguments, allow_nan=False)
 if not isinstance(arguments, dict):
     raise ValueError("arguments 必须为 JSON 对象")
```

**修复说明：** 建议片段未应用，仅经语法检查。严格拒绝NaN/Infinity及溢出产生的非有限浮点数；L1加载、模型解析、直接对象入参及最终序列化应采用一致策略，并转换为现有配置/参数错误。验收：NaN、Infinity、-Infinity、1e309及嵌套非有限值均不得下发；合法边界数值保持正常。证据：tests/results/review-2026-10-23/probe-results.json中的C01两项。

### R23-C02 · 异常结束时已观察的禁止调用决策未参与负面判定（P2）

- 位置：[src/src/mcp_eval/model_loop.py:111](../../../src/mcp_eval/model_loop.py)
- 规则：4.23
- 严重等级：minor

model_response事件已经保存一个完整调用决策，但在超时或finish_reason=length分支提前返回，response_raw.tool_calls仍为空。judge_record只检查后者，两个反例均判unassessed；按design.md第4节已观察到禁止调用即保留fail的契约，应判fail。实际下发次数均为0，停止执行的预算保护有效；问题是决策证据与执行记录混用导致漏报违规。关联位置：judge.py:97-102。

**原代码／修复后（未应用）：**

```diff
--- 原代码摘录
+++ 修复建议（未应用）
@@ -1,3 +1,9 @@
 calls = response.get("tool_calls") if isinstance(response, dict) else None
-if any(a["type"] == "no_tool_call" for a in case["assertions"]) and isinstance(calls, list) and calls:
+observed = [decision for event in record.events
+            if isinstance(event, dict) and event.get("kind") == "model_response"
+            and isinstance(event.get("decisions"), list)
+            for decision in event["decisions"]
+            if isinstance(decision, dict) and isinstance(decision.get("name"), str)
+            and decision["name"]]
+if any(a["type"] == "no_tool_call" for a in case["assertions"]) and (observed or isinstance(calls, list) and calls):
     return _set(record, "fail", "负面控制被违反：已观察到工具调用决策")
```

**修复说明：** 建议片段未应用，仅经语法检查。将已解析决策与实际执行分开记录，在异常收尾和rebuild时使用一致判据；不要为了保存决策而继续下发超时工具，也不要把没有有效决策的API错误改为fail。验收：两个反例均fail且执行器调用0次，无决策的错误仍unassessed。证据：tests/results/review-2026-10-23/probe-results.json中的C02两项。
## §7 整改顺序

### P0
{{ROADMAP_CRITICAL_MD}}

### P1
{{ROADMAP_MAJOR_MD}}

### P2
{{ROADMAP_MINOR_MD}}

工时尚未评估；优先修复判定和证据缺陷，再核对真机。修复后重跑反例及回归，当前没有问题已被修复的结论。
