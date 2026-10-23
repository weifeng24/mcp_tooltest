# 实际访问与命令记录

## 1. 路径、边界与记录口径

- 项目根（R）：`/home/tssh/文档/Works/mission/校招生ai演练任务`
- 本组唯一可写目录（W）：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-2-missing-evidence/with_skill`
- 本组交付根（S）：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-2-missing-evidence/with_skill/sandbox`
- 实际输出目录：`W/outputs/`。
- 全部 4 条终端命令均使用 **Ubuntu Bash**，工具的 `workdir` 显式设置为 S；Python 使用用户指定的解释器。没有运行安装、提交、设备连接或模型 API 请求命令。
- 下表中的 R/W/S 只是路径缩写，不是用户需要设置的环境变量。记录显式读取、Skill 加载和命令；不声称进行了系统调用级文件访问审计。黑盒脚本及 Python 导入所需的运行时文件不逐一展开。
- 原始命令输出保存在 `outputs/raw/`，按终端工具返回的完整文本保存，未删节。工具消息未单独给出 stdout/stderr 分流及数值退出码，因此不补造这些字段；4 条命令均正常返回，未报告命令失败。
- token 用量、总耗时未知，未读取或改写预置 `timing.json`，未作估算。

## 2. 实际读取顺序

首个工具调用读取本组 `S/skills/mcp-eval/SKILL.md`。并行组内序号用于索引，不表示精确的完成时序。

| 序号 / 组 | 方式 | 实际位置 | 读取内容与用途 |
|---|---|---|---|
| R01 | read | `S/skills/mcp-eval/SKILL.md` | 全文 70 行；本组执行规则，首先读取 |
| R02 / A | skill | `/home/tssh/.config/opencode/addyosmani-skills/skills/using-agent-skills/SKILL.md` | 上层会话工作流要求；工具返回 Skill 正文 |
| R03 / A | skill | `/home/tssh/.config/opencode/anthropic-skills/skills/skill-creator/SKILL.md` | 用户要求的 Creator 评测流程；工具返回正文及资源路径列表，未打开 grader/analyzer 或评分文件 |
| R04 / A | read | `R/docs/README.md` | 全文 68 行；项目规则强制读取的索引，存在污染 |
| R05 / A | read | `R/memory/CURRENT.md` | 全文 98 行；项目规则强制读取的记忆，存在污染 |
| R06 / A | read（目录） | `W/` | 仅返回 `input-hashes-before.json`、`outputs/`、`sandbox/`、`timing.json` 四个名称 |
| R07 / A | read | `S/fixtures/missing-evidence.json` | 全文 12 行；唯一被解释的样本 |
| R08 / A | read | `S/skills/mcp-eval/references/report-guide.md` | 全文 12 行；判定与指标规则 |
| R09 / A | read | `S/skills/mcp-eval/references/troubleshooting.md` | 全文 16 行；提供方错误与重建边界 |
| R10 / B | read（目录） | `W/outputs/` | 初始为空；确认输出目录现状 |
| R11 / B | read（目录） | `S/` | 返回本组交付根的 9 个直接条目；未递归读取其他 fixture |
| R12 / B | read | `S/README.md` | 全文 195 行；本组运行说明，自带历史摘要的曝光见第 3 节 |
| R13 / B | skill | `/home/tssh/.config/opencode/superpowers-skills/skills/verification-before-completion/SKILL.md` | 完成前验证工作流；工具返回 Skill 正文 |
| R14 | read | `W/input-hashes-before.json` | 全文 30 行；本组预置哈希清单。包含其他 fixture 的名称及哈希，没有读取这些 fixture 正文；只使用 `missing-evidence.json` 条目 |
| R15 / V | read | `W/outputs/answer.md` | 全文 54 行；确认已保存复核结论、计数、处理方式与边界 |
| R16 / V | read | `W/outputs/access-log.md` | 补记前全文 96 行；确认已保存读取、污染及命令记录，随后追加本次回读事实 |
| R17 / V | read | `W/outputs/raw/01-check-env-help.txt` | 全文 3 行；与 C01 返回文本逐项核对 |
| R18 / V | read | `W/outputs/raw/02-cli-help.txt` | 全文 17 行；与 C02 返回文本逐项核对 |
| R19 / V | read | `W/outputs/raw/03-check-env.txt` | 全文 7 行；与 C03 返回文本逐项核对 |
| R20 / V | read | `W/outputs/raw/04-fixture-integrity.txt` | 全文 3 行；与 C04 返回文本逐项核对 |

上层自动注入了根目录 `AGENTS.md`、环境信息及可用 Skill 描述；没有另行读取 `AGENTS.md` 文件。没有打开 `memory/DECISIONS.md`、其他组目录、历史评测产物或实际评分标准文件。

