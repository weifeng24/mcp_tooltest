# Code Review 质量审查报告 · 校招生AI实战演练 / MCP工具评测 / src/src/mcp_eval（核心执行、判定、配置、回放及采集静态审查与离线反例）

> THUNDERSOFT · CONFIDENTIAL
> 兜底 Markdown 模板, 用于 Gerrit / GitLab MR / GitHub PR 评论区粘贴。HTML 是主交付物。

## §1 项目概览

| Field      | Value           |
| ---------- | --------------- |
| Repository | 校招生AI实战演练 / MCP工具评测        |
| Module     | src/src/mcp_eval（核心执行、判定、配置、回放及采集静态审查与离线反例）      |
| Branch     | main      |
| Commit     | `fe75e121ce02fa9e889d786ca699698f6a93fc61`    |
| 审查时间   | 2026-10-23（UTC+08:00）   |
| Reviewer   | OpenCode AI辅助审查；非导师验收    |
| 扫描模式   | 当前工作树；产品源码未修改；160项回归、8项合成回放、旧7项修复复核、新4项边界反例   |
| 应用规则   | Common九维检查；无额外项目编码规范文件；Python评测端不套用车端C++领域规则, 维度2 N/A：同步编排无共享线程；维度8 N/A：无直接Binder/AIDL实现（adb子进程已有检查）；维度6 UI项N/A, 分数仅为已检出项的模板扣分，非覆盖率、项目进度或演练成绩；修复片段未应用 |

## §2 总体评分

**综合评分: 9.8 / 10  →  A 级  →  CL 评分 不适用；本地复审结论为Request changes**

| Critical | Major | Minor | Q/Praise |
| -------- | ----- | ----- | -------- |
| 0 | 1 | 1 | 0 |

> **评审边界**: 本报告只覆盖 **编码规范 / 设计规范 / 历史 Bug Root Cause 逻辑检查**; 不覆盖架构设计 / Bug Fix / 功能验收。


**Request changes：新增2项问题（P1一项、P2一项），4个离线反例复现。模板分数不代表合入批准或演练成绩。** 修复片段未应用，仅核对语法。需求与验收覆盖见 [主审查报告](requirements-review.md)。

## §3 各维度评分

| 维度 | 权重 | 得分 | 🔴 Critical | 🟡 Major | 🟢 Minor | 💡 Q/P | 备注 |
| ---- | ---- | ---- | ----------- | -------- | -------- | ------ | ---- |
| 维度1·空安全与边界防护 | 20% | 10.0/10 | 0 | 0 | 0 | 0 |  |
| 维度2·线程安全与同步机制 | 14% | — | 0 | 0 | 0 | 0 | N/A |
| 维度3·资源与内存管理 | 20% | 10.0/10 | 0 | 0 | 0 | 0 |  |
| 维度4·代码逻辑与语法规范 | 14% | 8.7/10 | 0 | 1 | 1 | 0 |  |
| 维度5·性能与体验优化 | 8% | 10.0/10 | 0 | 0 | 0 | 0 |  |
| 维度6·兼容性、安全与工程规范 | 8% | 10.0/10 | 0 | 0 | 0 | 0 |  |
| 维度7·代码风格与命名规范 | 8% | 10.0/10 | 0 | 0 | 0 | 0 |  |
| 维度8·IPC 通信安全 | 6% | — | 0 | 0 | 0 | 0 | N/A |
| 维度9·序列化与数据格式 | 6% | 10.0/10 | 0 | 0 | 0 | 0 |  |

维度二、八为 N/A：无共享锁模型，不实现 Android AIDL/Binder；adb 调用契约另查。

## §4 严重等级分布

P0=0；P1=1；P2=1；P3=0。图表见 HTML。

## §5 问题汇总

| # | 严重 | 规则 | 维度 | 检查项 | 位置 | 修复建议 |
|---|---|---|---|---|---|---|
| 1 | Major | `4.21` | 维度4·代码逻辑与语法规范 | 非有限数值可通过参数校验并进入工具执行（P1） | `src/src/mcp_eval/providers/openai_compat.py:101` | 建议片段未应用，仅经语法检查。严格拒绝NaN/Infinity及溢出产生的非有限浮点数；L1加载、模型解析、直接对象入参及最终序列化应采用一致策略，并转换为现有配置/参数错误。验收：NaN、Infinity、-Infinity、1e309及嵌套非有限值均不得下发；合法边界数值保持正常。证据：tests/results/review-2026-10-23/probe-results.json中的C01两项。 |
| 2 | Minor | `4.23` | 维度4·代码逻辑与语法规范 | 异常结束时已观察的禁止调用决策未参与负面判定（P2） | `src/src/mcp_eval/model_loop.py:111` | 建议片段未应用，仅经语法检查。将已解析决策与实际执行分开记录，在异常收尾和rebuild时使用一致判据；不要为了保存决策而继续下发超时工具，也不要把没有有效决策的API错误改为fail。验收：两个反例均fail且执行器调用0次，无决策的错误仍unassessed。证据：tests/results/review-2026-10-23/probe-results.json中的C02两项。 |

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
- 无

### P1
- `src/src/mcp_eval/providers/openai_compat.py:101` — 非有限数值可通过参数校验并进入工具执行（P1） (规则 `4.21`)

### P2
- `src/src/mcp_eval/model_loop.py:111` — 异常结束时已观察的禁止调用决策未参与负面判定（P2） (规则 `4.23`)

工时尚未评估；优先修复判定和证据缺陷，再核对真机。修复后重跑反例及回归，当前没有问题已被修复的结论。
