# MCPVehicleService 离线预检与注册目录采集计划

## 结论

已在本组交付副本执行 checklist 和 `capture-catalog --dry-run`，两条命令均正常退出（退出码 0），stderr 均为空。计划涉及两个注册定义文件，`executed` 为 **0**。本轮未执行 ADB（Android Debug Bridge，Android 调试桥）、连接设备、调用模型 API、安装依赖或提交代码。

`sandbox/configs/servers/ark_mcp_service.json` 初读时的 `device_serial` 已为 `SYNTHETIC-SERIAL-NOT-A-DEVICE`，运行后复读仍一致，因此无需改写。此次新增文件全部位于本组 `outputs/`，没有修改产品源码。

## 运行位置与产物

- 终端：开发机 Ubuntu Bash。
- 工作目录：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-7-preflight-plan/without_skill/sandbox`，即本次交付根。
- 解释器：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python`。
- 环境：`PYTHONPATH=src` 指向本组源码；`PYTHONDONTWRITEBYTECODE=1` 禁止生成 Python 字节码缓存。
- 实际执行参数分别为 `-m mcp_eval checklist` 和 `-m mcp_eval capture-catalog configs/servers/ark_mcp_service.json --service MCPVehicleService --dry-run`。完整 shell 命令、工作目录和退出码见 [commands.json](commands.json)。两条命令已经执行，无需用户重复操作。

| 产物 | 内容 |
|---|---|
| [checklist.stdout.md](checklist.stdout.md) | CLI 原样生成的上机检查清单 |
| [checklist.stderr.txt](checklist.stderr.txt) | checklist 原始 stderr，空文件 |
| [catalog-plan.stdout.json](catalog-plan.stdout.json) | dry-run 原始 JSON 计划 |
| [catalog-plan.stderr.txt](catalog-plan.stderr.txt) | dry-run 原始 stderr，空文件 |
| [commands.json](commands.json) | 实际命令及结果摘要 |
| [access-log.md](access-log.md) | 文件访问、额外上下文与执行边界 |
| [00-directory-check.stdout.txt](00-directory-check.stdout.txt)／[stderr](00-directory-check.stderr.txt) | 执行前目录检查输出 |

**原始 checklist 仅作为本次离线生成证据。**其中序列号是明确的合成值，列出的设备连接、正式评测与模型步骤均未执行，不能照此清单连接真实设备，也不能据清单标题认定已就绪。

## 实际采集计划与证据边界

| 服务 | 类型 | 计划读取的设备路径 |
|---|---|---|
| MCPVehicleService | 工具注册定义 | `/data/mcp/dump/tools_MCPVehicleService.json` |
| MCPVehicleService | 资源注册定义 | `/data/mcp/dump/resources_MCPVehicleService.json` |

实际输出关键字段：

```json
{
  "executed": 0,
  "device_configured": true,
  "runtime_tools_list_tested": false
}
```

- `device_configured: true` 仅表示序列号字符串非空。源码 `src/mcp_eval/__main__.py:74` 使用 `bool(server["device_serial"])`，不会检查设备身份、连接状态或序列号真实性。
- `--service MCPVehicleService` 将计划限定为该服务；没有扩大到配置中的其他服务。
- `--dry-run` 分支只生成文件路径和读取参数。JSON 中的 `shell`、`cat` 是计划文本，没有被执行。真实执行器调用仅存在于另一分支。
- 本轮没有获取原始设备 JSON、文件哈希或真实采集 manifest；输出证明本地计划生成成功，不证明远端文件存在。
- 注册 dump 是服务注册时保存的定义快照，可能陈旧且两文件不是原子快照。即使未来成功读到文件，也不能替代实时 `tools/list`（工具发现接口）或 `resources/read`（资源值读取接口）的验证。本轮资源值未读取。

## 接下来仍需现场确认

以下项目均为待办，只有获得真实证据后才能关闭；本轮不执行现场操作。

| 待确认项 | 所需证据与完成判据 | 不满足时的处理 |
|---|---|---|
| 目标项目、设备与时间窗 | 设备负责人确认项目/车型、实际设备身份、可用时段及允许的读取范围；真实序列号与指定设备一致 | 保留未就绪，不将合成序列号用于现场连接 |
| ADB 访问条件 | 现场确认授权、连接状态和读取指定 dump 文件所需权限 | 无权限或设备身份不明确时停止采集；不自动 root 或重启 |
| 二进制与源码对应关系 | 确认实际 `mcp_service` 路径、版本或可核验的构建标识，并与目标源码版本建立对应 | 配置中的基线 commit 只是记录，不能当作设备版本证明 |
| 注册文件位置与完整性 | 确认目标项目实际 dump 目录、两个精确文件名、可读性及完整 JSON 内容；工具/资源数组可解析，工具定义含实际名称与参数 schema | 文件缺失、权限错误或只有摘要时记录具体阻塞；不自动开启 dump、启停服务或用 `--mcp all` 替代 |
| 快照来源与新鲜度 | 保存设备身份、采集时点、原始输出及哈希；核对文件生成时间与当前服务版本，明确两文件是否来自同一注册状态 | 无法证明新鲜度或一致性时继续标注未知，不宣称当前实时目录已验证 |
| 工具名称及实际调用契约 | 后续真实调用前确认 `--toolscall` 支持情况、完整工具名或服务名别名、参数、响应字段及错误判据 | 名称映射和调用契约仍待设备验证；不猜测数值 serviceId，不直接扩大批次 |
| 真实评测及恢复条件 | 若后续开展接口评测，先冻结用例预期、独立状态回读与恢复方法；实时发现/资源读取另确认可用入口 | 未实现或未验证的动作保持 blocked／未验证；本轮计划成功不计作真实用例通过 |

## 访问披露与未计量项

未读取目标 Skill 及其 references、其他组、历史评测文件或独立评分标准文件。按上层要求额外读取项目 `docs/README.md`、`memory/CURRENT.md`、`memory/DECISIONS.md`，并加载 `using-agent-skills`、`verification-before-completion` 两个通用流程 Skill；解释器及现有依赖来自用户指定路径。

强制索引/记忆及本组 README 已暴露历史状态和部分评测摘要，因此本轮不能称为完全盲评。完整访问范围见 [access-log.md](access-log.md)。token 消耗与总耗时未知，未估算。
