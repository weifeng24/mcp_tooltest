# 无目标 Skill 基线访问记录

## 边界与路径

- 用户指定唯一可写目录为本文件所在的 `without_skill/`；交付根与所有终端命令工作目录为本组 `sandbox/`。
- 使用指定解释器 `/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python`。该历史目录仅用于调用解释器，不查阅其中评测结果。
- 本轮仅做本地预检，不执行 ADB、模型 API、实际车控批次或 `--mcp all`。只使用现有依赖，不安装包，不提交。
- 目标 Skill、目标 Skill 的 references、其他组、历史评测文件和独立评分标准均不主动读取。

## 强制上层上下文及非本组访问

1. 环境已注入项目根 `AGENTS.md`，要求先读取资料索引和当前记忆。
2. 已全文读取项目根 `docs/README.md`、`memory/CURRENT.md`。其中包含历史测试、Skill 对照摘要和评分提示；这是强制上下文暴露，不能声称完全无历史信息的盲评。未跟进其历史评测、审查、评分标准链接；本轮判断以本组文件及实际命令输出为依据。
3. 初次定位交付根时额外读取了项目根 `src/README.md`。发现本组存在 `sandbox/` 后已校正，并重新读取 `sandbox/README.md`；额外读取如实记录，不隐去。
4. 在项目根 `src/` 以精确路径模式查找其至本组路径各层 `AGENTS.md`，无匹配；没有递归搜索其他组。
5. 按上层通用 Skill 发现要求调用 `using-agent-skills`。它是通用流程指引，不是被测目标 Skill；没有读取它引用的 references。
6. 本轮不涉及修改课题范围或追溯历史决定，未读取 `memory/DECISIONS.md`。未写上层索引、记忆：用户本轮唯一可写目录限制优先；交接信息保存在本组记录与 `outputs/answer.md`。
7. 保存结论前调用通用 `verification-before-completion`，要求依据实际执行输出核验；没有读取目标 Skill。

## 本组直接读取与检索

按探索顺序记录；相对路径均以本组 `sandbox/` 为基准，除非明确另述。

1. 列出本组目录、`outputs/` 和 `sandbox/` 的直接子项。只见文件名的 `input-hashes-before.json`、`timing.json` 未读取，原有文件未覆盖。
2. 全文读取 `README.md`。其中包含历史摘要和目标 Skill 链接，没有跟进该链接。
3. 仅在本组 `sandbox/` 使用 glob 查找 `AGENTS.md`、配置 JSON、源码 Python、用例 JSON 及这些目录下的 `AGENTS.md`；没有匹配到补充指令文件。
4. 全文读取 `src/mcp_eval/__main__.py`、`device.py`、`catalog.py`，以及 `configs/servers/ark_mcp_service.json`、`configs/runs/{l1_device,l2_device,replay_smoke}.json`。
5. 在 `src/mcp_eval/` 内检索 `dry_run|checklist|tools_file|device_serial|capture_catalog|def run`，定位离线分支和前置条件。
6. 读取 `src/mcp_eval/runner.py` 第 1—245、311—334 行，全文读取 `src/mcp_eval/config.py`。
7. 全文读取产品操作文档 `docs/catalog-capture.md`、`docs/device-readiness.md`。它们是 sandbox 内的常规项目文档，不是目标 Skill references；未跟进文档中的 `/data` 源码树或其他链接。
8. 全文读取 `tests/cases/l1/P01_tools_list.json`、`P05_resources_read.json`、`P02_set_temp_valid.json`。

## 命令与自动访问记录

- 首个 Bash 命令：`ls -ld` 检查本组 `outputs/`、`sandbox/` 和指定解释器路径；工作目录为本组 `sandbox/`。终端原文逐字保存在 `outputs/00-directory-check.stdout.txt`，退出码为 0，无 stderr。
- 新建本组诊断脚本 `outputs/run_preflight.py`，只执行脚本中明确列出的帮助、清单、dry-run 和 show-call 命令。`-B` 与 `PYTHONDONTWRITEBYTECODE=1` 禁止写入 Python 字节码缓存，`PYTHONPATH=src` 指向本组源码。
- 所有产品命令的完整 argv、工作目录、环境覆盖及退出码保存于 `outputs/commands.json`；stdout/stderr 分开按原始字节保存，不过滤错误或拼接成成功输出。没有输出的文件保留为空文件。
- 诊断脚本对本组源码、配置、用例、当前合成录制及上述三个说明文件做执行前后 SHA-256 校验；精确访问文件清单保存在 `outputs/checked-inputs-before.json` 和 `checked-inputs-after.json`，没有通过哈希扫描其他组或历史评测。
- CLI 导入本组 `src/mcp_eval/` 模块及指定环境的现有标准库/依赖；配置预检读取引用的模型配置、用例及合成录制。L2 尝试读取配置指定的 `tests/results/l2-device/tools_capture.json`，文件是否存在以命令原始输出为准。
- 已在本组 `sandbox/` 执行 `PYTHONDONTWRITEBYTECODE=1` 加指定解释器的 `-B` 参数运行 `../outputs/run_preflight.py`，诊断脚本退出 0。完整绝对调用路径见本轮终端记录，脚本中 9 条产品命令的原始输出已分别落盘。
- 执行后通过读取工具核验 `outputs/preflight-verification.json`、`03-l1-device-dry-run.stderr.txt`、`04-l2-device-dry-run.stderr.txt` 和 `07-catalog-dry-run.stdout.txt`，据此生成 `outputs/answer.md`。最终回读本组答案、访问记录及已生成产物目录，核对交付内容。

## 当前交接

已执行 9 条本地预检命令。L1/L2 dry-run 分别因空设备号和引用的工具文件不存在退出 2；P01/P05 的 show-call 退出 2，确认设备动作不支持；回放预检计划 8 条、执行 0；采集 dry-run 仅列出 8 服务的 16 个文件计划，设备未配置、执行 0、未测试实时 tools/list。36 个已检查输入前后哈希相同。没有执行真实 ADB/API、实际采集或合成回放批次。最小下一步是取得设备身份和有来源的完整工具定义，再做本地配置副本预检。token 与总耗时未知，不估算。
