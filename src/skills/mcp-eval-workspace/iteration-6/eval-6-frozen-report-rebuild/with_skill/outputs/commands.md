# 执行命令与输出

终端为 Ubuntu Bash。所有命令工作目录均为本组 `sandbox/`：

```text
/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-6-frozen-report-rebuild/with_skill/sandbox
```

所有 Python 命令使用用户指定解释器，`PYTHONPATH=src`；另设 `PYTHONDONTWRITEBYTECODE=1`，避免导入时创建字节码文件。`../outputs/` 为本组证据目录。以下是助手实际执行记录，不要求用户重复执行。

## 00a：确认本组与 sandbox 目录

```bash
ls -ld -- "/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-6-frozen-report-rebuild/with_skill" "/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-6-frozen-report-rebuild/with_skill/sandbox"
```

退出码 0。工具返回的 stdout 原样转存至 `00a-directory.stdout.txt`；stderr 无内容，保存空文件。此命令发生于建立日志文件之前。

## 00b：确认输出与批次目录

```bash
ls -ld -- ../outputs fixtures/rebuild-batch fixtures/rebuild-batch/artifacts
```

退出码 0。工具返回的 stdout 原样转存至 `00b-directory.stdout.txt`；stderr 无内容，保存空文件。

## 01—11：重建与证据核验

下列命令的 stdout/stderr 均通过重定向直接保存。SHA-256 命令的 stdout 使用 `.sha256` 扩展名；空 stderr 文件表示该命令没有标准错误输出。每条命令独立执行，哈希快照先于任何评测器执行，重建后才进行后哈希与一致性检查。

| 编号 | 操作 | 退出码 | stdout | stderr |
|---|---|---|---|---|
| 01 | 不变文件前哈希 | 0 | `01-immutable-before.sha256` | `01-immutable-before.stderr.txt` |
| 02 | 过期报告前哈希 | 0 | `02-reports-before.sha256` | `02-reports-before.stderr.txt` |
| 03 | 环境脚本帮助 | 0 | `03-env-help.stdout.txt` | `03-env-help.stderr.txt` |
| 04 | 评测器帮助 | 0 | `04-cli-help.stdout.txt` | `04-cli-help.stderr.txt` |
| 05 | 本机环境自检 | 0 | `05-env-check.stdout.txt` | `05-env-check.stderr.txt` |
| 06 | rebuild 帮助 | 0 | `06-rebuild-help.stdout.txt` | `06-rebuild-help.stderr.txt` |
| 07 | 目标批次重建（一次） | 0 | `07-rebuild.stdout.txt` | `07-rebuild.stderr.txt` |
| 08 | 不变文件后哈希 | 0 | `08-immutable-after.sha256` | `08-immutable-after.stderr.txt` |
| 09 | 重建报告后哈希 | 0 | `09-reports-after.sha256` | `09-reports-after.stderr.txt` |
| 10 | 与前哈希逐文件校验 | 0 | `10-immutable-check.stdout.txt` | `10-immutable-check.stderr.txt` |
| 11 | 批次证据与统计独立核验 | 0 | `11-verify.stdout.json` | `11-verify.stderr.txt` |

### 01

```bash
sha256sum fixtures/rebuild-batch/manifest.json fixtures/rebuild-batch/results.jsonl fixtures/rebuild-batch/recording-input.jsonl fixtures/rebuild-batch/artifacts/*.json src/mcp_eval/*.py src/mcp_eval/providers/*.py skills/mcp-eval/SKILL.md skills/mcp-eval/references/*.md skills/mcp-eval/scripts/check_env.sh > ../outputs/01-immutable-before.sha256 2> ../outputs/01-immutable-before.stderr.txt
```

### 02

```bash
sha256sum fixtures/rebuild-batch/summary.json fixtures/rebuild-batch/report.md > ../outputs/02-reports-before.sha256 2> ../outputs/02-reports-before.stderr.txt
```

### 03

```bash
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 bash skills/mcp-eval/scripts/check_env.sh --help > ../outputs/03-env-help.stdout.txt 2> ../outputs/03-env-help.stderr.txt
```

### 04

```bash
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -m mcp_eval --help > ../outputs/04-cli-help.stdout.txt 2> ../outputs/04-cli-help.stderr.txt
```

### 05

```bash
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 MCP_EVAL_PYTHON="/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" bash skills/mcp-eval/scripts/check_env.sh > ../outputs/05-env-check.stdout.txt 2> ../outputs/05-env-check.stderr.txt
```

### 06

```bash
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -m mcp_eval rebuild --help > ../outputs/06-rebuild-help.stdout.txt 2> ../outputs/06-rebuild-help.stderr.txt
```

### 07

```bash
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -m mcp_eval rebuild fixtures/rebuild-batch > ../outputs/07-rebuild.stdout.txt 2> ../outputs/07-rebuild.stderr.txt
```

重建退出码 0 表示报告生成完成，本批结果仍包含失败与无法判断；不能把该退出码解读为全部评测条目通过。

### 08

```bash
sha256sum fixtures/rebuild-batch/manifest.json fixtures/rebuild-batch/results.jsonl fixtures/rebuild-batch/recording-input.jsonl fixtures/rebuild-batch/artifacts/*.json src/mcp_eval/*.py src/mcp_eval/providers/*.py skills/mcp-eval/SKILL.md skills/mcp-eval/references/*.md skills/mcp-eval/scripts/check_env.sh > ../outputs/08-immutable-after.sha256 2> ../outputs/08-immutable-after.stderr.txt
```

### 09

```bash
sha256sum fixtures/rebuild-batch/summary.json fixtures/rebuild-batch/report.md > ../outputs/09-reports-after.sha256 2> ../outputs/09-reports-after.stderr.txt
```

### 10

```bash
sha256sum --check ../outputs/01-immutable-before.sha256 > ../outputs/10-immutable-check.stdout.txt 2> ../outputs/10-immutable-check.stderr.txt
```

### 11

```bash
env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 "/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" ../outputs/verify_rebuild.py > ../outputs/11-verify.stdout.json 2> ../outputs/11-verify.stderr.txt
```

该脚本仅核对本次文件证据，不读取其他 fixture 内容或评测评分标准，不重新执行产品评测。输出中的 `attempted_metadata_consistent: false` 明示原 manifest 的执行计数与逐项状态不一致，未改写原始记录。
