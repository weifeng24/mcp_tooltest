# Code Review 质量审查报告 · mcp_tooltest / mcp_eval（代码可靠性；需求覆盖另见 requirements-review.md）

> THUNDERSOFT · CONFIDENTIAL
> 兜底 Markdown 模板, 用于 Gerrit / GitLab MR / GitHub PR 评论区粘贴。HTML 是主交付物。

## §1 项目概览

| Field      | Value           |
| ---------- | --------------- |
| Repository | mcp_tooltest        |
| Module     | mcp_eval（代码可靠性；需求覆盖另见 requirements-review.md）      |
| Branch     | main      |
| Commit     | `5e10eef421602fc468b616680f2bba7da35f659e`    |
| 审查时间   | 2026-10-16（UTC+08:00）   |
| Reviewer   | OpenCode AI 审查；非公司正式审批    |
| 扫描模式   | src/ 全量静态检查及隔离离线反例；无真机/API 调用；修复片段仅为设计示意，未应用   |
| 应用规则   | AGENTS.md, code-review Common 9 维度, code-review-and-quality |

## §2 总体评分

**综合评分: 7.7 / 10  →  B 级  →  CL 评分 0**

| Critical | Major | Minor | Q/Praise |
| -------- | ----- | ----- | -------- |
| 3 | 7 | 1 | 0 |

> **评审边界**: 本报告只覆盖 **编码规范 / 设计规范 / 历史 Bug Root Cause 逻辑检查**; 不覆盖架构设计 / Bug Fix / 功能验收。


**Request changes：存在 P0 阻塞。模板分数不是演练成绩。** 修复片段未应用，仅核对语法。需求与验收覆盖见 [主审查报告](requirements-review.md)。

## §3 各维度评分

| 维度 | 权重 | 得分 | 🔴 Critical | 🟡 Major | 🟢 Minor | 💡 Q/P | 备注 |
| ---- | ---- | ---- | ----------- | -------- | -------- | ------ | ---- |
| 维度1·空安全与边界防护 | 20% | 6.0/10 | 1 | 2 | 0 | 0 |  |
| 维度2·线程安全与同步机制 | 14% | — | 0 | 0 | 0 | 0 | N/A |
| 维度3·资源与内存管理 | 20% | 10.0/10 | 0 | 0 | 0 | 0 |  |
| 维度4·代码逻辑与语法规范 | 14% | 3.0/10 | 2 | 3 | 0 | 0 |  |
| 维度5·性能与体验优化 | 8% | 10.0/10 | 0 | 0 | 0 | 0 |  |
| 维度6·兼容性、安全与工程规范 | 8% | 9.7/10 | 0 | 0 | 1 | 0 |  |
| 维度7·代码风格与命名规范 | 8% | 9.0/10 | 0 | 1 | 0 | 0 |  |
| 维度8·IPC 通信安全 | 6% | — | 0 | 0 | 0 | 0 | N/A |
| 维度9·序列化与数据格式 | 6% | 9.0/10 | 0 | 1 | 0 | 0 |  |

维度二、八为 N/A：无共享锁模型，不实现 Android AIDL/Binder；adb 调用契约另查。

## §4 严重等级分布

P0=3；P1=7；P2=1；P3=0。图表见 HTML。

## §5 问题汇总