## 3. 上下文污染记录

1. **强制索引污染：** R04 包含项目历史验证摘要、历史资料入口及公司评分权重速查。读取来自上层项目规则第 7 节，也符合用户“强制读索引记忆则照办记录污染”的例外。没有跟进其中链接。
2. **强制记忆污染：** R05 含旧评测分数、历史判定缺陷及整改摘要。其影响不能保证完全排除，因此不宣称独立盲评；未将旧分数、修复状态或历史结果作为此样本判定依据。
3. **本组说明中的历史摘要：** R12 的项目 README 自带旧测试与整改摘要；根据本组 Skill 的入口要求读取，未打开其引用的历史报告或其他评测文件。
4. **外部通用工作流：** R02、R03、R13 来自已安装 Skill，属于 sandbox 外部的通用指导上下文。未加载外部 `mcp-eval` 副本；实际判定依据为 R01、R07、R08、R09。
5. **预置哈希清单元数据：** R14 曝光本组其他 fixture 的名称和校验值，不含其内容或评分断言；命令 C04 只读取目标 fixture 的字节作完整性校验。

## 4. 实际命令与原始输出

以下均为已执行命令的记录，不是要求用户重复执行的步骤。

### C01：环境脚本帮助

终端：Ubuntu Bash。`workdir=S`。与 C02 并行执行；先查询脚本支持的解释器选择方式。

```bash
bash skills/mcp-eval/scripts/check_env.sh --help
```

原始输出：[raw/01-check-env-help.txt](raw/01-check-env-help.txt)。帮助明确支持 `MCP_EVAL_PYTHON`。

### C02：评测 CLI 帮助

终端：Ubuntu Bash。`workdir=S`。`PYTHONPATH=src` 指向本组源码；`-B` 和 `PYTHONDONTWRITEBYTECODE=1` 禁止写入 Python 字节码缓存。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -B -m mcp_eval --help
```

原始输出：[raw/02-cli-help.txt](raw/02-cli-help.txt)。显示 `run`、`gen-config`、`checklist`、`show-call`、`rebuild`、`capture-catalog` 帮助，未执行这些子命令。

### C03：本机环境自检

终端：Ubuntu Bash。`workdir=S`。在 C01 返回后执行，按帮助传入指定解释器并禁用字节码缓存。

```bash
PYTHONDONTWRITEBYTECODE=1 MCP_EVAL_PYTHON="/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" bash skills/mcp-eval/scripts/check_env.sh
```

原始输出：[raw/03-check-env.txt](raw/03-check-env.txt)。确认 Python、依赖和交付根；提示 adb 命令存在，但未验证设备连接。仅输出密钥是否设置，没有显示密钥值。脚本按黑盒执行，没有打开实现阅读；结果只支持本机基础环境结论。

### C04：目标 fixture 完整性校验

终端：Ubuntu Bash。`workdir=S`。专用读取工具不提供 SHA-256 校验，故使用指定解释器只读计算；预期值来自 R14 的目标条目。命令不写文件。

```bash
"/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -B -c 'import hashlib, sys; from pathlib import Path; p = Path("fixtures/missing-evidence.json"); expected = "939ab51fa2bf63ce3472f62ce3b7f00153369dc60d4bc1cf53470fdab3584cf6"; actual = hashlib.sha256(p.read_bytes()).hexdigest(); print("fixture=" + str(p)); print("sha256=" + actual); print("matches_initial_record=" + str(actual == expected).lower()); sys.exit(0 if actual == expected else 1)'
```

原始输出：[raw/04-fixture-integrity.txt](raw/04-fixture-integrity.txt)。`matches_initial_record=true`，证明目标 fixture 与组内预置哈希相符；没有将此校验扩大为所有产品文件的哈希验证。

## 5. 写入记录与结果

所有文件变更均通过 `apply_patch` 完成，位于 `W/outputs/`：

- C01、C02 完成后保存 `raw/01-check-env-help.txt`、`raw/02-cli-help.txt`。
- C03、C04 完成后保存 `raw/03-check-env.txt`、`raw/04-fixture-integrity.txt`、`answer.md` 和本文件。
- 本次文档复核结论为 `unassessed`；没有运行产品判定器生成新批次，也没有把人工复核伪装成自动重建结果。
- 未修改原始 fixture、Skill、产品或根目录记忆；未安装依赖、提交代码、连接设备或请求模型 API。
- R15—R20 回读确认六个产物存在且内容可读，四份原始输出与对应工具返回文本一致；随后仅通过 `apply_patch` 给本文件补记这些已执行的回读。没有新增终端命令。
