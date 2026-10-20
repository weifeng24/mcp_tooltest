# 整改验证摘要

日期：2026-10-16。最终验证与持久记录保存在交付区；pytest现已统一使用区内临时目录。本轮未调用真实车机或收费模型。

- 标准 `python3 -m venv` 因缺少ensurepip失败；未执行系统安装命令。
- 使用`venv --without-pip`与宿主pip的`--target`在项目内创建独立环境，依赖从PyPI安装。依赖清单及Python前缀见末次verification.json。
- 末次验证：[verification-20261016T104008355598Z](verification-20261016T104008355598Z/verification.json)。**114项测试通过，退出码0；合成回放8/8通过，rebuild前后summary一致**。
- CLI help/dry-run/show-call/checklist/run/rebuild日志均在该目录。每次实际运行产物为独立目录，旧的固定replay-smoke未被覆盖。
- Skill结构校验与帮助/环境脚本检查通过；两组有限语义测试各6/6，真实自动触发未测试，数据未提供的时长/token以null保留。
- 新增回归测试均围绕实际审查缺陷；历史失败记录与审查报告保留，未通过跳过测试来达成全绿。
- 最后文档/数据核对：41份Markdown、106处本地链接无断链；84份JSON可解析；`git diff --check`通过。对纳入检查的文本未检出sk型凭据模式，未打印任何凭据内容。

结论边界：设备发现/资源动作、设备二进制、真实工具绑定、Kimi接入、IDE范围和完整Skill验收仍未闭环。当前数据只能证明离线软件行为，不是最终业务评测数据。

## 2026-10-19 增补验证

新增注册目录只读快照采集后，使用同一独立环境执行`scripts/verify_offline.py`：123项通过、合成回放8/8、重建一致。新增catalog-plan日志明确列出cat文件读取计划，未运行adb。证据位于[verification-20261019T080940766650Z](verification-20261019T080940766650Z/verification.json)。

采集器不重编译或替换车端组件，也不启用dump；现场文件和权限仍须核对。资源定义快照不等于资源值读取，实时ToolsList/ResourcesRead仍待适配。
