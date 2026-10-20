# 场景 1：离线回放实际结果

## 结论

已执行一次 `replay_smoke`，生成唯一新批次 `replay-smoke-20261020T082452120070Z-235a47c8`。本次计划 8 项、尝试执行 8 项、保存结果 8 项；通过 8 项、失败 0 项、无法判断 0 项。数据来源全部为 `synthetic`，结论仅适用于本次合成输入下的离线回放及判定流程。

## 实际执行

- 终端：本机 Ubuntu Bash。
- 工作目录：`/home/tssh/文档/Works/mission/校招生ai演练任务/src`。
- 解释器：`tests/results/remediation-2026-10-16/.venv/bin/python`；本批次 manifest 记录 Python `3.10.12`。
- 记录时间：`2026-10-20T16:24:52+08:00`，来自本次结果时间戳。
- 执行次数：1 次正式回放；未执行额外 dry-run 或 rebuild。

已执行命令：

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 tests/results/remediation-2026-10-16/.venv/bin/python -m mcp_eval run configs/runs/replay_smoke.json
```

`PYTHONPATH=src` 指向交付区内源码目录；`PYTHONDONTWRITEBYTECODE=1` 禁止本次解释器写入 Python 字节码缓存。批次由程序按时间戳及随机后缀新建，公共代码使用 `exist_ok=False`，不存在覆盖同名旧批次的运行路径。

## 结果核对

依据本次命令输出及新批次的 `manifest.json`、`results.jsonl`、`summary.json`、`report.md`：

| 分组 | 计划 | 通过 | 失败 | 无法判断 | 计划内通过率 | 判定覆盖率 |
|---|---:|---:|---:|---:|---:|---:|
| L1 正向 | 6 | 6 | 0 | 0 | 100% | 100% |
| L1 负面控制 | 2 | 2 | 0 | 0 | 100% | 100% |
| 合计 | 8 | 8 | 0 | 0 | 100% | 100% |

- manifest：`state=finished`、`attempted_items=8`、`recorded_items=8`。
- 命令输出：`executed=8`、`interrupted=false`、`warnings=[]`。
- summary：`total=8`、`observed=8`、`failure_categories={}`。
- 范围：`channel=replay`；8 项均为 L1（工具接口级），L2（模型调用级）为 0，模型数量为 0，重复次数为 1。
- N01、N02、P01、P02、P03、P04、P05、P06 均为 `completed/pass`。
- N01 的合成响应为未知工具错误，N02 为温度 40 越界错误，两者均返回错误码 `-32602`。负面用例通过表示匹配了预期错误条件。
- P02、P03、P06 的完整 artifact 已读取：主调用成功，独立后置回读分别返回温度 22、16、30，均为合成回放事件。
- 两组时延统计均为 `samples=0`，中位数、最小值及最大值均为 `null`；不据此报告设备性能。

## 数据来源与可追溯性

1. 执行配置：`configs/runs/replay_smoke.json`。
2. 原始输入：`recordings/DEV_SYNTHETIC_V2_NOT_REAL.jsonl`。
3. 本次输入副本：`tests/results/replay-smoke-20261020T082452120070Z-235a47c8/recording-input.jsonl`。
4. 副本共 11 条合成事件，对应 8 项主调用和 3 次温度回读；原始 `run_id=synthetic-v2`。新结果的 `provenance.source_run_id` 保留该来源，`source_type=synthetic`。
5. 使用 `sha256sum` 核对原始输入与新批次副本，两者均与 manifest 的 `recording_sha256` 一致：

```text
0a18cffdb92afe1d683d88177f3821f27240bbcac5506d57457ce588e8bcc848
```

6. manifest 保存本次计划、运行/服务/用例配置及 14 个公共源码文件的 SHA-256（文件内容摘要）。输入副本原文没有时间戳；结果中的 `source_timestamp` 由加载记录时的默认逻辑补入，不能作为真实采集时间。

本次结果不证明真实车机接口、真实模型调用或 IDE／客户端评测通过；未连接设备或外部模型。

## 实际新批次与文件

批次绝对路径：

```text
/home/tssh/文档/Works/mission/校招生ai演练任务/src/tests/results/replay-smoke-20261020T082452120070Z-235a47c8/
```

批次产物：

- `manifest.json`：计划、输入快照、源码哈希、完成状态。
- `results.jsonl`：8 项执行结果。
- `summary.json`：分组统计。
- `report.md`：本批次评测报告。
- `recording-input.jsonl`：合成输入副本。
- `artifacts/item-00001.json` 至 `artifacts/item-00008.json`：逐项证据。

访问与写入明细见同目录 `access-log.md`。本次未运行 pytest、未修改源码/配置/项目文档、未 commit、未调用 Skill 或委派、未生成 grading。

## 独立性边界披露

启动时按会话中已加载的项目规则读取了根目录 `docs/README.md`、`memory/CURRENT.md`，其中包含历史审查及历史 Skill 行为结果摘要。因此不能声称本轮完全没有接触历史结果信息。没有打开这些摘要链接的审查报告、其他组输出或评分期望文件；本报告的执行结果与来源结论均以本次新批次为依据。`skills/`、`skills-creator/` 下未进行读取，指定输出仅通过 `apply_patch` 写入，未回读。
