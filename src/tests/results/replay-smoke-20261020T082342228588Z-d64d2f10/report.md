# 评测报告（run: replay-smoke-20261020T082342228588Z-d64d2f10）

- 计划总数：8
- 回放数据仅供开发自测；device 标签也须结合 source_type、原始证据和版本快照解释。
- 合成数据不能支撑真机结论；时延按判定分组，未知值不填零。

## 指标汇总

| 分组 | 计划 | 通过 | 失败 | 无法判断 | 计划内通过率 | 判定覆盖率 |
|---|---|---|---|---|---|---|
| replay\|L1\|negative\|- | 2 | 2 | 0 | 0 | 100.0% | 100.0% |
| replay\|L1\|positive\|- | 6 | 6 | 0 | 0 | 100.0% | 100.0% |

来源 `replay\|L1\|negative\|-`：synthetic。
来源 `replay\|L1\|positive\|-`：synthetic。

## 逐项判定与证据

| item | case | 模型 | 重复序号 | 状态 | 判定 | 原因 | 证据 |
|---|---|---|---|---|---|---|---|
| item-00001 | N01 | - | 0 | completed | pass | 全部断言及后置条件通过 | artifacts/item-00001.json |
| item-00002 | N02 | - | 0 | completed | pass | 全部断言及后置条件通过 | artifacts/item-00002.json |
| item-00003 | P01 | - | 0 | completed | pass | 全部断言及后置条件通过 | artifacts/item-00003.json |
| item-00004 | P02 | - | 0 | completed | pass | 全部断言及后置条件通过 | artifacts/item-00004.json |
| item-00005 | P03 | - | 0 | completed | pass | 全部断言及后置条件通过 | artifacts/item-00005.json |
| item-00006 | P04 | - | 0 | completed | pass | 全部断言及后置条件通过 | artifacts/item-00006.json |
| item-00007 | P05 | - | 0 | completed | pass | 全部断言及后置条件通过 | artifacts/item-00007.json |
| item-00008 | P06 | - | 0 | completed | pass | 全部断言及后置条件通过 | artifacts/item-00008.json |

## 失败类别

- 无已判定失败
