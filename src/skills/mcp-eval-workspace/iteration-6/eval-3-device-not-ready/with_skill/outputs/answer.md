# 设备未就绪：本地预检结果

## 结论

**当前不能直接运行全部车机用例，也不能把 `--mcp all` 用作只读工具清单采集。状态为 blocked（阻塞）。** 本次只执行了本地环境检查、帮助命令、上机清单生成和 `--dry-run` 预检；没有连接车机、调用模型 API 或创建真实评测批次。

用户给定的“合成回放 8/8”属于情景前提，本次没有重新执行或读取其历史批次。合成数据只能支持对应离线逻辑的结论，不能证明真实设备、工具绑定、模型调用或客户端集成可用。

## 本次实际证据

所有命令工作目录均为本组 `sandbox/`，使用指定 Python 解释器及 `PYTHONPATH=src`。原始输出保存在本目录，完整命令和访问边界见 [access-log.md](../access-log.md)。

| 检查 | 实际结果 | 证据 |
|---|---|---|
| 本机环境 | Python 与基础依赖可用；检测到 adb 命令，但没有检查设备连接；两个模型密钥环境变量均未设置 | [03-check-env.txt](03-check-env.txt) |
| 设备配置 | `device_serial` 为 `""`；`service_bin=mcp_service`、`dump_dir=/data/mcp/dump` 只是现有配置，未获设备实测验证 | `sandbox/configs/servers/ark_mcp_service.json:5-7` |
| 上机清单 | 退出码 0，但正文明确为“上机预检（尚未就绪）”；输出中的现场操作提示没有执行 | [07-checklist.txt](07-checklist.txt) |
| L1 接口级预检 | 退出码 2：`device 模式必须填写 device_serial` | [08-l1-device-dry-run.txt](08-l1-device-dry-run.txt) |
| L2 模型级预检 | 退出码 2：`tests/results/l2-device/tools_capture.json` 不存在；这是当前 `tools_file` 引用 | [09-l2-device-dry-run.txt](09-l2-device-dry-run.txt)、`sandbox/configs/runs/l2_device.json:10` |
| 注册目录采集预览 | 退出码 0；仅列出配置中 8 个服务、16 个文件的读取计划；`executed=0`、`device_configured=false`、`runtime_tools_list_tested=false` | [10-capture-catalog-dry-run.txt](10-capture-catalog-dry-run.txt) |

退出码 2 表示本地输入/配置阻塞，不能记为车机用例已经执行失败。清单或采集预览退出码 0 也不能记为真机准备通过。

### 用例数量与未执行项

本组文件枚举得到 L1 用例 8 个、L2 用例 4 个。按现有 run 配置，L1 重复 1 次；L2 列出两个候选模型、各重复 1 次，因此静态候选执行项为 8＋4×2＝16 项。

| 范围 | 静态候选项 | 真实执行 | 通过 | 失败 | 无法判断/未执行 |
|---|---:|---:|---:|---:|---:|
| L1 工具接口 | 8 | 0 | 0 | 0 | 8，设备未指定 |
| L2 模型工具调用 | 8 | 0 | 0 | 0 | 8，真实工具文件缺失；设备及模型条件亦未就绪 |
| 合计 | 16 | 0 | 0 | 0 | 16 |

这是按配置和文件路径统计的候选范围，不是已冻结或已执行的 manifest。预检在输入校验阶段终止，没有生成本次真实批次目录、`manifest.json`、`results.jsonl` 或 `summary.json`；“无法判断”是本报告对未执行项的说明，不是伪造的判定器结果。全部候选项保留，不缩小范围以制造通过率。

## 为什么不能使用 `--mcp all`

- `sandbox/skills/mcp-eval/SKILL.md:45-49` 明确禁止把 `--mcp all` 当作只读采集。
- `sandbox/docs/device-readiness.md:11-14` 说明该入口可能运行既有车窗、空调等配置调用；工具发现和资源读取仍没有独立、已验证的机器可读采集入口，对应动作仍为 `blocked/unsupported_action`。
- 因此，补齐序列号后也不能立即宣称“所有车机用例都能跑”。尚须核对真实工具契约，并单独解决不支持的动作。

本次采用的是 `capture-catalog ... --dry-run`，其帮助明确说明“不运行 adb”。预览中的 `shell`、`cat` 只是待执行计划文本，没有执行远端读取，也没有取得任何真实工具清单。

## 最小下一步

**当前只需向设备负责人取得一份可核对的设备与工具资料，作为后续输入提供；本离线情景继续保持阻塞。** 所需最小信息为：

1. 确认目标项目、目标设备实际序列号、设备/服务二进制版本及路径、实际 dump 目录和服务范围；不要把 Ark 示例路径直接套用到未经确认的项目。
2. 提供该目标环境的完整原始工具定义 JSON，至少包含工具名和 `inputSchema`（输入参数结构约束），并附设备/服务版本、采集来源和采集时间。只有摘要、合成工具目录或来源不明的文件，不能解除真实 `tools_file` 阻塞。

资料齐备后，在另行允许更新配置的阶段，将已确认值写入指定配置副本，重跑 `checklist` 和 L1/L2 `--dry-run`。本轮没有修改原配置，也没有用虚构序列号或合成目录绕过检查。

如果现场只能提供已有注册 dump，可在另行允许设备访问、确认读取权限后使用 `capture-catalog` 采集所选服务的现有定义文件。该结果应标记为 `registration_dump`（注册定义快照），保留 `freshness=not_verified`、`atomic_snapshot=false`、`alias_verified_on_device=false`；它不证明实时 `tools/list`、`resources/read` 或生成别名可调用。文件缺失或无权限时保留错误，向维护者核对实际导出方式，不改用 `--mcp all`。

后续真实执行的最小范围应先是一条已核实的只读 `tools_call`，核对完整请求、响应及工具绑定后再扩展；涉及状态修改时需先有原值、回读与恢复办法。L2 还需分别核实模型端点、权限和密钥可用性，不能由合成回放或候选模型配置推定已接通。本轮不执行这些现场操作。

## 隔离与额外访问

写入仅位于本组。为遵守上层要求，读取了根目录 `docs/README.md`、`memory/CURRENT.md`；其中包含历史评测摘要及评分信息，构成上下文污染，不能称为完全盲评。另加载了三个通用流程 Skill，并使用用户指定的外部解释器环境。详细访问及污染记录见 [access-log.md](../access-log.md)；未追读其他组、历史评测文件或独立评分标准。
