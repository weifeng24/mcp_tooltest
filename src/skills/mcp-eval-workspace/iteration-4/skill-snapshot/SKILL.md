---
name: mcp-eval
description: 执行本项目的车载 MCP 评测与解读批次报告。用户要求运行 mcp_eval、离线回放、检查本项目真机准备、核对 manifest/results/report 或分析模型工具调用结果时使用。仅在任务属于本项目已有评测流程时触发；通用 MCP 概念问答、编写其他 MCP 服务、修改评测器源码、一般 adb 故障排查、只需修改 README 文句时不要触发。
---

# MCP 评测执行与证据解读

以交付根目录（有 `configs/`、`src/mcp_eval/`、`requirements.txt`）为工作目录。根据 README 选择实际 Python 解释器；命令中的 `python3` 可替换为该项目虚拟环境的解释器。

## 关键规则与自由度

- **CRITICAL：证据不完整不能推断通过。** API 失败、调用轨迹缺失、unsupported_action、no_recording 应结合记录解释，不能把“没看到调用”当作“正确不调用”。
- **CRITICAL：合成数据不支持真机结论。** 先核对 `source_type`、执行通道、版本及原始证据；`channel=device` 标签本身不是真实性证明。
- 执行步骤、目录、来源及指标口径采用低自由度：遵循工具帮助及冻结的 manifest，不凭经验改参数/预期，不覆盖旧批次。
- 原因解释采用中等自由度：可以提出可验证假设，分别标出证据与推测；不编造设备能力、额外测试或验收结论。
- 真实模型请求使用现有环境变量，不收集或显示密钥。真实设备操作按用户已确认的任务及状态恢复办法执行。

## 1. 先确认输入与能力

识别用户要执行回放、实际设备、模型验证还是解释已有报告。用户给出批次路径时读取该批次 `manifest.json`、`results.jsonl` 和 `summary.json`，不沿用旧的固定 `replay-smoke/` 目录。

先看脚本帮助，再将脚本作为黑盒运行；只有脚本失败需要诊断时才读实现：

```bash
bash skills/mcp-eval/scripts/check_env.sh --help
bash skills/mcp-eval/scripts/check_env.sh
PYTHONPATH=src python3 -m mcp_eval --help
```

环境自检只能证明本机基础依赖，不验证设备或模型额度。`--dry-run` 验证本地引用文件并显示未验证事项，不连接车机/API。

## 2. 根据已实现的模式执行

### 离线回放

```bash
PYTHONPATH=src python3 -m mcp_eval run configs/runs/replay_smoke.json --dry-run
PYTHONPATH=src python3 -m mcp_eval run configs/runs/replay_smoke.json
```

从输出获取实际新批次目录，查看全部计划项的判定及来源。当前开发样本明确为 synthetic；按实际输出报告数量，不在答复中写死 7/7 或 8/8。

### 真机准备

先读 `docs/device-readiness.md` 并生成 `checklist`。当前适配仅验证到 `--toolscall` 的离线命令契约；设备二进制、真实工具和输出仍待现场核对。

工具发现/资源操作当前没有受验证的 machine-readable 入口，返回 `blocked`。禁止将会运行旧测试的 `--mcp all` 当作只读工具采集。缺少完整工具目录时，说明尚不能开展依赖它的 L2 批次，保留阻塞与下一步所需信息。

可按 `docs/catalog-capture.md` 使用 `capture-catalog --dry-run` 检查注册定义文件的只读采集计划。真实采集前确认项目、序列号和dump目录。此入口读取现有文件，`registration_dump`不能表述为实时tools/list或资源读取通过；保留新鲜度未知、名称别名未验证等标记。

### 模型验证

只有用户要求真实 API 验证且实际凭据已就绪时，运行 `scripts/api_smoke.py`。它的模型请求可能收费，工具执行为本地状态模拟。Kimi Coding Plan 的接入配置与能力未核实，不声称双模型已通。

## 3. 解读与输出

按需读取 [报告规则](references/report-guide.md) 与 [故障处理](references/troubleshooting.md)。输出固定包含：

1. 实际执行/读取内容与批次路径。
2. 计划数、通过/失败/无法判断数量，以及未执行项。
3. 数据来源与结论边界。
4. 有证据的问题和下一步；未做的验证明确标记。

`results` 不全时按 manifest 保留缺失项，不缩小分母。需要重建时使用 `rebuild`，不用当前用例替换批次中冻结的版本。

## 4. 完成判据

命令执行、产物读取及来源核对完成后，才报告本次操作结果。离线验证完成不等于真机准备完成；Skill 结构校验不等于行为/触发评测或导师验收通过。IDE 首版范围差异按需求文档保留，不把模型切换当作 IDE 适配证据。
