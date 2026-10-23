# MCPVehicleService 离线预检与注册目录采集计划

## 1. 本轮结论

已在本组交付副本设置离线序列号，生成 checklist，并完成 `MCPVehicleService` 注册定义采集的 dry-run。计划包含两个文件，`executed=0`，未连接设备或 API。**本轮仅证明本地清单与计划可以生成，不能证明真机就绪、目录存在或工具可用。**

执行位置：本机 Ubuntu Bash；工作目录为

```text
/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-7-preflight-plan/with_skill/sandbox
```

使用用户指定解释器，`PYTHONPATH=src`；另设 `PYTHONDONTWRITEBYTECODE=1` 禁止生成 Python 字节码。完整实际命令与输出位置见 [commands.md](commands.md)。

## 2. 配置修改及本机检查

唯一配置修改：`sandbox/configs/servers/ark_mcp_service.json` 的 `device_serial` 从空字符串改为 `SYNTHETIC-SERIAL-NOT-A-DEVICE`。`service_bin=mcp_service`、`dump_dir=/data/mcp/dump`、服务清单及其他字段保持原值。

- [修改前配置](server-before.json)的 SHA-256 与修改前命令记录一致。
- [实际差异](10-server-diff.stdout.txt)仅包含上述序列号变更。
- [修改前哈希](06-input-hashes-before.stdout.txt)与[修改后哈希](09-input-hashes-after.stdout.txt)显示目标 `SKILL.md` 内容一致。
- [环境自检](03-check-env.stdout.txt)确认 Python ≥3.10、`jsonschema`/`pytest` 可导入、交付根目录符合要求及本机存在 adb 命令。未验证 adb 版本、设备连接或模型可用性；本轮也未运行 pytest。

## 3. 生成的 checklist

原始清单保存在 [07-checklist.stdout.txt](07-checklist.stdout.txt)，包含设备身份、二进制用法、基线、完整工具目录、用例冻结、配置预检、正式批次、L2 前提和证据/恢复等九项提示。

**清单第1、2项中的序列号是刻意设置的虚构值。清单所列 adb、设备批次和基线查询命令均未执行；不能照抄该清单进行现场操作。** 其中 `/data/AIOS_Ark_2026-dev/...` 仅作为本地配置内容和清单文本出现，本轮没有访问该源码树。

## 4. dry-run 结果及统计

实际调用参数：

```text
-m mcp_eval capture-catalog configs/servers/ark_mcp_service.json --service MCPVehicleService --dry-run
```

原始 JSON：[08-capture-catalog-dry-run.stdout.json](08-capture-catalog-dry-run.stdout.json)。

| 计划项 | 远端路径（仅文本计划） | 本轮状态 |
|---|---|---|
| 工具注册定义 | `/data/mcp/dump/tools_MCPVehicleService.json` | 未执行，是否存在/可读/有效均无法判断 |
| 资源注册定义 | `/data/mcp/dump/resources_MCPVehicleService.json` | 未执行，是否存在/可读/有效均无法判断 |

输出关键字段：

```json
{
  "executed": 0,
  "device_configured": true,
  "runtime_tools_list_tested": false
}
```

`device_configured=true` 只表示配置中的序列号字段已填写。合成序列号仍会产生该值，它不证明真实设备存在、身份正确、已授权或在线。

按两个文件读取计划统计：计划 **2**，实际执行 **0**，成功采集 **0**，失败采集 **0**，未执行且无法判断 **2**。这些是本报告对计划的统计，未伪造程序不存在的 `counts` 字段。没有执行 L1 接口级或 L2 模型级评测，也没有产生真实采集 `catalog`、`capture_manifest` 或评测批次目录。

## 5. 数据来源与结论边界