| # | 严重 | 规则 | 维度 | 检查项 | 位置 | 修复建议 |
|---|---|---|---|---|---|---|
| 1 | Critical | `4.13` | 维度四·代码逻辑 | 用例配置未接入车端客户端实际读取及执行路径 | `src/src/mcp_eval/device.py:146` | P0，上机前必须修。先核实设备二进制版本与支持命令；本地基线源码 main.cpp:161-166 已有 --toolscall，可评估复用。若保留配置方式，须对齐加载路径、配置节点并备份恢复。以独立契约测试核对实际请求，而非让 FakeRunner 无条件返回成功。示意代码未应用，不构成完整修复。 |
| 2 | Critical | `4.2` | 维度四·代码逻辑 | 模型只尝试了目标工具就被当作任务完成 | `src/src/mcp_eval/judge.py:149` | P0，正式评测前必须修。保存模型决策、校验拒绝、执行尝试三个不同事件。用实际工具定义冻结断言；增加错误参数、执行失败、无限调用及缺最终回答的反例。报告可单列选工具率，但不得将其命名为任务完成率。 |
| 3 | Critical | `1.4` | 维度一·空安全与边界 | 模型 API 失败及缺失调用证据被负面控制误判通过 | `src/src/mcp_eval/judge.py:86` | P0，正式评测前必须修。用明确的 trace_complete/终止状态区分零调用和缺失证据；未知错误及判定器错误不得计为被测对象通过或失败；保留可信证据已证实违规的优先级。 |
| 4 | Major | `9.1` | 维度九·序列化 | 把最后一个 JSON 对象或请求回显当作目标响应 | `src/src/mcp_eval/device.py:167` | P1，上机前修。保存完整原文，明确事件类型与 request id，支持真实日志输出格式。没有目标响应时记为无法判断，不能从其他 RPC 的成功推导本用例成功。 |
| 5 | Major | `4.25` | 维度四·代码逻辑 | 总超时未约束模型等待和后续工具执行 | `src/src/mcp_eval/model_loop.py:106` | P1，上机前修。总时限传递到 provider/adb；响应返回后及每次工具执行前重检；区分模型轮数与工具调用数。明确远端任务超时取消/恢复，不把终止本机 adb 等同于车端操作停止。 |
| 6 | Major | `4.23` | 维度四·代码逻辑 | 重跑删除历史结果，中断丢计划项并导致分母缩小 | `src/src/mcp_eval/runner.py:114` | P1，上机前修。用不可覆盖的批次 ID、完整 manifest 和逐项异常记录；中断也可重建部分报告。计划项身份应含 case/model/repeat，统计分母来自 manifest。测试必须覆盖中断与重复运行。 |
| 7 | Major | `4.24` | 维度四·代码逻辑 | 回放折叠重复录制且沿用旧 case_id | `src/src/mcp_eval/replay.py:25` | P1。明确回放是按事件序列还是固定样本查询；重复命中不得默默丢失败历史。保留源时间、源用例和当前运行身份，增加同请求多次及跨用例复用测试。 |
| 8 | Major | `1.12` | 维度一·空安全与边界 | dry-run 提前返回且工具采集输入与上机清单不一致 | `src/src/mcp_eval/runner.py:100` | P1，上机前修。区分配置语法预检和设备可用性；建立只读发现及规范工具导出路径。清单使用 git -C 查询版本，保持交付区工作目录；提供真实二进制位置/依赖核查，不把打印清单视为实测。 |
| 9 | Major | `7.11` | 维度七·接口契约 | 记录缺少设计承诺的原始证据、版本与准确资源统计 | `src/src/mcp_eval/model_loop.py:119` | P1，正式采集前补。保存逐轮原始输入输出、实际请求 ID、配置/源码/Schema 版本、完整 stdout/stderr 与证据相对路径；未知用量不填零，mock 与真机标明来源。依据完整用量和费率再核算成本。 |
| 10 | Major | `1.5` | 维度一·空安全与边界 | 断言参数未验证，缺失字段会退化为永真条件 | `src/src/mcp_eval/config.py:96` | P1。按断言类型使用 oneOf/独立校验，拒绝空选择器、错误值类型和不适用动作；Schema 验证使用明确草案版本的 check_schema。错误判据属于配置/评测器错误，不应归为被测工具失败。 |
| 11 | Minor | `6.6` | 维度六·输出兼容 | 分组键未转义导致 Markdown 指标表错列 | `src/src/mcp_eval/report.py:94` | P2。对所有表格文本统一转义，或将维度拆成独立列；增加 Markdown 表格列数检查。只影响展示不改变 summary.json 数值。 |

