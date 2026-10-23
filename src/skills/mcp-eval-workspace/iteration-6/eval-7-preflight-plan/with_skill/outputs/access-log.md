# 访问与隔离记录

日期：2026-10-23。任务：iteration-6 / eval-7-preflight-plan / with_skill 离线演练。

## 路径与写入边界

- 项目根：`/home/tssh/文档/Works/mission/校招生ai演练任务`（下称 `ROOT`）。
- 本组根：`ROOT/src/skills/mcp-eval-workspace/iteration-6/eval-7-preflight-plan/with_skill`（下称 `GROUP`）。
- 执行目录：`GROUP/sandbox`；以下 shell 命令均显式以此为工作目录。
- 允许写入：本组 `sandbox/configs/servers/ark_mcp_service.json` 的 `device_serial` 及 `GROUP/outputs/`。
- Python 使用用户指定的 `ROOT/src/tests/results/remediation-2026-10-16/.venv/bin/python`；`PYTHONPATH=src`。设置 `PYTHONDONTWRITEBYTECODE=1`，防止导入在源码或解释器目录生成字节码。

## 显式读取顺序与用途

1. 首次读取 `GROUP/sandbox/skills/mcp-eval/SKILL.md` 全文，遵循用户要求的先读顺序。
2. 根据已注入的根 `AGENTS.md`，读取 `ROOT/docs/README.md`、`ROOT/memory/CURRENT.md` 全文，核对上层索引和交接约束。
3. 加载通用 Skill：`/home/tssh/.config/opencode/addyosmani-skills/skills/using-agent-skills/SKILL.md` 与 `/home/tssh/.config/opencode/anthropic-skills/skills/skill-creator/SKILL.md`；完成前另加载 `/home/tssh/.config/opencode/superpowers-skills/skills/verification-before-completion/SKILL.md`。仅使用执行当前单组任务所需的工作流；未打开其 grader/comparator/analyzer、schemas、评分文件或其他评测组。
4. 列举 `GROUP` 直属目录项，定位已有 `outputs/` 与 `sandbox/`。看到 `timing.json` 文件名，但未读取、修改或生成估算数据。
5. 读取 sandbox 内 `docs/device-readiness.md`、`docs/catalog-capture.md`、`README.md` 全文，核对离线预检及注册定义采集边界。
6. 在 `ROOT/memory/DECISIONS.md` 搜索 D013/D016 标题，读取第115—159行。包含 D013/D016，以及同一范围内 D014/D015 的历史摘要和 D017 标题。
7. 用限定 glob 检查从 `ROOT/src/AGENTS.md` 至本组父目录的各级 `AGENTS.md`，以及 `GROUP/**/AGENTS.md`；没有匹配。未遍历其他组。
8. 读取 `sandbox/configs/servers/ark_mcp_service.json`；文件元数据确认其为单链接普通文件。`baseline_tree` 和 `dump_dir` 仅为本地 JSON 字符串，未打开这些外部路径。
9. 列举本组 `outputs/`，读取本轮帮助、环境检查、清单、计划及验证输出；详细命令见 `commands.md`。
10. 读取本组 `input-hashes-before.json`，原本用于寻找输入完整性基线。内容为其他场景夹具的文件名和 SHA-256 摘要，未含本轮 server；未打开其所列文件。本轮改用独立 server/Skill 哈希记录。

## 上层信息与上下文污染

- **存在污染，不能声称完全盲评。** 必读 `docs/README.md` 和 `memory/CURRENT.md` 暴露了历史 Skill 对照结果、整改/回归摘要、验收缺口；索引还包含公司评分权重速查。它们是上层规则要求读取的摘要，并非本组实际运行证据。
- `memory/DECISIONS.md` 指定范围额外暴露 D014/D015 的历史整改及有限 Skill 验证摘要；sandbox README 同样包含历史验证摘要。
- 通用 Skill 工作流及本组 `input-hashes-before.json` 的无关夹具文件名/摘要也进入上下文。
- 未进一步访问历史评测目录、其他组、隐藏评测断言或评分标准文件；未跟随上层索引进入框架评分细则、答辩模板或历史结果。
- 本轮结论仅引用本组新生成的配置、checklist 与 dry-run 输出，历史通过数量不计入本轮结果。

## 交接写入安排

本轮唯一可写范围为本组 server 指定字段及 outputs。上层索引与记忆仅读取，不更新主项目 `memory/`；本轮状态、证据与后续待确认项保存在 `outputs/answer.md` 和本访问记录中。

## 当前修改

- 使用 `apply_patch` 将本组 server 的空 `device_serial` 改为 `SYNTHETIC-SERIAL-NOT-A-DEVICE`，其余字段保持原值。
- 在 outputs 保存修改前配置、实际命令 stdout/stderr 和报告。

## 执行访问与最终结果

- 环境脚本按帮助作为黑盒运行；Python 根据 `PYTHONPATH=src` 加载本组包，使用指定 venv 的解释器和依赖。没有因解释器位于历史 results 目录而打开该目录的评测记录，也没有安装依赖。
- 未直接读取环境脚本或产品源码实现；读取了其帮助与运行输出。没有运行设备/API 命令；checklist 中的 adb/git/正式批次内容，以及 dry-run JSON 中的远端读取 argv，均仅为生成的文本。
- 实际计划只包含 `MCPVehicleService` 的 tools/resources 两个文件；`executed=0`、`device_configured=true`、`runtime_tools_list_tested=false`。没有读取远端文件，没有生成真实 catalog 或评测批次。
- 修改前配置副本哈希与原配置一致；前后 diff 仅含 `device_serial`。目标 `SKILL.md` 前后哈希相同。修改操作仅作用于指定 server 字段及 outputs；产品源码、主项目、其他组与上层记忆未修改。
- 已生成 `answer.md`，列明全部未执行项和现场待确认条件。没有生成评分、基线比较、耗时/token 估计或提交记录。
