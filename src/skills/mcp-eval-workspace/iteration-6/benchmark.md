# iteration-6行为评测汇总

5正向＋2负面；同一Skill版本，每场景各配置选取一个明确引用的回答/批次评分，额外产物见限制。

| 场景 | 分类 | 有Skill | 无目标Skill |
|---|---|---:|---:|
| 1 offline-replay | positive | 5/5 | 4/5 |
| 2 missing-evidence | negative | 5/5 | 5/5 |
| 3 device-not-ready | negative | 5/5 | 5/5 |
| 4 unexpected-success | positive | 5/5 | 5/5 |
| 5 report-interpretation | positive | 5/5 | 5/5 |
| 6 frozen-report-rebuild | positive | 5/5 | 4/5 |
| 7 preflight-plan | positive | 5/5 | 4/5 |

- 有Skill35/35，无目标Skill32/35；7个任务各5条评分，不是35个独立用例。
- 基线两项未执行帮助，另有场景7序列号修改过程证据不足；该项不能解释为Skill的能力增益。
- 两组均读到根索引/记忆摘要及通用Skill，非盲评；标准差跨场景，不代表重复运行稳定性。
- 场景1两组各存在一个回答未引用的较早批次；评分只针对所引批次，额外执行来源尚未核实，不能声称每组仅执行一次。
- 未知token/耗时为null，未验证真实自动触发、业务效果或导师验收。

详细评分与证据：[grading-notes.md](grading-notes.md)。