## §6 问题详情

### R01 · 用例配置未接入车端客户端实际读取及执行路径

- 位置：[src/src/mcp_eval/device.py:146](../../../src/mcp_eval/device.py)
- 规则：4.13
- 严重等级：critical

execute_case 只写 workdir/case_config.json，随后执行固定路径 mcp_service -c -t --mcp <service>。config_target 完全未使用，service=auto 直接发给客户端。对照车端 TestConfig.cpp:111-137，Android 默认读 /system/etc/test_config_ark.json；test_mcp_interface.cpp:147-175 的带服务名重载读 specific_services，而生成器写 mcp_interface。即使临时文件成功生成，也不能证明指定工具和参数被执行。见反例 R01-config-not-consumed。另缺少固定二进制路径的安装/发现步骤。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,3 +1,4 @@
-command = command_for_case(case)
-setup = f"cat > {self.workdir}/case_config.json ..."
-result = self.runner(["shell", " ".join(command)], timeout)
+# 修复设计示意：已核实目标二进制支持 --toolscall 后，显式传递单次请求。
+command = [service_bin, '-c', '-t', '--toolscall', resolved_tool, json.dumps(arguments)]
+remote_command = shlex.join(command)
+result = runner(['shell', remote_command], remaining_timeout)
```

**修复说明：** P0，上机前必须修。先核实设备二进制版本与支持命令；本地基线源码 main.cpp:161-166 已有 --toolscall，可评估复用。若保留配置方式，须对齐加载路径、配置节点并备份恢复。以独立契约测试核对实际请求，而非让 FakeRunner 无条件返回成功。示意代码未应用，不构成完整修复。

### R02 · 把最后一个 JSON 对象或请求回显当作目标响应

- 位置：[src/src/mcp_eval/device.py:167](../../../src/mcp_eval/device.py)
- 规则：9.1
- 严重等级：major

extract_jsonrpc 按行解析且接受任意含 jsonrpc/result/error 的字典，record_from_result 直接取 records[-1]。复现了 id=1 的错误响应被 id=1001 的成功响应覆盖、仅请求回显被标 completed、多行 JSON 无法提取。车端 --mcp 本身会执行多种调用；TestCommon.cpp:15-103 对工具清单仅输出摘要且完整 JSON 输出被注释，当前采集方案也不能保证获得完整工具定义。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,2 +1,5 @@
-records = extract_jsonrpc(result.stdout)
-response = records[-1] if records else None
+# 示意：先获取完整结构化帧，再严格匹配请求。
+candidates = [msg for msg in frames if msg.get('id') == expected_id and ('result' in msg or 'error' in msg)]
+if len(candidates) != 1:
+    raise ValueError('响应缺失或关联不唯一')
+response = candidates[0]
```

**修复说明：** P1，上机前修。保存完整原文，明确事件类型与 request id，支持真实日志输出格式。没有目标响应时记为无法判断，不能从其他 RPC 的成功推导本用例成功。

### R03 · 模型只尝试了目标工具就被当作任务完成

- 位置：[src/src/mcp_eval/judge.py:149](../../../src/mcp_eval/judge.py)
- 规则：4.2
- 严重等级：critical

