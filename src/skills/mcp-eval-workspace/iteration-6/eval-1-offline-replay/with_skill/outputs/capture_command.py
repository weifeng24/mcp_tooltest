"""在本组 sandbox 执行命令，逐字节保存标准输出、标准错误与退出码。"""

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def main():
    output_dir = Path(__file__).resolve().parent
    sandbox = output_dir.parent / "sandbox"
    if Path.cwd().resolve() != sandbox.resolve():
        raise SystemExit("工作目录必须为本组 sandbox")
    if os.environ.get("PYTHONPATH") != "src":
        raise SystemExit("必须设置 PYTHONPATH=src")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("必须设置 PYTHONDONTWRITEBYTECODE=1")
    if len(sys.argv) < 3 or not re.fullmatch(r"[a-zA-Z0-9-]+", sys.argv[1]):
        raise SystemExit("用法：capture_command.py LABEL COMMAND [ARGS...]")

    label, command = sys.argv[1], sys.argv[2:]
    stdout_path = output_dir / f"{label}.stdout.txt"
    stderr_path = output_dir / f"{label}.stderr.txt"
    metadata_path = output_dir / f"{label}.execution.json"
    for path in (stdout_path, stderr_path, metadata_path):
        if path.exists():
            raise SystemExit(f"拒绝覆盖已有证据：{path}")

    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        completed = subprocess.run(command, stdout=stdout, stderr=stderr, check=False)

    metadata = {
        "cwd": str(sandbox),
        "argv": command,
        "command": shlex.join(command),
        "launcher": shlex.join([sys.executable, *sys.argv]),
        "environment": {
            "PYTHONPATH": "src",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        "returncode": completed.returncode,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with (output_dir / "access-log.md").open("a", encoding="utf-8") as stream:
        stream.write(
            f"\n## 命令 {label}\n\n"
            f"- 工作目录：`{sandbox}`\n"
            "- 环境：`PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1`\n"
            f"- 捕获入口：`{metadata['launcher']}`\n"
            f"- 实际命令：`{metadata['command']}`\n"
            f"- 返回码：`{completed.returncode}`\n"
            f"- 原始 stdout：`{stdout_path.name}`\n"
            f"- 原始 stderr：`{stderr_path.name}`\n"
            f"- 执行元数据：`{metadata_path.name}`\n"
            "- 捕获脚本读取上述两份原始输出并原样转发到执行工具。\n"
        )
    sys.stdout.buffer.write(stdout_path.read_bytes())
    sys.stderr.buffer.write(stderr_path.read_bytes())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
