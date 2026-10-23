# N02 无目标 Skill 基线：访问与执行记录

## 1. 路径与任务边界

- 工作区根 `W`：`/home/tssh/文档/Works/mission/校招生ai演练任务`。
- 唯一写入目录 `G`：`W/src/skills/mcp-eval-workspace/iteration-6/eval-4-unexpected-success/without_skill`。
- 本组交付根 `S`：`G/sandbox`。下列产品路径均相对 `S`；所有 shell 命令工作目录均为 `S`。
- 任务：仅根据 `fixtures/anomaly.json` 分析 N02 越界参数返回成功；离线核验本组判定器。
- 所有新文件位于 `G/outputs/` 或 `G/access-log.md`，没有修改输入/产品、连接设备/API、安装依赖或提交版本。

## 2. 上层规则强制读取及额外访问

| 访问对象 | 方式与原因 | 暴露范围及用途 |
|---|---|---|
| `W/AGENTS.md` | 会话上层指令已加载，未另行读取磁盘文件 | 按其中索引读取、中文交付与开发区约束执行 |
| `W/docs/README.md` | `read` 全文；项目规则要求工作前读取 | 包含历史工作索引和公司评分权重摘要；没有继续打开历史报告或评分资料 |
| `W/memory/CURRENT.md` | `read` 全文；项目规则要求工作前读取 | 包含既往 Skill 评测得分与状态摘要；未打开链接指向的历史评测，未将摘要作为本次判据 |
| `using-agent-skills` | `skill` 加载；上层通用工作流要求 | 路径：`/home/tssh/.config/opencode/addyosmani-skills/skills/using-agent-skills/SKILL.md`；用于识别适用流程 |
| `debugging-and-error-recovery` | `skill` 加载；异常行为分析流程适用 | 路径：`/home/tssh/.config/opencode/addyosmani-skills/skills/debugging-and-error-recovery/SKILL.md`；用于保留证据、区分现象与根因 |
| `verification-before-completion` | `skill` 加载；完成前验证流程适用 | 路径：`/home/tssh/.config/opencode/superpowers-skills/skills/verification-before-completion/SKILL.md`；用于要求实际验证后再声明结果 |
| 指定 Python 解释器及现有运行库 | 执行用户明确指定的解释器；导入标准库、现有 `jsonschema` 及其依赖 | 解释器：`W/src/tests/results/remediation-2026-10-16/.venv/bin/python`。仅作为运行环境使用，没有读取该历史目录的评测报告或其他证据 |

**隔离说明：**未读取或使用目标 `mcp-eval` Skill 及其 `references`，未访问其他评测组。强制索引/记忆已经暴露历史摘要和部分得分，故本轮不能宣称完全无历史背景的盲评；这与继续访问历史评测内容不同。上述三个通用 Skill 已如实披露，不将本轮表述成“未使用任何 Skill”。

未另读 `memory/DECISIONS.md`：本次没有制定项目范围/方案或处理历史决定。没有修改共享记忆；此次独立情景的交接信息保存在唯一可写目录内。

## 3. 本组实际读取与搜索