M01 仅检查工具名包含 setTemp 及调用数上限，不检查 temperature=22、是否真实执行、工具结果、回读状态或最终回答。复现：模型给出 40，参数校验拦截、executor 调用次数为零，仍 verdict=pass；硬轮数上限终止且 final_answer=null 也通过。模型调用意图不能替代执行与业务结果。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,3 +1,3 @@
-names = [str(c.get('name', '')) for c in _tool_calls(record)]
-if any(needle in n for n in names):
-    return True, ''
+# 修复契约示意：将工具选择、参数语义、执行结果和任务完成分别断言。
+required_checks = ['exact_tool', 'temperature_equals_22', 'call_executed', 'tool_succeeded', 'state_readback', 'final_answer_consistent']
+completion_required = True
```

**修复说明：** P0，正式评测前必须修。保存模型决策、校验拒绝、执行尝试三个不同事件。用实际工具定义冻结断言；增加错误参数、执行失败、无限调用及缺最终回答的反例。报告可单列选工具率，但不得将其命名为任务完成率。

### R04 · 模型 API 失败及缺失调用证据被负面控制误判通过

- 位置：[src/src/mcp_eval/judge.py:86](../../../src/mcp_eval/judge.py)
- 规则：1.4
- 严重等级：critical

_tool_calls 将缺失/非法 tool_calls 转为空数组；INFRA_ERROR_CATEGORIES 未包含 provider_error。复现 M03 遇 ProviderError 后 execution_status=error 却 verdict=pass，response_raw=None 也 pass。没有记录不能证明没有调用。同时 timeout 被无条件称为跟踪完整，违背设计中的证据前提。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,2 +1,7 @@
-calls = response.get('tool_calls')
-return calls if isinstance(calls, list) else []
+# 修复设计示意：先验证证据完备性，再评价是否应调用。
+if record.error_category == 'provider_error' or not trace_complete:
+    verdict = 'unassessed'
+elif not isinstance(response.get('tool_calls'), list):
+    verdict = 'unassessed'
+else:
+    verdict = 'pass' if not response['tool_calls'] else 'fail'
```

**修复说明：** P0，正式评测前必须修。用明确的 trace_complete/终止状态区分零调用和缺失证据；未知错误及判定器错误不得计为被测对象通过或失败；保留可信证据已证实违规的优先级。

### R05 · 总超时未约束模型等待和后续工具执行

- 位置：[src/src/mcp_eval/model_loop.py:106](../../../src/mcp_eval/model_loop.py)
- 规则：4.25
- 严重等级：major

仅在每轮开始检查时钟；provider 固定单次超时，executor 无剩余预算参数。复现任务时限 1 秒、provider 返回时模拟时钟为 999 秒，仍执行工具并记 completed。每轮可包含多个工具，调用总数未单列上限；case.timeout_seconds 也被 runner 的全局 timeout 覆盖。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,5 +1,5 @@
-if self.clock() - start > timeout_seconds:
-    return self._finish(...)
-response = self.provider.chat(messages, self.openai_tools)
-for decision in response.tool_calls:
-    result, is_validation_error = self._execute_decision(decision, original_name)
+# 示意：统一截止时间，所有阻塞边界及下发前检查剩余时间。
+remaining = deadline - clock()
+if remaining <= 0:
+    raise TimeoutError('任务总预算已耗尽')
+response = provider.chat(messages, tools, timeout=remaining)
```

**修复说明：** P1，上机前修。总时限传递到 provider/adb；响应返回后及每次工具执行前重检；区分模型轮数与工具调用数。明确远端任务超时取消/恢复，不把终止本机 adb 等同于车端操作停止。

### R06 · 重跑删除历史结果，中断丢计划项并导致分母缩小

- 位置：[src/src/mcp_eval/runner.py:114](../../../src/mcp_eval/runner.py)
- 规则：4.23
- 严重等级：major

同 run_id 会 unlink results.jsonl，循环中异常未收敛为逐项记录，只有全部结束才生成报告。summarize 的 planned 实际来自 len(records)，未读取固定运行计划。复现旧证据被覆盖，第二项中断后只剩一条结果且无新报告；两项计划只传入一条成功记录时报告显示 planned=1、覆盖率=100%。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,4 +1,4 @@
-if results_path.exists():
-    results_path.unlink()
-# ...
-group['planned'] += 1
+# 修复契约示意：独立批次目录、固定计划和终止收尾。
+manifest = {'run_id': unique_run_id, 'planned_items': planned_items}
+missing_items = set(planned_item_ids) - set(recorded_item_ids)
+# missing_items 在报告中保留为 not_run/unassessed；禁止删除旧批次。
```

