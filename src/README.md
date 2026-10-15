# MCP 工具评测

状态：需求已确认（2026-10-13 访谈确认，见 `../memory/DECISIONS.md` D013），进入实现阶段。被测对象为公司车载 `mcp_service`（8 个服务）；首版 L1 接口级必达、L2 模型级（DeepSeek＋Kimi）尽量做到；截止 2026-10-28；真机仅 1—2 次（下周一次）。尚无业务代码与评测结论。

## 课题概述

评测车载 MCP 工具是否好用：接口层验证工具枚举、调用、参数约束与错误行为；模型层验证模型选工具与填参能力。配置化支持多模型切换。预期交付 MCP 工具集、评测工具及评测报告，另含必交的评测流程 Skill。

## 方案阅读顺序

1. [需求分析与选题方案](./proposal.md)：公司要求、范围建议、验收和待确认事项。
2. [技术与评测设计](./docs/design.md)：架构、接入、数据、指标及 AI 交互。
3. [阶段计划](./tasks/plan.md)与[候选任务清单](./tasks/todo.md)：依赖、检查点及后续任务。
4. [用例设计](./tests/cases/README.md)：至少 5 正向＋2 负面控制的候选场景。

建议稿中的范围已按确认的意图收敛；IDE 直连车机的 L3 评测首版不做（自研传输非标准通道），详见 proposal.md §4.2。

## 目录结构

本目录为当前本地开发与交付区根目录，中间的项目名层级已被用户确认取消（历史名称见 `../memory/DECISIONS.md` 中 D004/D005）：

```text
src/                         # 本地开发与交付区
├── README.md
├── proposal.md
├── midterm.md
├── src/                     # 源代码、开发脚本，当前为空；完整路径为 src/src/
├── tests/
│   ├── cases/               # 用例设计草案；尚无可执行用例
│   └── results/             # 验证记录；尚无业务评测数据
├── docs/
│   ├── design.md            # 技术与评测设计建议稿
│   └── report.md            # 结题报告，待编写
├── tasks/
│   ├── plan.md              # 阶段计划建议稿
│   └── todo.md              # 候选任务与验收清单
├── skills/
│   └── README.md            # Skill 目录预留说明
└── skills-creator/
    └── fix-log.md           # 整改记录，尚未执行
```

工作区路径中，`src/src/` 是本目录下的源码目录，不是重复路径错误。该本地布局按用户要求确定；正式提交目录是否允许省略“姓名拼音－课题简称”这一层，仍以部门指定位置及演练要求为准。

空目录中的 `.gitkeep` 仅用于保留目录，不是源码、用例或测试结果。若需交付 Skill，按 [skills/README.md](./skills/README.md) 中的规范建立具体技能目录。

## 快速开始与使用说明

待确认技术栈、依赖和运行入口后补充。目前没有安装、运行或测试命令，不应将该骨架视为可执行工具。

## 验证与交付记录

- 本轮资料与文档核验：[planning-validation-2026-10-13.md](./tests/results/planning-validation-2026-10-13.md)；不属于业务评测结果。
- 中期记录：[midterm.md](./midterm.md)。
- 技术方案：[docs/design.md](./docs/design.md)。
- 结题报告：[docs/report.md](./docs/report.md)。
- Skills Creator 整改：[skills-creator/fix-log.md](./skills-creator/fix-log.md)。

## 工作区资料

本目录即工作区的 `src/` 目录，后续开发、测试及文档编写均以本目录或其子目录为工作目录。工作区任务资料见 [资料索引](../docs/README.md)，跨对话状态见 [CURRENT.md](../memory/CURRENT.md)。这些链接依赖当前工作区布局；正式打包前须补齐必要的独立使用说明与来源记录，并检查交付内容内链接。
