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


**Request changes：新增5项问题（P1三项、P2两项）。模板分数不代表合入批准或演练成绩。** 修复片段未应用，仅核对语法。需求与验收覆盖见 [主审查报告](requirements-review.md)。

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

### C01 · 正向字段断言和后置回读绕过工具错误标志

- 位置：[src/src/mcp_eval/judge.py:88](../../../src/mcp_eval/judge.py)
- 规则：4.2
- 严重等级：major / P1

judge_record的后置条件只检查trace_complete和字段值；field_equals分支（108—110行）也不检查工具结果isError。用当前P02模板和真实DeviceChannel解析器，分别令主调用或回读返回isError=true，同时保留匹配的structuredContent，均判pass。相互矛盾或带失败状态的响应不能证明成功。此缺陷影响L1主判定及L1/L2共同的后置验证。证据：C01-primary-error、C01-readback-error。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复方向（未应用）
@@ -1,3 +1,12 @@
-found, value = resolve_path(verifications[index].get('response_raw'), expected['path'])
-if not found or not json_equal(value, expected['value']):
-    failures.append(f"后置状态 {expected['path']} 不符合预期")
+# 设计片段：后置条件先核对执行与工具结果，再比较业务字段。
+checked = verifications[index]
+raw = checked.get('response_raw')
+result = response_result(raw)
+if checked.get('execution_status') != 'completed' or not checked.get('trace_complete'):
+    unknown.append('回读执行证据不足')
+elif result is None or result.get('isError', False) is not False:
+    failures.append('回读返回错误，不能证明目标状态')
+else:
+    found, value = resolve_path(raw, expected['path'])
+    if not found or not json_equal(value, expected['value']):
+        failures.append('后置状态不符合预期')
```

**修复说明：** P1，正式采集前修复。为正向工具调用与后置读取建立一致的响应成功前置条件，核对回读工具及参数身份；负面error_expected仍按冻结错误契约判断。矛盾响应至少不得pass，错误/未知的细分类需明确。示意片段不是完整补丁，未应用。

### C02 · 主调用后发生异常或中断会丢失已执行证据

- 位置：[src/src/mcp_eval/runner.py:200](../../../src/mcp_eval/runner.py)
- 规则：4.23
- 严重等级：major / P1

_execute_item在所有后置调用完成后才返回；run_evaluation在返回后才保存记录。复现主设置成功、回读阶段KeyboardInterrupt后，最终条目为not_run、executed=0、request/response均为空；同位置OSError会生成全新evaluation_error记录并丢掉主响应。分母虽保留，已发生调用仍被错记或遗失。OSError使用边界替身注入，标准AdbRunner已转换的OSError不走此抛出路径；KeyboardInterrupt可直接来自用户中断。证据：C02-interrupt、C02-oserror。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复方向（未应用）
@@ -1,5 +1,12 @@
+# 设计片段：分阶段持久化；中断时保留主调用，未开始条目才使用not_run。
+record = execute_primary(case)
+persist_checkpoint(record)
 try:
-    record = _execute_item(item, case, run, channel, tools, by_model)
-    judge_record(case, record)
-except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
-    record = EvalRecord(run_id=run['run_id'], case_id=case['case_id'], channel=run['channel'], action=case['action'], service=case['service'], execution_status='error')
+    execute_postconditions(record, case, checkpoint=persist_checkpoint)
+except KeyboardInterrupt:
+    record.trace_complete = False
+    record.execution_status = 'error'
+    record.error_category = 'interrupted_after_primary'
+    raise
+finally:
+    persist_checkpoint(record)
```

**修复说明：** P1，正式采集前修复。保存每次已完成调用及进行中状态，使异常包装携带部分记录；同样检查L2多轮中断。增加在主调用之后、后置读取期间、模型多轮之间中断的回归，不能仅测试第一条调用前中断。片段内函数为待设计接口，仅用于表达修复方向。

### C03 · 用JSON文本相等替代数值语义造成22与22.0误判

- 位置：[src/src/mcp_eval/judge.py:35](../../../src/mcp_eval/judge.py)
- 规则：9.1
- 严重等级：minor / P2