- 本轮来源为本组本地配置和程序生成的计划，设备号为人工合成值；没有真实注册定义、工具响应或资源值。
- 未来真实采集的来源应标记为 `registration_dump`，表示读取既有注册定义文件。它不能替代实时 `tools/list`（工具发现）或 `resources/read`（资源值读取）。
- 依据 `docs/catalog-capture.md`，实际采集还须保留 `freshness=not_verified`、`atomic_snapshot=false`、`alias_verified_on_device=false` 等边界。这些字段不是本次 dry-run 已输出或已验证的事实。
- 各文件可能陈旧，且并非同一时刻的原子快照；无前缀工具名生成的 `服务名.工具名` 别名仍需现场验证，不猜测数值服务 ID。
- `--mcp all` 可能执行既有车控测试，不能用作只读工具发现。实时发现及资源读取入口仍未验证，相关评测应保留 `blocked`。
- 尚未取得完整、可追溯的工具定义，依赖该目录的 L2 批次仍受阻；本轮未检查模型接入或调用 API。

## 6. 接下来需现场确认

下表是后续现场信息需求。本次离线演练到此结束，以下确认和操作均未执行。

| 待确认项 | 需取得的证据与完成判据 | 异常或缺失时的处理 |
|---|---|---|
| 设备所属项目与窗口 | 现场负责人确认车型/项目、目标设备及允许操作时段；核对是否确为当前 Ark 配置适用对象 | 项目不一致时先核对实际配置，不套用 Ark 路径或其他项目二进制 |
| 真实设备身份与访问状态 | 实际序列号、连接状态为 `device`、必要授权及读取权限；在未来获准的现场配置中替换合成值并重新生成清单 | `unauthorized`、`offline` 或多设备无法区分时，先解决身份/连接问题 |
| 二进制与版本对应关系 | 设备实际 `service_bin`、软件/服务版本、构建来源及用法输出；核对是否支持 `--toolscall` | 本地源码 commit 不能证明设备版本；无参用法可能非零退出，应核对输出内容，不以退出码判工具接口通过 |
| 注册定义导出路径及范围 | 实际 dump 目录、`MCPVehicleService` 注册情况、两个 JSON 文件是否存在且可读，以及原始完整内容 | 文件不存在或权限不足时保留错误，向模块维护者确认导出方式；不自动启用 dump、重启服务或用旧测试补采 |
| 定义新鲜度与一致性 | 文件生成时间、对应服务/设备版本及当前注册关系；记录采集时间、原始内容、来源和哈希 | 无法核实时继续标记新鲜度未知、非原子快照；不声称实时目录通过 |
| 工具契约与名称绑定 | 真实完整工具名、输入 schema、返回字段、错误类型及服务名前缀别名；冻结一项已确认的读取用例 | 别名及契约未验证前，不把目录条目视为可成功调用的工具 |
| 后续真实用例与状态恢复 | 现场确认原始状态、允许修改范围、后置回读及恢复方法；先核对最小用例，再准备正式批次 | 失败、超时或中断后先确认状态，避免直接重试或仅凭“成功”响应认定状态正确 |
| 实时接口及 L2 前提 | 单独确认可采集完整实时结果的入口；L2 另需完整工具目录、已核对的模型配置和可用凭据 | 未具备时保留阻塞，注册快照与模型配置均不替代实际能力验证 |

## 7. 产物与访问范围

所有本轮产物均位于本组 `outputs/`：本报告、[访问记录](access-log.md)、[实际命令记录](commands.md)、原始 checklist、原始采集 dry-run JSON、各命令 stdout/stderr、配置原值、差异及哈希。

访问以本组 sandbox 和 outputs 为主；按上层要求读取了项目索引及记忆，并使用指定解释器与通用 Skill。上层材料暴露了历史评测摘要等信息，已明确记录为上下文污染，**本轮不属于完全盲评**。未进入其他评测组或历史评测目录，未打开评测断言/评分标准文件。没有修改主项目、Skill 或产品源码，没有安装包、提交或真实设备/API 调用。
