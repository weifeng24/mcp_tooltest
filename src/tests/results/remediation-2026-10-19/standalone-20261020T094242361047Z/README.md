# MCP 工具评测

面向车载 MCP 工具的接口评测（L1）与模型调用评测（L2）原型。2026-10-19复审发现的5项问题已完成本轮离线整改：原7个反例均满足修复判据，完整回归160项通过，8项合成回放通过且报告重建一致。**真机、完整工具发现、Kimi接入及最终验收仍未完成**。最新证据见[本轮整改记录](docs/remediation-2026-10-19.md)，[复审报告](docs/reviews/2026-10-19/requirements-review.md)保留修复前结论。

支持配置加载、独立运行计划、顺序回放、明确的通过/失败/无法判断、报告重建和模型工具调用循环。开发样本采用 `synthetic` 标记，不能作为车机能力结论。实际范围及差异见 [proposal.md](proposal.md)，整改见 [docs/remediation.md](docs/remediation.md)。

## 1. 执行位置与环境

以下命令使用开发机 **Ubuntu Bash**，工作目录为本文件所在的交付区根目录。工作区布局中它是第一层 `src/`，源码是第二层 `src/src/`。

当前工作区进入方式：

```bash
cd "/home/tssh/文档/Works/mission/校招生ai演练任务/src"
pwd
```

预期末尾为 `校招生ai演练任务/src`，且本目录包含 `requirements.txt`、`configs/`、`src/mcp_eval/`。独立交付后请进入解压出来的交付根目录，不使用上述开发机绝对路径。

要求 Python 3.10 或更新版本；仅设备模式需要 adb。先检查版本：

```bash
python3 --version
```

### 创建隔离环境

```bash
python3 -m venv .venv
```

该命令只在交付区创建 `.venv/`，成功时通常没有输出。若报 `ensurepip` 不可用，需要先具备 Ubuntu 的 Python venv 支持；此时先解决环境问题，不继续安装。

```bash
.venv/bin/python -m pip install -r requirements.txt
```

依赖包括 `jsonschema` 和测试框架 `pytest`。成功时显示安装完成或已满足；网络/软件源错误时先保留错误信息，不使用管理员权限修改系统 Python。

### 本机缺少 ensurepip 时的已验证替代安装方式

本机曾遇到这一情况。可使用现有系统 pip 将依赖安装到**项目虚拟环境目录**，不修改系统已安装包。仅在上一种方式因 ensurepip 缺失而失败时执行：

```bash
python3 -m venv --without-pip .venv
```

读取该虚拟环境的依赖目录；`$(...)` 表示取命令输出，`VENV_SITE` 保存路径：

```bash
VENV_SITE=$(.venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
```

```bash
python3 -m pip --isolated install --no-cache-dir --index-url https://pypi.org/simple --target "$VENV_SITE" -r requirements.txt
```

`--target` 将依赖写入虚拟环境，`--isolated` 忽略个人 pip 配置，`--no-cache-dir` 不建立额外缓存。成功后仍使用 `.venv/bin/python` 运行下文所有命令；该方式不会给虚拟环境安装 pip，因此后续补装也使用同样的 `--target` 方法。

## 2. 离线验证：无需设备、无需模型密钥

### 检查工具帮助和测试

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval --help
```

`PYTHONPATH=src` 仅为当前命令指定源码包搜索位置。帮助中应包含 `run`、`show-call`、`rebuild`、`checklist`。

```bash
.venv/bin/python -m pytest -q
```

预期测试全部通过。测试临时文件统一写入 `tests/results/.pytest-tmp/`；集成测试使用隔离副本，不覆盖现有回放报告。

### 查看运行计划

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval run configs/runs/replay_smoke.json --dry-run
```

该命令校验配置、用例、引用文件和录制格式，不连接设备或模型。当前示例计划为 8 条 L1 用例（6 正向＋2 负面）；`executed` 为 0。预检通过不等于设备连接或接口已验证。

### 执行合成回放

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval run configs/runs/replay_smoke.json
```

预期输出 `counts` 为 8 个 pass，并给出 `manifest`、`results`、`summary`、`report` 的实际路径。数据来自 `recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl`，含主调用及状态回读的合成事件。

每次运行生成带时间戳和随机后缀的新目录，例如 `tests/results/replay-smoke-.../`。**不得把旧目录 `tests/results/replay-smoke/` 当作最新输出。** 用编辑器打开本次输出中的 `report` 路径即可查看报告。

回放按请求依次消费录制，不自动复制最后一次结果。重复次数超过已有录制时，后续条目显示 `unassessed/no_recording`，分母仍包含全部计划项。

### 重建报告

从本次输出复制批次目录的实际相对路径，替换下方占位项后执行；不要原样执行含占位项的命令。

```text
PYTHONPATH=src .venv/bin/python -m mcp_eval rebuild 实际批次目录
```

`rebuild` 使用该批次冻结的用例和计划，重算 summary 与报告，不重新调用模型或工具；相同输入的指标应一致。

## 3. 真机接口状态与上机前置条件

当前 device 适配仅实现源码中已核对的 `mcp_service -c -t --toolscall TOOL ARGS` 单工具入口，并按该入口固定的请求 `id=1` 关联响应。工具名和 JSON 参数直接传递，不改车端系统配置。

正式使用前必须确认：

1. 设备二进制与源码版本对应，确实支持该入口及完整响应日志。
2. `configs/servers/ark_mcp_service.json` 的 `device_serial` 和 `service_bin` 符合实际设备。
3. 用例中的完整工具名、参数、返回字段、错误判据与恢复方法已经按真实接口核对。当前用例仍是开发模板。
4. 获取可追溯的完整工具 JSON。当前客户端 ToolsList 输出主要为摘要；`--mcp all` 会执行既有工具测试，不能当只读发现使用。

可以离线显示单次调用参数：

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval show-call tests/cases/l1/P02_set_temp_valid.json
```