json_equal为避免True==1，改为比较json.dumps字符串，但把22和22.0也区分为不同值。当前P02的真实数值型温度回读只要采用浮点表示22.0，就会判fail。JSON Schema的number/整数值语义不要求这种文本差异；用例也没有声明必须返回整数字面量。证据：C03-numeric。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复方向（未应用）
@@ -1,2 +1,13 @@
+# 设计片段：JSON值递归比较；布尔值独立于数值，浮点误差容限应另配。
 def json_equal(left, right):
-    return json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(right, sort_keys=True, ensure_ascii=False)
+    if isinstance(left, bool) or isinstance(right, bool):
+        return type(left) is type(right) and left == right
+    if type(left) in (int, float) and type(right) in (int, float):
+        return left == right
+    if type(left) is not type(right):
+        return False
+    if isinstance(left, dict):
+        return left.keys() == right.keys() and all(json_equal(left[k], right[k]) for k in left)
+    if isinstance(left, list):
+        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
+    return left == right
```

**修复说明：** P2，冻结正式判据前修复。按JSON值语义递归比较，显式区分boolean与number；若业务需要浮点容差或精确字面量，提供单独断言。保留True与1不相等的回归，同时覆盖嵌套对象/列表中的22与22.0。输入非有限数应在数据入口拒绝。

### C04 · 空对象等非法tool_calls被折算为空数组并通过负面控制

- 位置：[src/src/mcp_eval/providers/openai_compat.py:86](../../../src/mcp_eval/providers/openai_compat.py)
- 规则：1.4
- 严重等级：major / P1

message.get('tool_calls') or []在类型检查之前将空对象、false、0和空字符串折算为[]。复现tool_calls={}并带正常文本的响应，经实际_parse和ModelLoop后得到trace_complete=true、no_tool_call=pass。输入类型错误仍被当作完整的零调用证据，属于前次R04/R10修复的遗漏。证据：C04-malformed-calls。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复方向（未应用）
@@ -1,3 +1,5 @@
-calls = message.get('tool_calls') or []
+calls = message.get('tool_calls')
+if calls is None:
+    calls = []
 if not isinstance(calls, list):
     raise ProviderError('响应 tool_calls 必须为数组')
```

**修复说明：** P1，L2正式评测前修复。只对接口契约允许的缺失/null做归一化，其他类型均抛ProviderError并归unassessed。增加{}、false、0、空字符串及正常[]的边界测试。

### C05 · L1最后一次调用返回后未检查总截止时间

- 位置：[src/src/mcp_eval/runner.py:154](../../../src/mcp_eval/runner.py)
- 规则：4.25
- 严重等级：minor / P2

L1路径只在每条后置调用之前检查deadline，主调用无后置条件或最后一次后置返回后没有再次检查。注入可控时钟：总预算1秒，执行器在2秒返回completed，最终latency_ms=2000仍判pass。该证据证明编排器边界缺失，不证明当前adb在真实设备上已经发生超时失效。证据：C05-late-l1。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复方向（未应用）
@@ -1,3 +1,5 @@
-result = channel.execute_case(followup, run['run_id'], remaining)
-record.provenance['postconditions'].append(result.to_dict())
-# 后置循环结束后直接返回记录。
+# 设计片段：主调用及每次后置调用返回后均执行，保留原始响应。
+if time.monotonic() >= deadline:
+    record.execution_status = 'timeout'
+    record.error_category = 'task_deadline_exceeded'
+    record.trace_complete = False
```

**修复说明：** P2，按共享任务预算设计补齐返回边界检查。业务效果与时限符合性分开记录；不宣称远端被取消。无后置条件及最后一条回读耗尽预算都应有回归，回放时延与实时墙钟预算口径需显式保留。
## §7 整改顺序

### P0
{{ROADMAP_CRITICAL_MD}}

### P1
{{ROADMAP_MAJOR_MD}}

### P2
{{ROADMAP_MINOR_MD}}

工时尚未评估；优先修复判定和证据缺陷，再核对真机。修复后重跑反例及回归，当前没有问题已被修复的结论。
