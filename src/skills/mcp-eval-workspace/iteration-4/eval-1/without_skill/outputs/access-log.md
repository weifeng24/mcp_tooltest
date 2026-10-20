# 场景 1 without_skill 访问日志

## 路径约定与审计范围

以下前缀是精确路径缩写，不是待替换的执行命令：

- `R` = `/home/tssh/文档/Works/mission/校招生ai演练任务`
- `D` = `/home/tssh/文档/Works/mission/校招生ai演练任务/src`
- `B` = `/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/replay-smoke-20261020T082452120070Z-235a47c8`
- `O` = `/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-4/eval-1/without_skill/outputs`

本日志完整列出本轮助手显式工具访问、命令、项目层运行输入及产物。程序内部读取依据已查看的公共代码与新批次 manifest 记录整理；未进行系统调用跟踪，不声称枚举 Python 标准库、第三方依赖及操作系统动态加载器的全部内部文件访问。

会话已自动提供 `R/AGENTS.md` 的项目规则文本；本轮未调用工具读取该文件。没有读取任何 Skill 指令文件，也没有调用 `functions.skill`。

## 1. 实际工具调用顺序

同一序号内通过 `multi_tool_use.parallel` 调度的是并行工具调用，不是子代理或任务委派。

| 顺序 | 工具 | 实际目标或操作 |
|---|---|---|
| 1 | `multi_tool_use.parallel` → 3 次 `functions.read` | `R/docs/README.md`；`R/memory/CURRENT.md`；`D/README.md` |
| 2 | `multi_tool_use.parallel` → 2 次 `functions.read` | 文件 `D/configs/runs/replay_smoke.json`；目录 `D/src/mcp_eval/`（只返回目录条目） |
| 3 | `multi_tool_use.parallel` → 4 次 `functions.read` | `D/src/mcp_eval/__main__.py`；`D/src/mcp_eval/runner.py`；`D/src/mcp_eval/config.py`；`D/src/mcp_eval/records.py` |
| 4 | `multi_tool_use.parallel` → 2 次 `functions.read`、1 次 `functions.bash` | `D/src/mcp_eval/replay.py`；`D/src/mcp_eval/report.py`；下列命令 C1 |
| 5 | `functions.bash` | 下列命令 C2，仅一次正式回放 |
| 6 | `multi_tool_use.parallel` → 4 次 `functions.read`、1 次 `functions.glob` | `B/manifest.json`；`B/summary.json`；`B/report.md`；`B/results.jsonl`；在 `D/tests/cases/l1/` 中匹配 `*.json`，仅取得文件路径 |
| 7 | `multi_tool_use.parallel` → 4 次 `functions.read`、1 次 `functions.bash` | `B/recording-input.jsonl`；`B/artifacts/item-00004.json`；`B/artifacts/item-00005.json`；`B/artifacts/item-00008.json`；下列命令 C3 |
| 8 | `functions.apply_patch` | 一次补丁新增 `O/answer.md` 和 `O/access-log.md`，不回读输出 |

`results.jsonl` 的第 4、5、8 行在 Read 展示中被长行截断，因此随后读取对应的三个完整 artifact。其余结果行、manifest、summary、report 和输入副本均由 Read 返回完整内容。

## 2. Ubuntu Bash 实际命令

三条命令的工作目录均显式设为 `D`，即 `/home/tssh/文档/Works/mission/校招生ai演练任务/src`。

### C1：核实产物父目录与指定解释器

```bash
ls -ld "tests/results" "tests/results/remediation-2026-10-16/.venv/bin/python"
```

- 仅查看两个指定路径的元数据，不枚举历史批次内容。
- `tests/results` 为已有目录。
- 指定解释器路径为已有符号链接，指向 `python3`。
- 不产生文件。