**修复说明：** P1，上机前修。用不可覆盖的批次 ID、完整 manifest 和逐项异常记录；中断也可重建部分报告。计划项身份应含 case/model/repeat，统计分母来自 manifest。测试必须覆盖中断与重复运行。

### R07 · 回放折叠重复录制且沿用旧 case_id

- 位置：[src/src/mcp_eval/replay.py:25](../../../src/mcp_eval/replay.py)
- 规则：4.24
- 严重等级：major

同请求指纹只保留最后一条，无法重放失败→成功序列或状态读取变化；命中后只更新 run_id/channel/timestamp，不更新 case_id。复现源记录 P02 被另一用例 P09 命中，输出仍为 P02；两次重复录制均回放最后的成功结果，污染分组与回归结论。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,4 +1,4 @@
-self._index[sig] = raw
-# ...
-record.run_id = run_id
-record.channel = 'replay'
+# 修复设计示意：使用逐请求序列，并保留来源身份。
+self._index.setdefault(sig, []).append(raw)
+record.case_id = case['case_id']
+source_identity = {'run_id': source_run_id, 'case_id': source_case_id, 'event_index': event_index}
```

**修复说明：** P1。明确回放是按事件序列还是固定样本查询；重复命中不得默默丢失败历史。保留源时间、源用例和当前运行身份，增加同请求多次及跨用例复用测试。

### R08 · dry-run 提前返回且工具采集输入与上机清单不一致

- 位置：[src/src/mcp_eval/runner.py:100](../../../src/mcp_eval/runner.py)
- 规则：1.12
- 严重等级：major

dry-run 在加载模型、tools_file、recording 前返回，引用不存在的模型配置仍通过；load_tools 不支持原始 JSON-RPC result.tools 包装。清单却让用户从 --mcp all 采集完整工具列表：该命令执行已有测试调用，且 ToolsList 日志是摘要。清单中的 cd 基线树还改变后续 PYTHONPATH=src 命令的工作目录。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,3 +1,5 @@
-info = plan(run, cases, root)
+# 修复设计示意：无副作用预检全部本地引用及适用契约。
+models = [load_config(root / ref, 'model') for ref in run.get('model_refs', [])]
+tools = parse_tools_capture(capture_data)
 if dry_run:
-    return {'plan': info, 'executed': 0}
+    outcome = {'plan': info, 'executed': 0, 'unverified': device_checks_not_run}
```

**修复说明：** P1，上机前修。区分配置语法预检和设备可用性；建立只读发现及规范工具导出路径。清单使用 git -C 查询版本，保持交付区工作目录；提供真实二进制位置/依赖核查，不把打印清单视为实测。

### R09 · 记录缺少设计承诺的原始证据、版本与准确资源统计

- 位置：[src/src/mcp_eval/model_loop.py:119](../../../src/mcp_eval/model_loop.py)
- 规则：7.11
- 严重等级：major

usage 每轮覆盖而不累计，rounds=len(call_log) 实为调用数；L2 未填 latency_ms/request_raw，未保存完整对话/工具定义快照。ChannelExecutor 丢弃底层 EvalRecord 的错误类别、耗时与证据；device 仅保存 stdout 最后 2000 字符，stderr 未保存、evidence 通常为空。原 API 冒烟记录的 442 tokens 只是最后一轮 usage，不能当作整个任务开销。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,4 +1,5 @@
-if response.usage:
-    usage = response.usage
-# ...
-'rounds': len(call_log)
+# 修复契约示意：分开保留逐轮资源与执行事件，再汇总。
+usage_by_round.append(response.usage)
+round_count += 1
+call_count = len(call_log)
+latency_ms = int((clock() - start) * 1000)
```

**修复说明：** P1，正式采集前补。保存逐轮原始输入输出、实际请求 ID、配置/源码/Schema 版本、完整 stdout/stderr 与证据相对路径；未知用量不填零，mock 与真机标明来源。依据完整用量和费率再核算成本。

### R10 · 断言参数未验证，缺失字段会退化为永真条件

- 位置：[src/src/mcp_eval/config.py:96](../../../src/mcp_eval/config.py)
- 规则：1.5
- 严重等级：major

assertions.items 仅验证 type，未按类型要求 path/value/name_contains 等字段。缺少 name_contains 的 model_selects_tool 能通过加载，随后空字符串匹配任意工具，复现 wrong_tool 也 pass。tools_have_schema 也只检查 dict，不验证 JSON Schema 合法性；field_equals 使用 Python 的宽松相等（例如 True==1）。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1,2 +1,5 @@
-'required': ['type'],
-'properties': {'type': {'enum': ASSERTION_TYPES}}
+# 修复契约示意：各类型有独立必填字段与适用动作。
+required_by_type = {'field_equals': ['path', 'value'], 'model_selects_tool': ['name_contains'], 'max_rounds': ['value']}
+missing = [key for key in required_by_type.get(assertion['type'], []) if key not in assertion]
+if missing:
+    raise ConfigError(f'断言缺少字段: {missing}')
```

