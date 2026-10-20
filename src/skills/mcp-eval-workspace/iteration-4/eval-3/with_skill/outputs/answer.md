# 场景 3：合成回放后的真机准备判断

## 结论

**目前不能直接运行全部车机用例，也不能用 `--mcp all` 作为只读工具清单采集命令。**

合成回放 8/8 只支持人工构造样本条件下的结论。当前配置中的 `device_serial` 确实为空，L2 引用的工具文件确实不存在；此外，当前设备适配尚不支持实时工具发现与资源读取。填好设备号也不能消除这些能力缺口。

本次依据当前 Skill、项目文档、配置及实际离线预检回答。未连接设备、调用模型 API、执行正式回放或运行 pytest。

## 1. 本次实际检查结果

工作目录：`/home/tssh/文档/Works/mission/校招生ai演练任务/src`。

解释器：`tests/results/remediation-2026-10-16/.venv/bin/python`；Python 命令均设置 `PYTHONPATH=src` 和 `PYTHONDONTWRITEBYTECODE=1`。

| 检查 | 实际输出与含义 |
|---|---|
| 环境脚本帮助及本机自检 | Python 和依赖可用，adb 命令存在；不证明设备连接、版本或 API 可用。脚本仅检查 pytest 可导入，未运行测试 |
| CLI 及相关子命令帮助 | 已核对 `run`、`checklist`、`show-call`、`capture-catalog` 的实际参数 |
| `checklist` | 输出“上机预检（尚未就绪）”，要求先确认目标设备并填写序列号 |
| L1 真机配置预检 | `错误: device 模式必须填写 device_serial；尚未连接设备可用 replay 模式` |
| L2 真机配置预检 | 无法读取 `tests/results/l2-device/tools_capture.json`，原因是文件不存在 |
| P02 的 `show-call` | 只展示 `mcp_service -c -t --toolscall` 的参数数组，工具示例为 `HvacService.setTemp`、温度 22；`device_verified=false`。没有执行该命令 |
| `capture-catalog` 预检 | 针对 `MCPVehicleService` 展示两个文件的读取计划；`executed=0`、`device_configured=false`、`runtime_tools_list_tested=false` |
| 合成回放配置预检 | 计划 8 项，6 正向＋2 负面，`executed=0`、`device_verified=false` |

**数量与批次边界：** 本次没有生成评测批次，也没有新增通过、失败或无法判断结果。回放预检的 8 项全部未执行，不能记作本次 8 项通过，也不能编造 8 条 `unassessed` 结果。用户给出的“合成回放 8/8”属于已有结果陈述；未提供对应批次路径，本次没有读取其 `manifest.json`、`results.jsonl` 或 `summary.json`，未重新核验该历史批次。

当前回放配置引用 `recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl`，明确是合成样本。`channel=device` 或 `channel=replay` 只是执行通道标签，不能单独证明数据来自真机。

## 2. 为什么不能直接跑全部车机用例

- **L1（接口级评测）被设备身份配置阻塞。** 当前 `configs/servers/ark_mcp_service.json` 的 `device_serial` 为 `""`；设备项目、二进制版本、命令支持和工具契约还需现场核验。配置中列出 8 个服务，不代表设备实际注册了全部服务。
- **当前设备通道只接入单工具调用。** 已离线核对的入口是 `--toolscall`，仍不代表目标设备已经支持并验证。
- **P01 的 `tools_list`（工具发现）与 P05 的 `resources_read`（资源值读取）尚未接入可验证的设备入口。** 这些动作属于 `blocked/unsupported_action`，不能计为通过。实际批次中应保留计划项和无法判断状态，不通过删项缩小分母。
- **具备调用实现通道的正向模板目前只有 P02、P03、P04、P06 四条。** N01、N02 是负面模板，也需要真实错误契约。当前不能声称已有至少 5 条正向＋2 条负面真机用例可执行；`docs/case-freeze.md` 中拟新增的 P07 尚未建立执行 JSON。
- **L2（模型调用工具评测）还缺完整工具输入。** `tools_file` 指向不存在的占位路径。需要包含工具名称、描述及 `inputSchema`（输入参数结构约束）的完整 JSON；日志摘要不能补成真实定义。取得工具文件后还需核对模型端点、权限等条件，不能据此直接认定 L2 就绪。

开发模板中的 Hvac 名称、温度上下界和返回字段尚未绑定目标设备，不能原样当作真实契约。

## 3. 工具清单应如何采集

**不要执行 `--mcp all` 来采集只读清单。** 当前项目文档明确指出，它可能执行已有的车窗、空调等配置测试。`--mcp <服务>` 也不能当作已验证的纯发现入口。

