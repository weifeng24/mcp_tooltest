# MCP 工具评测

状态：项目准备阶段。当前仅有交付目录骨架及需求信息摘录，尚无可运行程序、已执行测试或评测结论。

## 课题概述

评测 MCP 工具是否好用，支持灵活配置模型与 IDE／客户端。预期交付 MCP 工具集、评测工具及评测报告。

具体需求来源及待确认范围见 [proposal.md](./proposal.md)。

## 目录结构

本目录为当前本地开发与交付区根目录，中间的项目名层级已被用户确认取消（历史名称见 `../memory/DECISIONS.md` 中 D004/D005）：

```text
src/                         # 本地开发与交付区
├── README.md
├── proposal.md
├── midterm.md
├── src/                     # 源代码、开发脚本，当前为空；完整路径为 src/src/
├── tests/
│   ├── cases/               # 测试输入，当前为空
│   └── results/             # 测试结果及验证数据，当前为空
├── docs/
│   ├── design.md            # 技术方案，待编写
│   └── report.md            # 结题报告，待编写
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

- 中期记录：[midterm.md](./midterm.md)。
- 技术方案：[docs/design.md](./docs/design.md)。
- 结题报告：[docs/report.md](./docs/report.md)。
- Skills Creator 整改：[skills-creator/fix-log.md](./skills-creator/fix-log.md)。

## 工作区资料

本目录即工作区的 `src/` 目录，后续开发、测试及文档编写均以本目录或其子目录为工作目录。工作区任务资料见 [资料索引](../docs/README.md)，跨对话状态见 [CURRENT.md](../memory/CURRENT.md)。这些链接依赖当前工作区布局；正式打包前须补齐必要的独立使用说明与来源记录，并检查交付内容内链接。
