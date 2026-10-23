# 只读采集注册定义快照

更新：2026-10-19。状态：命令契约、解析与文件归档已离线测试，未连接真实车机。

## 1. 已核实的源码依据

基线：Ark 的 `AIRuntime/MCPServices/Linux`，以实际设备版本另行核对。

| 位置 | 事实 |
|---|---|
| `app/test/config/test_config_ark.json:322-324` | 声明 `dump.enabled=true`、`dump.path=/data/mcp/dump` |
| `app/src/main.cpp:1051-1056` | Server启动时按配置设置RouteManager导出路径 |
| `RouteManager/src/RouteManager.cpp:852-858` | 注册时写出`tools_服务名.json`，内容是原始service_tools，而非加数值前缀后的版本 |
| 同文件 `:927-933` | 写出`resources_服务名.json`，这是资源定义，不是资源值 |
| `app/test/client/test_svcmap.cpp:46-59`、RouteManager.cpp `:2357-2374` | 当前--svcmap使用GetService，返回逻辑名等信息；不能按旧文档当作数字ID映射 |
| `app/src/main.cpp:161-166` | --toolscall声明支持serviceName.method及serviceId.method |

采集器仅读取已经存在的文件，不启用dump、不重启服务、不执行ToolsCall。目录内容可能陈旧，各文件不是原子快照；采集成功不证明服务当前注册、实时tools/list或resources/read成功。

## 2. 开发机离线查看计划

终端：Ubuntu Bash。目录：交付根目录；解释器依赖先按README准备。若使用系统Python且依赖已经验证，可将`.venv/bin/python`替换为`python3`。

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval capture-catalog --help
```

预期看到server配置路径、`--service`、`--timeout`和`--dry-run`选项。

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval capture-catalog configs/servers/ark_mcp_service.json --service MCPVehicleService --dry-run
```

此命令不运行adb。预期列出tools/resources两个远端文件读取计划，`executed=0`，`runtime_tools_list_tested=false`。`device_configured=false`表示尚未填写设备号，不能执行实际采集。

`--service`用于明确选择配置范围内的服务，可重复；不指定则使用server配置清单。`--timeout`为整次采集的有限正数秒预算，不是每文件重新计算的独立预算。

## 3. 现场采集

前置条件：确认借用车机对应的项目、实际dump目录及服务；通过adb连接且有读取权限。当前默认是Ark源码中的路径，不能套用于未经核对的Dora/Mostrar等设备。

1. 在开发机用`adb devices`确认目标设备状态为device，填写server配置中的device_serial。
2. 核对dump_dir与选定服务名。此工具不会修改车端配置；文件不存在或权限不足时保留错误，先向模块维护者确认实际导出方式。
3. 在同一交付目录执行已核对的采集命令，例如仅采集Vehicle：

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval capture-catalog configs/servers/ark_mcp_service.json --service MCPVehicleService
```

实际影响：通过adb读取两个现有JSON文件，保存本地独立目录，不执行车控工具或服务重启。成功时输出catalog和manifest的实际相对路径。

| 输出状态 | 解释及处理 |
|---|---|
| catalog_status=complete | 请求的文件均已读取、解析；只覆盖请求的服务子集，仍不证明新鲜度或运行能力 |
| partial/failed | 保留已采集原文与每文件错误；查看capture_manifest和raw，不删除失败文件条目 |
| tools_status=complete | 请求的工具定义文件完整，可供后续核对；若只是资源定义缺失，工具部分可单独使用 |
| tools_status=partial | L2加载器拒绝把不完整工具目录作为完整输入；补采集或明确选择可用子集 |

状态码0表示请求的全部文件捕获成功，1表示部分或全部失败，2表示本地配置错误，130表示中断。网络断开、超时或输出不是完整JSON时均保留证据。

## 4. 名称与证据

- 有点号前缀的工具名保留；无前缀名称生成`服务名.工具名`别名。bindings保留原名、转换策略和`alias_verified_on_device=false`。
- 不猜测数值serviceId，不把逻辑服务名列表当ID表；别名仍须在最小调用中验证。
- raw保存完整stdout/stderr、成功解析的定义；manifest记录远端路径、命令、状态、耗时和采集文本SHA-256。
- catalog包含`source.kind=registration_dump`、`freshness=not_verified`、`atomic_snapshot=false`，并显式声明未测试实时工具列表、未读取资源值。

核对完成后，将返回的catalog相对路径填入L2运行配置的tools_file。正式运行会另存tools-input.json及其哈希，避免后续目录变化影响历史复现。

## 5. 仍需解决的实时接口

实时ToolsList/ResourcesRead在C++客户端接口中存在，但当前通用CLI没有已核实的独立输出路径；评测器仍将这些device动作标为blocked。目录快照采集不会冒充这些操作的执行结果。

本机NDK29存在；Ark CMake引用的`SDK/InternalSDK/android-aarch64/MCPServices`路径未找到。另有Dora预编译库，但依赖Binder及平台libc++等，不能在目标项目/ABI未确认时混用。若需编译只读客户端探针，须先确认目标项目、同版本SDK头文件/库及设备运行依赖。
