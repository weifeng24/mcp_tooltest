# 已执行核对命令与原始输出

## 执行环境

- 终端：Ubuntu Bash。
- 所有命令的 `workdir`：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/skills/mcp-eval-workspace/iteration-6/eval-5-report-interpretation/without_skill/sandbox`。
- 写入目录：上述目录的同级 `../outputs/`。
- Python：`/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python`。
- `-I` 隔离 Python 环境变量及用户级模块路径，`-B` 禁止字节码缓存写入，`-S` 不加载 site 初始化。核对只使用标准库。
- 下列命令用于本次已保存文件的核算及产物核对；未调用产品 CLI、回放器、设备或模型 API。

## C1：确认工作目录与输出目录

```bash
ls -ld -- . ../outputs
```

退出状态 0。原始输出保存为 [directory-check.stdout.txt](directory-check.stdout.txt)，内容从终端工具返回逐字转存；终端未报告错误。这里 `.` 是 sandbox，`../outputs` 是唯一写入位置。

## C2：独立只读核算

```bash
"/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -I -B -S "../outputs/check_report.py" > "../outputs/check-report.stdout.json" 2> "../outputs/check-report.stderr.txt"
```

退出状态 0。标准输出和标准错误由终端直接重定向保存，未经摘要或手工改写：

- [check-report.stdout.json](check-report.stdout.json)：计算结果、17 项一致性检查、逐项证据投影、录制差异、18 个读取文件的字节数和 SHA-256 内容摘要。
- [check-report.stderr.txt](check-report.stderr.txt)：空文件。

`>` 保存标准输出，`2>` 保存标准错误；执行时这些目标文件尚不存在。脚本只读输入并输出 JSON，不执行产品调用或产品判定器。

## C3：交付文件及输入保持性核对

```bash
"/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -I -B -S -c 'import hashlib, json; from pathlib import Path; root = Path.cwd(); out = root.parent / "outputs"; audit = json.loads((out / "check-report.stdout.json").read_text()); names = ["answer.md", "access-log.md", "commands.md", "check_report.py", "directory-check.stdout.txt", "check-report.stdout.json", "check-report.stderr.txt"]; files = {name: (out / name).read_bytes() for name in names}; unchanged = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() == metadata["sha256"] for name, metadata in audit["input_files"].items()}; checks = {"audit_exit_status_zero": audit["exit_status"] == 0, "audit_checks_true": all(audit["checks"].values()), "all_18_inputs_unchanged": len(unchanged) == 18 and all(unchanged.values()), "required_outputs_nonempty": all(files[name] for name in names if name != "check-report.stderr.txt"), "audit_stderr_empty": files["check-report.stderr.txt"] == b""}; status = 0 if all(checks.values()) else 1; print(json.dumps({"checks": checks, "input_hashes_unchanged": unchanged, "output_files": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in files.items()}, "exit_status": status}, ensure_ascii=False, indent=2)); raise SystemExit(status)' > "../outputs/final-check.stdout.json" 2> "../outputs/final-check.stderr.txt"
```

实际核对值及退出状态见 [final-check.stdout.json](final-check.stdout.json)；标准错误见 [final-check.stderr.txt](final-check.stderr.txt)。该命令重新读取 C2 已核对的 18 个输入，比较其内容摘要，并检查本次交付文件；不会新增产品测试。
