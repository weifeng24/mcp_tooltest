# 本地预检结果：车机全量评测阻塞

**当前不能直接运行所有车机用例，也不能把 `--mcp all` 用作只读工具清单采集。** 本轮已执行 9 条本地预检命令，真实设备用例执行数为 0，模型 API 调用数为 0；未执行 ADB 或实际工具目录采集。

题设中的“合成回放 8/8”仅作为已给定背景。本轮没有复跑合成批次；实际观察到的是回放配置预检通过、计划 8 条、`executed=0`、`device_verified=false`。合成数据通过不能证明车机、真实工具定义或模型接入可用。

## 1. 阻塞依据

以下源码和配置路径均相对本组 `sandbox/`，没有以历史评测结果替代本轮检查。

| 项目 | 本轮证据 | 结论 |
|---|---|---|
| 设备未配置 | `configs/servers/ark_mcp_service.json:5` 为 `"device_serial": ""`；L1 dry-run 退出码 2，报“device 模式必须填写 device_serial” | 不能启动真实 L1 批次。没有选择默认设备或填写虚构序列号绕过校验 |
| 真实工具文件缺失 | `configs/runs/l2_device.json:10` 指向 `tests/results/l2-device/tools_capture.json`；L2 dry-run 退出码 2，实际报 `No such file or directory` | 该配置引用文件确实不存在，L2 前置检查失败；模型 API 和密钥可用性本轮未验证 |
| `--mcp all` 非只读 | `README.md:117`、`docs/device-readiness.md:13` 与 `src/mcp_eval/device.py:1-5` 明确说明该入口可能执行既有车窗、空调等状态修改测试 | 不执行该命令；也不改用 `--mcp <服务>` 冒充只读发现。本轮未访问外部 C++ 源码树或设备二进制 |
| P01/P05 未接入设备通道 | P01 的 action 为 `tools_list`，P05 为 `resources_read`；两者 `show-call` 均退出 2 并明确提示不支持；`device.py:120-125` 将非 `tools_call` 设备动作标为 `blocked/unsupported_action` | 即使后续填好序列号，也不能据此宣称全量车机用例可执行或通过。当前未产生真实逐用例 verdict；后续不支持项应保留为无法评定，不能删除后提高通过率 |
| 用例仍需对照真实接口 | `tests/cases/l1/P02_set_temp_valid.json:7-15` 使用开发示例工具 `HvacService.setTemp` 和回读条件；说明明确要求真机前核实 | 离线生成 argv 只证明参数构造，不证明车端存在该工具或参数适用 |

`runner.py:105-120` 在正常批次前加载配置并检查工具文件和设备号；`runner.py:208-219` 的 dry-run 在创建设备通道及批次输出目录之前返回。L2 本次先遇到工具文件缺失，不能据此推断其他前置条件已通过。

## 2. 已执行命令与原始输出

执行位置：开发机 Ubuntu Bash。本组交付根和工作目录为：

```text
/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-3-device-not-ready/without_skill/sandbox
```

