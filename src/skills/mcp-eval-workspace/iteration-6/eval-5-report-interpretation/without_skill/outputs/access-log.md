# 无目标 Skill 基线访问记录

## 1. 边界与路径

- 本组根目录 W：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-5-report-interpretation/without_skill`。
- 交付根 S：`W/sandbox`；所有终端命令均以 S 为工作目录。
- 唯一实际写入目录 O：`W/outputs`。
- 本任务为固定报告批次的只读解读，未修改输入、产品或共享记忆，未连接设备／API、安装包或提交版本。
- 日期：2026-10-23。没有估算 token、执行耗时或其他未取得的计量数据。

## 2. sandbox 之外的上下文与额外访问

| 内容／路径 | 方式与范围 | 原因与影响 |
|---|---|---|
| 项目根 `AGENTS.md` | 由上层会话上下文直接提供，未额外打开文件 | 必须遵守项目约束，包括强制索引／记忆读取。 |
| `/home/tssh/文档/Works/mission/校招生ai演练任务/docs/README.md` | Read 全文，68 行 | 上层强制资料索引读取。包含公司要求、评分口径入口及历史工作摘要；未沿链接打开框架、评分材料或历史报告。 |
| `/home/tssh/文档/Works/mission/校招生ai演练任务/memory/CURRENT.md` | Read 全文，98 行 | 上层强制记忆读取。含历史评测与 Skill 对照摘要，必须披露这一已有上下文暴露；未将其作为本批结果依据，也未沿链接读取历史评测。 |
| `/home/tssh/.config/opencode/addyosmani-skills/skills/using-agent-skills/SKILL.md` | `skill` 工具加载正文 | 通用会话工作流 Skill；本次会话开始时按上层技能指令加载。未读取其 references。 |
| `/home/tssh/.config/opencode/superpowers-skills/skills/verification-before-completion/SKILL.md` | `skill` 工具加载正文 | 通用完成前核验 Skill；要求先取得实际核对输出再声明完成。未读取其 references。 |
| `/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python` | 执行指定解释器及其标准库 | 用户指定运行环境；使用 `-I -B -S`，未读取该历史整改目录中的报告、结果或测试材料。 |

本次是“无目标 Skill”条件，存在上述两项通用 Skill 和强制索引／记忆上下文，不能表述为无任何 Skill 或完全无历史摘要暴露。目标 `mcp-eval` Skill 及其 references、其他组文件、历史评测正文和评分标准正文均未主动读取。索引、记忆和本组 README 中出现的相关链接没有继续打开。

## 3. 本组目录与路径枚举

| 操作 | 路径与实际范围 |
|---|---|
| Read 目录 | W：看到 `input-hashes-before.json`、`outputs/`、`sandbox/`、`timing.json` 的名称；未读取两个 JSON 文件内容。 |
| Read 目录 | O：初始为空；S：查看顶层目录名称。 |
| Read 目录 | `S/fixtures/report-batch`、`S/src`、`S/configs`：定位本批证据、源码和配置。 |
| Glob `**/*.py` | 限 `S/src/mcp_eval`；枚举 14 个 Python 文件路径，未因此读取全部正文。 |
| Glob `*.json` | 限 `S/configs/runs`；枚举 `replay_smoke.json`、`l1_device.json`、`l2_device.json`。仅打开 replay 配置。 |
| Bash C1 | 在 S 执行 `ls -ld -- . ../outputs`，确认目录和输出位置；见 `directory-check.stdout.txt`。 |

没有枚举其他评测组或历史评测目录。

## 4. 本组内容读取与用途

以下路径均相对 S。

| 路径 | 实际访问 | 用途 |
|---|---|---|
| `README.md` | Read 全文；C2 读取字节计算摘要 | 确认统计口径、数据来源边界及输出定义。包含的历史概述未作为本批证据，未打开其历史链接。 |
| `fixtures/report-batch/manifest.json` | Read 全文；C2 JSON 解析 | 固定计划、正负分类、冻结断言、配置、来源与摘要。 |
| `fixtures/report-batch/results.jsonl` | Read；C2 完整 JSONL 解析 | 逐项状态、判定、缺证据原因、来源和后置回读。Read 中第 4／5／8 行超过工具显示长度，后续由 C2 完整解析，无截断统计。 |
| `fixtures/report-batch/report.md` | Read 全文；C2 内容比对 | 核对展示值与逐项判定。 |
| `fixtures/report-batch/summary.json` | Read 全文；C2 全字段比对 | 核对分组比例、判定覆盖率、失败类别和空时延样本。 |
| `fixtures/report-batch/recording-input.jsonl` | Read 全文；C2 解析与摘要比对 | 核对来源；发现 N02、P05 与当前结果不同。未据此重放或覆盖结果。 |
| `fixtures/report-batch/artifacts/item-00002.json`、`item-00007.json` | Read 全文；C2 对应对象比对 | 核对失败与未完成项。 |
| `fixtures/report-batch/artifacts/item-00004.json` | Read 全文；C2 对应对象比对 | 查看一条完整的后置状态回读结构。 |
| `fixtures/report-batch/artifacts/item-00001.json`、`item-00003.json`、`item-00005.json`、`item-00006.json`、`item-00008.json` | 仅 C2 完整 JSON 解析 | 与结果逐项比对，不调用工具。 |
| `configs/runs/replay_smoke.json` | Read 全文；C2 JSON 比对 | 确认单次 L1 合成回放配置及空模型列表；用冻结配置作比对依据。 |
| `src/mcp_eval/report.py` | Read 全文；Grep 命中；C2 摘要比对 | 明确固定分母、缺结果保留与分组公式。 |
| `src/mcp_eval/judge.py` | Read 全文；Grep 命中；C2 摘要比对 | 核对 `error_expected`、缺证据判定与后置条件含义。 |
| `src/mcp_eval/runner.py` | Grep；Read 第 200–319 行；C2 读取全文字节计算摘要 | 明确尝试计数与批次收尾语义。未导入或执行源码。 |

一次 Grep 请求指定 `src/mcp_eval/runner.py`，模式为 `attempted_items|recorded_items|state.*finished|not_run|executed`。工具实际搜索范围扩展到其包目录，返回 27 个匹配，涉及 `__main__.py`、`report.py`、`judge.py`、`records.py`、`runner.py`、`model_loop.py`、`catalog.py`。这些额外匹配均位于本组允许的产品源码内；除上表列明文件外没有继续阅读全文。

C2 的精确字节读取清单见 `check-report.stdout.json.input_files`，共 18 个文件；每个均在核对结束时再次读取比较原字节。C3 再次读取这同一组文件，检查交付前内容摘要保持一致。源码的字节摘要读取不等于执行或完整源码审查。

结果中的工作区外绝对路径及 `baseline_tree` 仅作为输入字符串出现，未跟随读取 `/data`、原工作区录制或外部产品源码。

## 5. 写入、命令与产物回读

所有写入均在 O 内。

| 产物 | 产生方式／用途 |
|---|---|
| `check_report.py` | apply_patch 新建；独立只读统计及文件比对脚本，仅使用标准库。 |
| `directory-check.stdout.txt` | apply_patch 将 C1 终端返回原文逐字转存。 |
| `check-report.stdout.json`、`check-report.stderr.txt` | C2 直接捕获标准输出／标准错误；已 Read 全文，退出状态为 0，标准错误为空。 |
| `answer.md` | apply_patch 新建；本批报告解读。 |
| `access-log.md` | apply_patch 新建；本访问记录。 |
| `commands.md` | apply_patch 新建；C1、C2、C3 的完整命令、工作目录及输出入口。 |
| `final-check.stdout.json`、`final-check.stderr.txt` | C3 直接捕获交付核对的标准输出／标准错误；实际值见文件。 |

最终核对读取 O 内的答案、访问记录、命令记录、脚本和原始输出；随后通过 Read 检查答案、访问记录、命令及最终原始输出。原始 stdout／stderr 文件不做手工改写。未写入目标 Skill、输入目录、产品目录、共享 memory 或 W 下其他位置。

## 6. 结论依赖范围

报告数量、比例、未完成项和来源边界仅依据本组冻结 manifest、results、summary、report、artifacts、随附录制及相关源码／配置。索引、记忆和通用 Skill 仅影响协作及核对流程，未用于填补本批证据缺失。本次没有重新运行 MCP 工具、产品回放、产品判定器或测试套件。
