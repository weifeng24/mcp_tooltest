# 上下文与访问边界

## 实际环境限制

本会话工具列表没有Task、agent或其他创建隔离模型上下文的接口。`multi_tool_use.parallel`只能并行调用现有工具，不能创建独立模型上下文。实际启动独立上下文数为0；没有启动8次并行或串行子代理。

按skill-creator的无子代理降级说明，仅执行4个主上下文with_skill检查，without_skill全部not_run。这里的without_skill指无Skill基线，不是旧Skill版本。不能将同一上下文切换标签、外部CLI调用或脚本生成答案冒充隔离代理。本轮没有调用任何外部模型API。

## 请求的隔离规则与实际状态

- 预期with_skill：读取当前 `skills/mcp-eval/SKILL.md` 及必要参考、公共资料。
- 预期without_skill：仅场景prompt及必要公共README/配置，禁止读取整个 `skills/`、`skills-creator/`、本轮工作区、历史对照和相邻代理产物；仅允许写入自己的答案/访问日志。
- 实际without_skill：没有运行、没有读取、没有生成answer或grading；各目录仅由管理侧写入阻塞状态与null timing。因此**未建立可用于比较的基线隔离**。
- 实际with_skill：同一主会话读过所有prompt、expected_output、expectations、根规则、旧memory及当前Skill。4份答案为主上下文检查产物，不能推断Skill增量、稳定性或速度。

## 主会话共享读取

1. 根 `AGENTS.md`、`docs/README.md`、`memory/CURRENT.md`；`memory/DECISIONS.md`末段；框架Skill/交付相关检索。管理脚本另外保留这些文件的完整文本快照和哈希。
2. 原申报表“维度说明”第2行，通过标准库zip/XML解析，结果在 `topic-row.json`。没有修改表格。
3. skill-creator正文、grader、analyzer、schemas、聚合器、生成器与viewer模板（为检查null数据兼容性）。全局目录只读，Python运行禁用字节码写入。
4. 项目Skill正文、两个references、4个既有eval；交付README、回放配置、server配置、L2配置、device-readiness、N02模板。所读内容保存在 `input-snapshots.json`。
5. 本轮唯一CLI回放的原始产物。未读取iteration-2的历史答案或评分。git状态和写边界哈希清单可能包含历史路径，但未作为答题内容使用。

`glob **/AGENTS.md`未发现交付区额外规则。父目录检查使用ls；git status/rev-parse保留工作树已有用户修改。首次 `command -v claude` 无输出，脚本复核记录了退出码1。

## 命令与原始返回

所有运行cwd显式为交付根目录。外层调用为指定venv解释器运行本轮 `scripts/collect_evidence.py` 的prepare/preflight/replay；最终还执行integrity和本轮评分/展示脚本。每个实际子命令的argv、环境覆盖、stdout、stderr、退出码由脚本即时保存于 `logs/*.json`，没有重写为预期输出。

Read/Glob/Grep/apply_patch的原始工具返回保留在会话中，本环境没有完整原始会话导出接口。磁盘上的快照、访问日志不能冒充原始工具转录；这是本次证据保全的限制。没有子代理通知，token/耗时均为null，不估算。

最终校验阶段还加载了verification-before-completion流程，并读取本轮grading、产物检查和分析文件。发生在答案写入之后，没有用于生成独立代理答案。官方生成器先生成审阅页，grading字段规范化后以review-final再次生成；两次命令返回分别保留，答案和分数没有变化。

## 写边界

所有新增内容位于本iteration-3目录。答案和手写脚本/文档通过apply_patch编辑；JSON结果、CLI原始产物和官方review.html由这些脚本生成。场景输出目录只含answer.md与access-log.md；本地回放产物与管理日志独立保存在本轮evidence/logs。

写边界核对覆盖Git已跟踪和未忽略的未跟踪文件，排除iteration-3；不声称对忽略的venv、系统缓存和并发进程实施了操作系统级沙箱监控。运行统一禁用Python字节码写入，不安装依赖、不启动服务、不执行pytest、commit或push。

## 新旧事实

用户最新说明为C01—C05已修复、完整回归160passed、8合成回放与7原反例修复验证通过；旧README/memory尚未同步。本轮只重新验证自己的合成回放，未将用户提供的完整回归记录冒充本轮执行，未改主文档或memory。