当前可用的准备方式是 `capture-catalog --dry-run`：它只展示读取既有注册定义文件的计划，不调用 adb。本次计划中的远端路径为：

- `/data/mcp/dump/tools_MCPVehicleService.json`
- `/data/mcp/dump/resources_MCPVehicleService.json`

这些路径来自 Ark 候选配置，**本次没有访问远端文件**。实际采集前须确认设备属于哪个项目、实际 `dump_dir`、服务范围、序列号和文件读取权限，不能跨项目套用路径。

真实 `capture-catalog` 只读取既有文件，不开启 dump、不重启服务、不调用车控工具。即使采集成功，仍需保留以下边界：

- 来源是 `registration_dump`（注册定义文件快照），不是实时 `tools/list`。
- `freshness=not_verified`、`atomic_snapshot=false`：文件新鲜度未经验证，各文件不是同一时刻的原子快照。
- `alias_verified_on_device=false`：生成的服务名前缀别名需要实际验证，不能猜数值服务 ID。
- 资源文件保存的是定义，不是资源值，不能证明 `resources/read` 通过。
- 本次预检只选择一个服务；后续即使显示 `catalog_status=complete`，也仅表示请求范围内文件完整，不代表所有服务齐全。
- `tools_status=partial` 时，不能把不完整工具目录当完整 L2 输入。取得并核对工具定义后，再使用实际返回的 catalog 路径替换 `tools_file`。

## 4. 可以复核的离线命令

第 4.1—4.3 节的预检命令已经由助手执行，无需重复。若要自行复核，使用**开发机 Ubuntu Bash**；不在车机 Shell 或远程服务器执行。前置条件是指定解释器及项目文件仍然存在，不需要设备或 API 密钥。

先确认位置：

```bash
cd "/home/tssh/文档/Works/mission/校招生ai演练任务/src"
pwd
```

`cd` 切换工作目录，`pwd` 显示当前目录。应输出上述完整路径；若目录不存在，停止并核对项目位置。

下面每条命令单独输入后按回车。`PYTHONPATH=src` 指定当前交付区内的源码目录；`PYTHONDONTWRITEBYTECODE=1` 禁止写入 Python 字节码缓存。它们只影响当前命令。

### 4.1 查看上机清单

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval checklist
```

目标是查看准备条件，命令只打印清单。当前应显示“尚未就绪”；这表示离线检查已给出阻塞信息，不是设备验证通过。不要在本次离线任务中继续执行清单建议的设备命令。

### 4.2 查看注册定义采集计划

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval capture-catalog configs/servers/ark_mcp_service.json --service MCPVehicleService --dry-run
```

`--service` 只选择该服务；`--dry-run` 只显示计划。正常结果为两个文件计划、`executed=0`、`device_configured=false`。这里的成功只表示计划可生成。若配置文件不可读，先核对目录和路径，不去掉 `--dry-run` 尝试真实采集。

### 4.3 检查 L1 和 L2 阻塞

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval run configs/runs/l1_device.json --dry-run
```

当前预期是缺少 `device_serial` 的错误。该结果说明设备批次未开始；本次只记录阻塞。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval run configs/runs/l2_device.json --dry-run
```

当前预期是工具文件不存在。缺少的文件不是空 JSON 能替代的，需要真实完整定义。若出现其他错误，保留完整错误文本，不能据此推断其余条件已经通过。

如任一命令提示解释器不存在或 `No module named mcp_eval`，先检查工作目录、解释器路径及 `PYTHONPATH=src`，不要继续真实运行。

## 5. 后续解除阻塞的顺序

本次止于上述离线检查。后续具备设备访问条件后，依次确认：

1. 设备所属项目、用机时段、序列号、实际二进制及版本与 `--toolscall` 支持情况。
2. 实际 dump 路径、目标服务及完整原始定义，保留采集来源、版本、原文和哈希。
3. 用例名称、参数、预期成功或错误、独立回读以及原状态和恢复办法，完成真实用例冻结。
4. 先核对一条只读调用，再验证一条可恢复设置，之后才扩大到已冻结批次。超时或中断时，先确认远端状态，再决定是否重试。
5. P01/P05 的能力缺口单独保留并解决；取得工具快照不能关闭这两项。正式评测保留所有计划项及未执行、证据不足项。

依据：`skills/mcp-eval/SKILL.md`、其报告与故障参考、`README.md`、`docs/device-readiness.md`、`docs/catalog-capture.md`、`docs/case-freeze.md`、`tests/cases/README.md` 及当前配置。完整访问与命令记录见同目录 `access-log.md`。