| 顺序 | 访问路径或范围 | 工具与目的 |
|---|---|---|
| 1 | `G/` | `read` 目录；确认本组含 `sandbox/`、`outputs/`；仅看到 `input-hashes-before.json`、`timing.json` 文件名，未打开内容 |
| 2 | `S/`、`G/outputs/` | `read` 目录；确认交付根及初始空输出目录 |
| 3 | `S/README.md` | `read` 全文；核对源码位置、判定状态和输出语义。正文含项目历史摘要及目标 Skill 链接；未跟随这些链接 |
| 4 | `S/fixtures/anomaly.json` | `read` 全文；本轮冻结规范、请求、响应及证据边界 |
| 5 | `S/src/mcp_eval/*.py` | `grep`：`error_expected\|error_not_raised`（正则或）；5 处命中，位于 `judge.py` 与 `config.py` |
| 6 | `S/tests/cases/` | `glob`：`**/N02*.json`；仅返回 `l1/N02_param_out_of_range.json` |
| 7 | `S/src/mcp_eval/judge.py` | `read` 全文；核对错误断言、失败汇总和证据不完整分支 |
| 8 | `S/tests/cases/l1/N02_param_out_of_range.json` | `read` 全文；核对冻结用例 |
| 9 | `S/src/mcp_eval/records.py` | `read` 全文；核对离线记录字段与默认状态 |
| 10 | `S/src/mcp_eval/config.py` | `read` 全文；核对断言校验及导入依赖，没有调用其中其他场景配置 |
| 11 | `S/src/mcp_eval/__init__.py` | `read` 全文；核对导入入口 |
| 12 | 上述七个本组文件：README、夹具、N02 用例及四个 Python 模块 | 命令 C2 读取并计算前后哈希；其中四个 Python 模块被导入，实际模块路径保存在原始标准输出 |
| 13 | `G/outputs/n02-judge.stdout.json`、`G/outputs/n02-judge.stderr.txt` | `read` 全文；确认实际离线判定结果和空标准错误 |
| 14 | 上述七个本组文件与 C1/C2 输出、答案及本日志 | 命令 C3 复核输入哈希、交付文件存在性、原始输出内容及答案链接；未再次执行判定器 |
| 15 | `G/outputs/verification.stdout.json`、`G/outputs/verification.stderr.txt`、`G/outputs/answer.md`、`G/access-log.md` | `read` 回读终检结果与交付文档；本日志补记后再次回读 |

`grep` 的实际正则字符串为 `error_expected|error_not_raised`；没有在整个工作区开展搜索。未读取其他用例内容、录制文件、历史测试结果、评分标准或目标 Skill 引用文件。

## 4. 命令及原始输出

全部命令由助手执行于本机 Ubuntu Bash，`workdir=S`。以下是已执行记录，不是要求用户再执行的操作步骤。

### C1：确认输出父目录

```bash
ls -d -- . ../outputs
```

工具返回正常，原始标准输出为两行 `.` 与 `../outputs`，标准错误为空。随后用 `apply_patch` 按工具返回内容原样保存为：

- `outputs/01-directory.stdout.txt`
- `outputs/01-directory.stderr.txt`（空文件）

### C2：单情景离线核验

`-B` 禁止生成 Python 字节码缓存；`-I` 使用隔离模式。源码搜索路径由脚本显式设置为本组 `S/src`。只调用判定函数，没有调用设备执行器。标准输出/错误由 shell 直接重定向保存，未加工或截断。

```bash
"/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -B -I -c 'import hashlib, json, sys
from pathlib import Path
paths = ["README.md", "fixtures/anomaly.json", "tests/cases/l1/N02_param_out_of_range.json", "src/mcp_eval/__init__.py", "src/mcp_eval/judge.py", "src/mcp_eval/config.py", "src/mcp_eval/records.py"]
before = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
sys.path.insert(0, str(Path("src").resolve()))
from mcp_eval.judge import judge_record
from mcp_eval.records import EvalRecord
fixture = json.loads(Path("fixtures/anomaly.json").read_text(encoding="utf-8"))
case = fixture["case"]
assert fixture["source_type"] == "synthetic" and case["case_id"] == "N02"
assert case == json.loads(Path("tests/cases/l1/N02_param_out_of_range.json").read_text(encoding="utf-8"))
assert fixture["request"]["id"] == fixture["response"]["id"]
assert fixture["request"]["params"]["name"] == case["tool"]
assert fixture["request"]["params"]["arguments"] == case["arguments"]
assert case["arguments"]["temperature"] > fixture["allowed_temperature"][1]
record = EvalRecord(run_id="n02-fixture-analysis", case_id=case["case_id"], channel="replay", action=case["action"], service=case["service"], tool=case["tool"], arguments=case["arguments"], request_raw=fixture["request"], response_raw=fixture["response"], execution_status="completed", trace_complete=True, source_type=fixture["source_type"], provenance={"scope": "offline supplied fixture only; no observed device execution"})
judged = judge_record(case, record)
assert (judged.verdict, judged.verdict_reason) == ("fail", "预期错误未出现")
after = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
assert before == after
print(json.dumps({"analysis_type": "offline_fixture_judgement_only", "case_id": case["case_id"], "source_type": fixture["source_type"], "tool_version": fixture["tool_version"], "spec_version": fixture["spec_version"], "frozen_range": fixture["allowed_temperature"], "request": fixture["request"], "response": fixture["response"], "frozen_case_matches_local_case": True, "request_identity_checks": "passed", "verdict": judged.verdict, "verdict_reason": judged.verdict_reason, "independent_state_readback": fixture["independent_state_readback"], "recovery_method": fixture["recovery_method"], "device_execution": "not_performed", "model_api_execution": "not_performed", "offline_record_assumptions": {"execution_status": "completed", "trace_complete": True, "meaning": "complete supplied synthetic request/response for judge input, not a verified device trace"}, "input_sha256_before": before, "input_sha256_after": after, "read_inputs_unchanged": before == after, "loaded_product_modules": {name: getattr(module, "__file__", None) for name, module in sorted(sys.modules.items()) if name == "mcp_eval" or name.startswith("mcp_eval.")}}, ensure_ascii=False, indent=2))' > ../outputs/n02-judge.stdout.json 2> ../outputs/n02-judge.stderr.txt
```