**修复说明：** P1。按断言类型使用 oneOf/独立校验，拒绝空选择器、错误值类型和不适用动作；Schema 验证使用明确草案版本的 check_schema。错误判据属于配置/评测器错误，不应归为被测工具失败。

### R11 · 分组键未转义导致 Markdown 指标表错列

- 位置：[src/src/mcp_eval/report.py:94](../../../src/mcp_eval/report.py)
- 规则：6.6
- 严重等级：minor

分组键含三个管道符，直接插入 Markdown 单元格。复现表头为 7 列，数据行为 10 列；数字与列标题错位，影响报告阅读。现有测试仅搜索字符串，未验证表格结构。

**原代码／修复后设计示意（未应用）：**

```diff
--- 原代码摘录
+++ 修复设计示意（未应用）
@@ -1 +1,2 @@
-lines.append(f'| {key} | {g["planned"]} | ... |')
+escaped_key = key.replace('|', '\\|').replace('\n', ' ')
+lines.append(f'| {escaped_key} | {g["planned"]} | ... |')
```

**修复说明：** P2。对所有表格文本统一转义，或将维度拆成独立列；增加 Markdown 表格列数检查。只影响展示不改变 summary.json 数值。

## §7 整改顺序

### P0
- `src/src/mcp_eval/device.py:146` — 用例配置未接入车端客户端实际读取及执行路径 (规则 `4.13`)
- `src/src/mcp_eval/judge.py:149` — 模型只尝试了目标工具就被当作任务完成 (规则 `4.2`)
- `src/src/mcp_eval/judge.py:86` — 模型 API 失败及缺失调用证据被负面控制误判通过 (规则 `1.4`)

### P1
- `src/src/mcp_eval/device.py:167` — 把最后一个 JSON 对象或请求回显当作目标响应 (规则 `9.1`)
- `src/src/mcp_eval/model_loop.py:106` — 总超时未约束模型等待和后续工具执行 (规则 `4.25`)
- `src/src/mcp_eval/runner.py:114` — 重跑删除历史结果，中断丢计划项并导致分母缩小 (规则 `4.23`)
- `src/src/mcp_eval/replay.py:25` — 回放折叠重复录制且沿用旧 case_id (规则 `4.24`)
- `src/src/mcp_eval/runner.py:100` — dry-run 提前返回且工具采集输入与上机清单不一致 (规则 `1.12`)
- `src/src/mcp_eval/model_loop.py:119` — 记录缺少设计承诺的原始证据、版本与准确资源统计 (规则 `7.11`)
- `src/src/mcp_eval/config.py:96` — 断言参数未验证，缺失字段会退化为永真条件 (规则 `1.5`)

### P2
- `src/src/mcp_eval/report.py:94` — 分组键未转义导致 Markdown 指标表错列 (规则 `6.6`)

工时待车端入口确认后评估。修复后重跑反例及回归，当前没有问题已被修复的结论。
