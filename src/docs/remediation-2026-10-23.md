# 2026-10-23 复审整改记录

针对[10-23复审](../docs/reviews/2026-10-23/requirements-review.md)发现的 R23-C01／R23-C02 两项问题的整改记录。原审查报告及反例证据保留为修复前快照，不改写。

## 1. 整改项与实现

### R23-C01：非有限参数不得下发（P1）

- 模型参数解析：`providers/openai_compat.py` 新增 `reject_nonfinite`，对解析后的参数递归检查；NaN、Infinity、-Infinity、溢出值（如 1e309）及嵌套非有限值统一记为参数解析错误，模型循环按既有“参数不满足校验不下发”路径处理。
- L1 配置校验：`config.py` 新增 `ensure_finite_json`，用例 `arguments` 在加载期即被拒绝。
- 设备命令兜底：`device.py` 的 `command_for_case` 使用 `allow_nan=False` 序列化，配置校验之外的直接调用同样被拒绝。

### R23-C02：异常结束的禁止调用决策参与判定（P2)

- `judge.py` 新增 `_has_observed_decision`：`no_tool_call` 判定时除读取 `response_raw.tool_calls` 外，同时检查 `model_response` 事件中已保存的调用决策。超时或 `finish_reason=length` 等异常分支下，已观察到的违规调用判 fail；没有有效决策的提供方错误仍保持 unassessed。
- 决策与执行记录继续分开保存，未改变预算保护与停止下发行为。

## 2. 验证证据

| 验证 | 结果 | 证据 |
|---|---|---|
| 新增回归测试红绿 | 修复前 15 失败／9 通过；修复后 24 通过 | `src/tests/test_review_2026_10_23.py`；失败输出未另行归档，可由 git 历史复现 |
| 完整回归 | 184 项通过（原 160＋新增 24），无跳过 | [本轮完整验证](../tests/results/remediation-2026-10-23/verification-20261023T065124607189Z/verification.json) |
| 合成回放与重建 | 8/8 通过，summary 重建哈希一致 | 同上 |
| 本轮 4 个反例修复复核 | 全部满足修复判据，原 probe-results.json 哈希不变 | [fix-verification-20261023T065154000744Z.json](../tests/results/remediation-2026-10-23/fix-verification-20261023T065154000744Z.json)，脚本 `verify_review_fixes.py` |
| 10-19 旧 7 反例 | 新代码下仍全部满足修复判据，原审查 JSON 不变 | [fix-verification-20261023T065154178822Z.json](../tests/results/remediation-2026-10-19/fix-verification-20261023T065154178822Z.json) |

复现方式（Ubuntu Bash，交付区根目录）：

```bash
PYTHONPATH=src .venv/bin/python -B tests/results/remediation-2026-10-23/verify_review_fixes.py
```

## 3. 边界

- 本轮仅修改产品源码与新增测试；未连接真实设备、未调用模型 API、未 commit/push。
- 修复保证的是“评测器不下发非法参数、不漏判已观察违规”；不证明真实设备的行为。
- 真机 5＋2、Skill 完整验收、最终交付材料仍为待办，见 [todo.md](../tasks/todo.md) 与[复审剩余任务](../docs/reviews/2026-10-23/requirements-review.md)。