输出 argv 与 `device_verified: false`，不执行命令。无参工具不传空 JSON，以避免旧客户端将其转换为位置参数 `arg0`。

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval checklist
```

设备序列号未填写时，清单应提示尚未就绪。完整现场核对方法见 [docs/device-readiness.md](docs/device-readiness.md)。**发现和资源读取动作当前明确返回 blocked，不会调用 `--mcp all` 替代，也不会计为通过。**

2026-10-19 新增现有注册目录的只读快照采集：

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval capture-catalog configs/servers/ark_mcp_service.json --service MCPVehicleService --dry-run
```

先按 [docs/catalog-capture.md](docs/catalog-capture.md) 核对实际项目、目录和设备身份，再执行真实采集。该入口只读取现有dump，不等于实时tools/list或资源值读取；原始定义、名称别名、哈希与来源均会归档。

真机运行配置为 `configs/runs/l1_device.json` 和 `l2_device.json`。在上述条件确认前，不将配置文件存在当成真机可运行证明。

## 4. 模型接入与数据边界

- DeepSeek 有历史真实 API＋本地模拟工具的冒烟记录；本次整改后使用离线测试验证，尚未重新发起真实 API 调用。
- Kimi Coding Plan 的实际端点、模型、接口协议及权益尚待核实。现有 `kimi.json` 是待核对的候选配置，不代表 Coding Plan 与通用 Moonshot API 等价。
- OpenRouter 为扩展候选，尚未实测。不因 API key 外形相同就认为不同产品可互换。
- L2 要求有效 `model_refs` 与 `tools_file`。工具文件支持数组、`{"tools": [...]}` 或 JSON-RPC 的 `result.tools`，不接受仅有日志摘要的内容。

### 在本机终端设置凭据

只在需要真实 API 冒烟时操作，会产生提供方计费。使用同一 Ubuntu Bash 终端，交互输入不会回显，不把密钥放进可复制命令或项目文件：

```bash
read -rsp "DeepSeek API key: " DEEPSEEK_API_KEY
```

输入后按回车，再导出变量：

```bash
export DEEPSEEK_API_KEY
```

随后在**同一终端**运行：

```bash
PYTHONPATH=src .venv/bin/python scripts/api_smoke.py configs/models/deepseek.json
```

预期模型选择 22 度参数，执行器在本地模拟并回读状态；输出标记为 synthetic。结果不能证明真机成功。其他终端或 AI 工具进程不会自动继承这里的变量；缺变量会明确报错。HTTP 401 需要核对提供方凭据状态，反馈日志时不附密钥。结束后可用 `unset DEEPSEEK_API_KEY` 从本终端清除变量。

## 5. 输出与退出码

每个批次包含：`manifest.json`（固定计划、输入与源码哈希）、`results.jsonl`、`artifacts/`（完整记录/原始输出）、`summary.json`、`report.md`。回放额外保存录制输入副本及哈希。

`executed`表示尝试执行的计划项数，不是成功调用数。调用边界保存检查点；受控异常或中断后，已开始的条目保留部分证据并标记错误，只有尚未开始的条目使用`not_run`。结果追加中断时，收尾会从原子保存的artifact重建JSONL。强制终止进程、磁盘故障及远端状态恢复不因此得到保证。

| 退出码 | 含义 |
|---|---|
| 0 | 命令完成，正式运行的全部计划条目通过；dry-run 只表示本地预检完成 |
| 1 | 有失败或无法判断项，查看报告，不删除这些条目 |
| 2 | 配置、路径或输入错误，未开始正常批次 |
| 130 | 批次中断；已执行证据及未执行计划项仍保留 |

判定有三种：`pass`、`fail`、`unassessed`。模型错误、缺失证据、未支持动作不能计作通过。指标分母来自 manifest，不随丢失结果缩小。报告同时展示 `source_type`，仅靠 device/replay 标签不足以证明数据真实。

## 6. 交付入口

- [需求与范围](proposal.md)、[设计](docs/design.md)、[整改记录](docs/remediation.md)。
- [用例设计](tests/cases/README.md)、[工具目录状态](docs/tool-catalog.md)、[任务状态](tasks/todo.md)。
- [Skill](skills/mcp-eval/SKILL.md)及[整改记录](skills-creator/fix-log.md)：初版存在，完整验收仍待闭环。
- [中期自评](midterm.md)、[结题报告](docs/report.md)：区分已验证结果和待真机材料。
- [真实用例冻结表](docs/case-freeze.md)、[答辩讲解准备稿](docs/defense-outline.md)：用于取得设备信息后准备真实批次与最终演示。

源码在 `src/mcp_eval/`，测试在 `src/tests/`，配置在 `configs/`。正式提交名称和部门入口待确认；运行不依赖交付区之外的 `memory/` 或 `/data` 源码路径。