解释器为用户指定的 `/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python`。每条产品命令使用 `-B -m mcp_eval`，并设置 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=src`，避免生成字节码缓存并使用本组源码。完整可追溯 argv、工作目录、环境覆盖和退出码见 [commands.json](commands.json)。下表是已执行记录。

| 编号 | `mcp_eval` 子命令及参数 | 退出码 | 实际观察 |
|---|---|---:|---|
| 01 | `--help` | 0 | 确认本地 CLI 支持的命令 |
| 02 | `checklist` | 0 | 输出“上机预检（尚未就绪）”；退出 0 只代表清单生成成功 |
| 03 | `run configs/runs/l1_device.json --dry-run` | 2 | 设备序列号为空，配置预检阻塞 |
| 04 | `run configs/runs/l2_device.json --dry-run` | 2 | 配置引用的工具 JSON 文件不存在 |
| 05 | `run configs/runs/replay_smoke.json --dry-run` | 0 | 计划 8 条，6 正向＋2 负面；实际执行 0 |
| 06 | `show-call tests/cases/l1/P02_set_temp_valid.json` | 0 | 仅生成单次调用 argv；`device_verified=false` |
| 07 | `capture-catalog configs/servers/ark_mcp_service.json --dry-run` | 0 | 8 个配置服务、16 个文件读取计划；`executed=0`、`device_configured=false`、`runtime_tools_list_tested=false` |
| 08 | `show-call tests/cases/l1/P01_tools_list.json` | 2 | `当前车端适配不支持 tools_list` |
| 09 | `show-call tests/cases/l1/P05_resources_read.json` | 2 | `当前车端适配不支持 resources_read` |

关键原文：

- [L1 stderr](03-l1-device-dry-run.stderr.txt)
- [L2 stderr](04-l2-device-dry-run.stderr.txt)
- [回放预检 stdout](05-replay-dry-run.stdout.txt)
- [工具目录采集计划 stdout](07-catalog-dry-run.stdout.txt)
- [P01 stderr](08-show-call-p01.stderr.txt)、[P05 stderr](09-show-call-p05.stderr.txt)

每条命令均保存独立的 `*.stdout.txt`、`*.stderr.txt` 和 `*.exitcode.txt`；空输出保留为空文件。清单原文中的 `adb devices` 是产品生成的现场指引，本轮没有执行，也不是当前离线阶段需要补跑的步骤。

## 3. 只读采集的可用边界

已离线验证 `capture-catalog ... --dry-run` 能生成现有注册定义文件的读取计划。计划中的 `/data/mcp/dump` 来自配置，尚未证实适用于真实设备；16 个文件是计划数量，不能当作已取得 16 份文件或已发现 8 个服务。

`src/mcp_eval/catalog.py:62-80,87-107` 表明，实际采集入口通过 ADB 读取已有的 `tools_服务名.json` 和 `resources_服务名.json`；空序列号会被拒绝。它不会替代实时 `tools/list`，资源定义文件也不等于 `resources/read` 得到的资源值。`catalog.py:155-156` 还明确保留快照可能陈旧、工具别名待验证的边界。

本轮只生成计划，没有取得真实 `tools_file`，也没有完成 P01/P05。

## 4. 最小下一步

**先取得真实设备身份与可追溯的完整工具定义，再做独立配置副本的本地预检。** 当前离线阶段可向设备维护者索取已有材料，无需运行设备命令：

1. **设备资料：**所属项目、真实序列号、已有连接状态记录、设备/二进制版本与来源、服务范围及实际注册快照目录；未知项标为“未确认”。这些信息用于排除错误设备、错误路径和版本不匹配。
2. **完整定义文件：**取得与该设备/服务版本对应的原始工具 JSON，保留导出方式、时间和覆盖范围。需包含工具 `name`、`inputSchema` 等完整定义，不能以工具名称摘要或合成样例替代。来源不明、文件缺失或只有摘要时继续保持阻塞。
3. **收到材料后的完成判据：**在本组独立配置副本中关联真实身份和定义文件，先完成本地加载与 `--dry-run`；核对完整工具名、参数、预期响应和涉及状态修改时的回读/恢复方法。本轮原配置保持原样。dry-run 成功仍不代表车机就绪；P01/P05 需独立解决设备接口支持。

后续进入允许连接设备的验证阶段时，先验证一条已核实的读取工具调用，再扩大到已确认用例；模型层另行核对提供方、端点、模型和凭据。当前不直接启动全量批次。

## 5. 产物与核验边界

- 本轮只在本组生成诊断脚本、原始输出和说明；没有修改产品源码或原配置，没有安装包或提交。
- [preflight-verification.json](preflight-verification.json) 记录 9 条命令的退出码均符合所读代码的预期，其中退出 2 是被保留的阻塞，不是业务测试通过。
- [执行前](checked-inputs-before.json)与[执行后](checked-inputs-after.json)的 36 个已检查输入 SHA-256 相同；范围为本组源码、配置、用例、当前合成录制及三份产品说明文件。
- 访问范围详见 [access-log.md](../access-log.md)。强制读取的上层索引、记忆包含历史摘要；初次定位还额外读过上层 `src/README.md`，均已记录。没有加载目标 Skill 或其 references，也未访问其他组及独立历史评测/评分文件。通用流程 Skill 的加载另有记录，因此不声称完全无历史上下文的盲评。
- token 与总耗时未取得，记为未知，不估算。
