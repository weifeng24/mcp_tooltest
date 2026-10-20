# 被测工具目录状态

状态：候选服务盘点，尚非最终工具集。来源为 Ark 源码的 `app/test/config/test_config_ark.json`，设备实际注册情况未验证。

| 服务候选 | 当前依据 | 实际工具定义/可运行性 |
|---|---|---|
| MCPVehicleService | 配置服务映射与用例 | 待原始 tools/list 与设备验证 |
| MCPVoiceService | 配置中的 setAcSwitch 示例 | 待核实完整参数与返回 |
| MCPMapService | 配置服务映射 | 待核实 |
| MCPVGuiService | 配置服务映射 | 待核实 |
| MCPKanziService | 配置服务映射 | 待核实 |
| MCPGuideService | 配置服务映射 | 待核实 |
| AndroidCameraProxy | 配置与相机测试入口 | 待核实 |
| NVCameraProxy | 配置与平台条件 | 待核实 |

`HvacService.setTemp/getTemp` 与 16—30 度来自协议文档示例，目前用于离线合成用例。不得据此认定它们就是以上目标设备的实际工具。

正式工具集应至少保存：服务/设备版本、完整工具名、description、inputSchema、可用的 outputSchema、读取/写入属性、测试任务、预期结果确认来源、状态恢复方式、实际验证批次。`tools_file` 可以保存完整 JSON-RPC `result.tools`，加载器会检查工具名唯一性及 Schema 合法性。

2026-10-19已有注册定义快照采集器，支持读取指定服务dump、规范名称别名并保留原文/哈希。具体见[catalog-capture.md](catalog-capture.md)。目前只有离线测试，没有真实采集产物；不得把开发配置中的8个服务视为实际全部注册。

工具集是课题预期交付物之一；仅有上述服务名清单不等于已交付可运行工具集。最终复用公司项目、附运行说明还是提交封装源码，按导师确认的交付边界执行。
