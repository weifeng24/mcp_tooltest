---
name: mcp-eval
description: 运行与解读车载 MCP 服务（mcp_service）的工具可用性评测。当用户要求"跑 MCP 评测""测试工具是否好用""验证 tools/list 或 tools/call""准备上机""解读评测报告""对比模型工具调用表现"时使用本 Skill，即使用户没有明确说出 mcp-eval。也用于上机日按清单执行 adb 采集与评测批次。不要用于：修改评测工具自身源码（普通开发任务）、与公司车载 MCP 无关的通用 MCP 咨询、真实车机以外的 MCP server 评测。
---

# MCP 评测执行与解读

面向公司车载 `mcp_service` 的可用性评测。工具位于交付区 `src/`（下称交付区根目录），源码 `src/mcp_eval/`，全部命令在交付区根目录执行。

## 核心原则

- **回放（replay）数据只证明工具链路可用，不能作为"工具好用"的结论**；结论只引用 device（真机）通道数据。报告中两通道分组统计，解读时先看通道。
- **unassessed（无法判断）不是失败**：证据不足（adb 失败、输出解析失败、录制缺失）时如实标注，不猜结果。
- **密钥只经环境变量使用**（`DEEPSEEK_API_KEY`、`KIMI_API_KEY`），不写入文件、不打印、不提交。
- 真机操作后**恢复车况**（如空调温度）并记录。

## 前置检查

运行 `scripts/check_env.sh`（在交付区根目录执行 `bash skills/mcp-eval/scripts/check_env.sh`）。它检查 Python、pytest、adb、PYTHONPATH 与密钥环境变量是否就绪，并说明缺什么；不会打印密钥内容。

## 三种运行模式

| 模式 | 命令（交付区根目录） | 用途与结论效力 |
|---|---|---|
| 回放冒烟 | `PYTHONPATH=src python3 -m mcp_eval run configs/runs/replay_smoke.json` | 离线验证链路；合成样本，不作结论 |
| 真机批次 | `PYTHONPATH=src python3 -m mcp_eval run configs/runs/l1_device.json`（L1）/ `l2_device.json`（L2） | 正式结论数据；需 adb 连接车机并在 server 配置填 device_serial |
| API 冒烟 | `PYTHONPATH=src python3 scripts/api_smoke.py configs/models/deepseek.json` | 验证模型密钥与工具调用链路；mock 执行，不动车机 |

执行前可用 `--dry-run` 只校验配置与计划。上机日完整步骤用 `PYTHONPATH=src python3 -m mcp_eval checklist` 生成，按其逐项执行并留档。

## 报告解读

报告在 `tests/results/<run-id>/report.md`。解读规则见 [references/report-guide.md](references/report-guide.md)；常见报错与处理见 [references/troubleshooting.md](references/troubleshooting.md)。

要点：

1. 先确认通道：回答"工具是否好用"只能用 `device|...` 分组。
2. 看三个数：计划内通过率（保守）、判定覆盖率（证据充分度）、失败/无法判断明细。
3. 负面用例 fail 且原因为"预期错误未出现"是**有效评测发现**（服务端未落实约束），不是评测工具出错。
4. 引用数据时保留 run_id 与证据路径，不复述无来源的数字。

## 边界

- 不修改被测车机源码与 baseline 树（`/data/AIOS_*` 只读引用）。
- 不承诺真实客户端（IDE）结论：首版范围不含 IDE 直连，被问及时说明自研传输限制并指向 docs/design.md。
- 评测工具本身的代码修改不属于本 Skill，按普通开发流程处理。