结果：正常返回，所有内存检查通过；N02 判定为 `fail`，理由“预期错误未出现”。标准错误为空。哈希核对仅覆盖列出的七个已读文件，不声称已扫描整个交付包。合成记录中的完成/完整标志是离线输入假设，非设备执行事实。

### C3：交付文件与输入完整性终检

```bash
"/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/remediation-2026-10-16/.venv/bin/python" -B -I -c 'import hashlib, json, re
from pathlib import Path
result = json.loads(Path("../outputs/n02-judge.stdout.json").read_text(encoding="utf-8"))
current = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in result["input_sha256_before"]}
assert current == result["input_sha256_before"] == result["input_sha256_after"]
files = ["../outputs/answer.md", "../access-log.md", "../outputs/01-directory.stdout.txt", "../outputs/01-directory.stderr.txt", "../outputs/n02-judge.stdout.json", "../outputs/n02-judge.stderr.txt"]
assert all(Path(p).is_file() for p in files)
assert Path("../outputs/01-directory.stdout.txt").read_bytes() == b".\n../outputs\n"
assert Path("../outputs/01-directory.stderr.txt").read_bytes() == b""
assert Path("../outputs/n02-judge.stderr.txt").read_bytes() == b""
answer = Path("../outputs/answer.md")
links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", answer.read_text(encoding="utf-8"))
assert all((answer.parent / p).is_file() for p in links)
print(json.dumps({"status": "verified", "input_files_checked": len(current), "read_inputs_unchanged": True, "checked_deliverables": files, "answer_local_links_checked": len(links), "raw_stderr_files_empty": True, "directory_stdout_matches_tool_result": True, "answer_sha256": hashlib.sha256(answer.read_bytes()).hexdigest()}, ensure_ascii=False, indent=2))' > ../outputs/verification.stdout.json 2> ../outputs/verification.stderr.txt
```

结果：正常返回，`status="verified"`。七个已读输入/源码文件的哈希仍一致，六个既有交付文件均存在，答案中的三个本地链接有效，C1/C2 标准错误均为空，C1 标准输出与工具返回一致。

原始标准输出保存为 `outputs/verification.stdout.json`，原始标准错误保存为 `outputs/verification.stderr.txt`（空文件），均已回读。此后只补记本日志，没有修改答案或输入。该核验不代表真实设备验证或产品整改。

## 5. 写入与状态

已保存 `outputs/answer.md`、本日志、C1/C2/C3 的六份原始标准输出/标准错误文件。文档由 `apply_patch` 创建；C1 输出按工具返回原样落盘，C2/C3 输出由重定向产生。答案与日志均已回读，终检结果见上文。

任务用时和 Token 用量没有可靠统计，记为未知，不估算。未读取 `timing.json`，不借用其他运行的统计。
