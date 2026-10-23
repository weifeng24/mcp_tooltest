# 答辩讲解与演示准备稿

状态：2026-10-19。按框架15分钟汇报设计，部门实际时长待确认。本稿为内容与演示脚本，不是已完成PPT或录屏。真实效果数据补齐后方可形成最终答辩版本。

2026-10-23补充：用户确认新HTML为公司答辩模板，明确15分钟汇报＋10分钟问答及Skill至少5正向＋2负面行为用例。正式展示须覆盖其01—06部分，个人介绍纳入开场、Skill展示嵌入方案或演示；当前缺口及成品目录见[模板分析](defense-template-analysis.md)。下文保留原准备稿，尚未制作最终展示文件。

同日本地执行后已有[六部分阶段HTML](defense/index.html)、[合成执行记录回看](defense/offline-demo.html)、[录屏](defense/offline-demo.webm)及[新版讲解提纲](defense/speaker-notes.md)。它们可用于当前本地演练，尚待真实业务素材、培训原文和个人实例形成正式答辩版本。

## 1. 汇报结构

| 页面 | 时间 | 内容 | 证据/素材 |
|---|---|---|---|
| 1 课题与目标 | 1分钟 | 真实车载工具评测；工具、模型、客户端三个层次 | proposal、原申报摘录 |
| 2 约束与范围 | 1分钟 | 设备稀缺、截止日、L1必达与L2扩展、IDE范围差异 | 已确认需求及实际设备记录 |
| 3 技术流程 | 2分钟 | 配置→冻结计划→执行→判定→报告；device/replay | design流程图及运行产物 |
| 4 AI和Skill设计 | 3分钟 | Tool Wrapper、渐进加载、自由度、反例驱动整改 | Skill正文、Creator记录、失败/通过测试 |
| 5 演示 | 5分钟 | 实际批次回放、逐项证据、错误与无法判断、报告重建 | 最终真实录制及报告；录屏保底 |
| 6 数据与总结 | 3分钟 | 可控对比、样本数、失败分析、局限与后续 | 正式结题数据；当前尚未取得 |

## 2. 当前可练习的离线演示

位置：开发机Ubuntu Bash，交付根目录。前置条件：按README配置Python依赖。当前样本是synthetic，演示时必须明确其开发验证用途。

先查看帮助，确认运行入口和选项：

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval --help
```

本机若使用已建立的验证venv，将`.venv/bin/python`替换为`tests/results/remediation-2026-10-16/.venv/bin/python`。解释器不存在时先按README准备，不继续执行。

查看冻结前的运行计划：

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval run configs/runs/replay_smoke.json --dry-run
```

预期显示8个计划项、executed=0，不连接设备/API。引用缺失时先修正配置，不能跳过未执行项。

执行一次独立回放：

```bash
PYTHONPATH=src .venv/bin/python -m mcp_eval run configs/runs/replay_smoke.json
```

预期8项pass及实际新批次路径。在编辑器打开输出中的report、manifest和一个artifact，说明计划分母、来源synthetic、请求/响应与后置证据。若结果不符，保留新批次并按实际结果说明，不切换旧成功报告冒充本次输出。

重建报告使用README中的`rebuild`步骤，实际批次路径从本次输出复制。正式答辩时应优先使用真实采集数据，并同时展示原始真机证据；当前离线演示不能替代真实5＋2验收。

## 3. 必须能够解释的问题

1. 为什么123项测试通过仍能发现缺陷？新增测试覆盖了哪些遗漏？
2. `execution_status`与`verdict`分别表示什么？为什么未知不能按失败或通过填数？
3. 为什么工具返回错误但某个字段符合期望仍不能判成功？
4. 中断发生时如何保留已有调用？为什么不能直接重试状态修改？
5. 注册定义dump与实时工具发现有何不同？
6. 为什么模型切换不能证明IDE适配？
7. Skill用了哪些约束和自由度，Creator实际验证了哪些内容？
8. 对比实验控制了什么变量，哪些结论当前没有数据支持？

## 4. 最终材料检查

真实批次、对比数据和Skill反馈齐全后，将以上内容制作为PPT，录制包含实际命令、批次路径与结果来源的演示视频，并按部门时长演练问答。当前未生成最终PPT/录屏，不能标作T11完成。