### C2：创建唯一新回放批次

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval run configs/runs/replay_smoke.json
```

- 解释器执行路径：`D/tests/results/remediation-2026-10-16/.venv/bin/python`。
- Python 版本由新批次 manifest 记录为 `3.10.12`。
- 运行源码搜索路径：`D/src`；禁用字节码缓存写入。
- 仅调用一次 `run`；未另行调用 dry-run、rebuild、pytest、设备或模型命令。
- 命令返回新 `run_id=replay-smoke-20261020T082452120070Z-235a47c8`。
- 返回 `executed=8`、`pass=8`、`fail=0`、`unassessed=0`、`interrupted=false`、`warnings=[]`。
- 标准输出由工具会话保留；未另写终端日志文件。
- 程序写入范围为 `B/`；新批次目录由 `mkdir(..., exist_ok=False)` 创建。

### C3：核对输入副本内容摘要

```bash
sha256sum "recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl" "tests/results/replay-smoke-20261020T082452120070Z-235a47c8/recording-input.jsonl"
```

- 实际读取 `D/recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl` 与 `B/recording-input.jsonl`。
- 两者均返回 `0a18cffdb92afe1d683d88177f3821f27240bbcac5506d57457ce588e8bcc848`，与 `B/manifest.json` 一致。
- 不产生文件。

## 3. 程序内部读取的项目路径

### 3.1 运行输入

C2 的公共执行代码按配置加载以下文件。除运行配置外，服务配置和原始用例未由助手逐个调用 Read，而由运行程序读取，并在新 manifest 中冻结；助手已读取该 manifest。

1. `D/configs/runs/replay_smoke.json`
2. `D/configs/servers/ark_mcp_service.json`
3. `D/tests/cases/l1/N01_unknown_tool.json`
4. `D/tests/cases/l1/N02_param_out_of_range.json`
5. `D/tests/cases/l1/P01_tools_list.json`
6. `D/tests/cases/l1/P02_set_temp_valid.json`
7. `D/tests/cases/l1/P03_set_temp_boundary.json`
8. `D/tests/cases/l1/P04_voice_service_call.json`
9. `D/tests/cases/l1/P05_resources_read.json`
10. `D/tests/cases/l1/P06_set_temp_upper_boundary.json`
11. `D/recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl`

`functions.glob` 仅在 `D/tests/cases/l1/` 下枚举上列 8 个 JSON 文件名。C2 为校验、回放索引及保存输入副本读取录制文件；C3 再次读取它计算哈希。

### 3.2 公共源码读取及快照

C2 在 `D/src/mcp_eval/` 内递归读取以下 14 个 `.py` 文件计算 `engine_sources` 哈希。该遍历不进入 `skills/` 或 `skills-creator/`。

1. `D/src/mcp_eval/__init__.py`
2. `D/src/mcp_eval/__main__.py`
3. `D/src/mcp_eval/catalog.py`
4. `D/src/mcp_eval/config.py`
5. `D/src/mcp_eval/device.py`
6. `D/src/mcp_eval/judge.py`
7. `D/src/mcp_eval/model_loop.py`
8. `D/src/mcp_eval/providers/__init__.py`
9. `D/src/mcp_eval/providers/base.py`
10. `D/src/mcp_eval/providers/openai_compat.py`
11. `D/src/mcp_eval/records.py`
12. `D/src/mcp_eval/replay.py`
13. `D/src/mcp_eval/report.py`
14. `D/src/mcp_eval/runner.py`

程序导入设备、模型模块不等于执行外部调用；本次配置与执行分支为 `replay`、纯 L1、`model_refs=[]`。配置中出现的 `/data/AIOS_Ark_2026-dev/lagvm/LINUX/android/vendor/mcp` 和设备 dump 路径只作为元数据保存，没有访问这些位置。

### 3.3 新批次运行时回读

C2 收尾时读取自己生成的以下文件，重建结果并统计：

- `B/artifacts/item-00001.json`
- `B/artifacts/item-00002.json`
- `B/artifacts/item-00003.json`
- `B/artifacts/item-00004.json`
- `B/artifacts/item-00005.json`
- `B/artifacts/item-00006.json`
- `B/artifacts/item-00007.json`
- `B/artifacts/item-00008.json`
- `B/results.jsonl`
- `B/summary.json`

这是获准创建的新回放批次，不是 `skills/` 下的行为评测输出目录。未读取任何旧批次结果文件。

## 4. 产物完整路径列表

### 4.1 C2 生成的永久产物

1. `B/manifest.json`
2. `B/results.jsonl`
3. `B/summary.json`
4. `B/report.md`
5. `B/recording-input.jsonl`
6. `B/artifacts/item-00001.json`
7. `B/artifacts/item-00002.json`
8. `B/artifacts/item-00003.json`
9. `B/artifacts/item-00004.json`
10. `B/artifacts/item-00005.json`
11. `B/artifacts/item-00006.json`
12. `B/artifacts/item-00007.json`
13. `B/artifacts/item-00008.json`

新建目录为 `B/` 与 `B/artifacts/`。

公共代码的原子保存流程还在同批次内使用以下临时路径，并以 replace 转为对应最终文件；这些不是额外批次：

- `B/manifest.tmp`
- `B/results.jsonl.tmp`
- `B/artifacts/item-00001.tmp`
- `B/artifacts/item-00002.tmp`
- `B/artifacts/item-00003.tmp`
- `B/artifacts/item-00004.tmp`
- `B/artifacts/item-00005.tmp`
- `B/artifacts/item-00006.tmp`
- `B/artifacts/item-00007.tmp`
- `B/artifacts/item-00008.tmp`

### 4.2 助手写入的两份文档

仅使用 `functions.apply_patch` 新增：

1. `/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-4/eval-1/without_skill/outputs/answer.md`
2. `/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-4/eval-1/without_skill/outputs/access-log.md`

未列目录或读取这些输出，也未写入 grading 文件。

## 5. 隔离边界及实际暴露

- 启动时按会话已加载的项目级规则读取 `R/docs/README.md` 和 `R/memory/CURRENT.md`；其中包含历史审查及历史 Skill 行为结果摘要，`D/README.md` 也包含历史验证概述。本轮确实接触了这些摘要，不能声称完全隔离于历史结果。
- 未继续打开上述文件链接的审查报告、其他组输出、Skill 指令或评分期望文件；本次结果统计及来源核对均依据 C2 返回的新批次。
- `skills/`、`skills-creator/` 下没有 Read、Glob、Grep、终端读取或目录枚举；唯一区内操作为向 `O` 写入两份文档。
- 未运行 pytest；未连接设备或外部模型；未修改源码、配置、项目文档或交接记忆；未 commit；未委派；未调用任何 Skill；未运行评分。
