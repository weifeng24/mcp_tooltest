# 实际命令与输出索引

以下是助手已执行命令的留存记录，不是要求用户重新执行的步骤。终端为本机 Ubuntu Bash，所有命令的工作目录均显式设置为：

```text
/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-7-preflight-plan/with_skill/sandbox
```

`../outputs/` 指本组与 sandbox 同级的产物目录。命令中的 `>` 将标准输出写入指定文件，`2>` 单独保存标准错误；空 stderr 表示本次未输出错误文本，不等于设备通过验证。`env` 的变量设置仅作用于该条命令及其子进程；`PYTHONPATH=src` 使用本组源码，`PYTHONDONTWRITEBYTECODE=1` 禁止字节码写入，`MCP_EVAL_PYTHON` 为环境自检指定解释器。

## 路径和文件类型检查

执行前曾用 `ls -ld . ../outputs` 确认父目录存在，结果在工具会话中返回。以下为之后再次检查并直接留存的命令：

```bash
ls -ld . ../outputs > ../outputs/00-path-check.stdout.txt 2> ../outputs/00-path-check.stderr.txt
```

```bash
stat -c '%F %h %n' configs/servers/ark_mcp_service.json skills/mcp-eval/SKILL.md > ../outputs/00-file-scope.stdout.txt 2> ../outputs/00-file-scope.stderr.txt
```

## 帮助及本机自检

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src bash skills/mcp-eval/scripts/check_env.sh --help > ../outputs/01-check-env-help.stdout.txt 2> ../outputs/01-check-env-help.stderr.txt
```

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval --help > ../outputs/02-cli-help.stdout.txt 2> ../outputs/02-cli-help.stderr.txt
```

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src MCP_EVAL_PYTHON=/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python bash skills/mcp-eval/scripts/check_env.sh > ../outputs/03-check-env.stdout.txt 2> ../outputs/03-check-env.stderr.txt
```

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval checklist --help > ../outputs/04-checklist-help.stdout.txt 2> ../outputs/04-checklist-help.stderr.txt
```

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval capture-catalog --help > ../outputs/05-capture-help.stdout.txt 2> ../outputs/05-capture-help.stderr.txt
```

## 配置修改前记录

```bash
sha256sum configs/servers/ark_mcp_service.json skills/mcp-eval/SKILL.md > ../outputs/06-input-hashes-before.stdout.txt 2> ../outputs/06-input-hashes-before.stderr.txt
```

随后使用 `apply_patch`，仅修改本组 server 的 `device_serial` 并在 outputs 保存原值。文件编辑不通过 shell 脚本执行。

## 生成清单与离线计划

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval checklist > ../outputs/07-checklist.stdout.txt 2> ../outputs/07-checklist.stderr.txt
```

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval capture-catalog configs/servers/ark_mcp_service.json --service MCPVehicleService --dry-run > ../outputs/08-capture-catalog-dry-run.stdout.json 2> ../outputs/08-capture-catalog-dry-run.stderr.txt
```

`--service MCPVehicleService` 将计划限定为该服务，`--dry-run` 仅生成文件读取计划，不执行 adb。checklist 输出中的设备操作只是文本，未当作 shell 命令执行。

## 修改和日志核查

```bash
sha256sum ../outputs/server-before.json configs/servers/ark_mcp_service.json skills/mcp-eval/SKILL.md > ../outputs/09-input-hashes-after.stdout.txt 2> ../outputs/09-input-hashes-after.stderr.txt
```

```bash
diff -u ../outputs/server-before.json configs/servers/ark_mcp_service.json > ../outputs/10-server-diff.stdout.txt 2> ../outputs/10-server-diff.stderr.txt
```

```bash
wc -c ../outputs/*.stderr.txt > ../outputs/11-stderr-sizes.stdout.txt 2> ../outputs/11-stderr-sizes.stderr.txt
```

`sha256sum` 留存内容摘要；`diff -u` 留存带上下文的实际差异，输出唯一序列号变更是预期结果；`wc -c` 记录各 stderr 文件的字节数。工具返回未单独展示各命令退出码，未补造退出码；本报告结论依据实际 stdout/stderr、哈希与差异。
