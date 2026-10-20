# 10-19复审整改证据

本目录保存C01—C05的失败复现、修复后回归及离线验证。所有模拟数据均不代表真实设备或模型结果。原始审查证据保留在相邻`review-2026-10-19/`目录，不覆盖。

## 证据索引

- `judgement-red.xml`：18失败、8通过；`judgement-green.xml`：相关组合70通过。
- `checkpoints-red.xml`：7失败；`checkpoints-green.xml`：实现过程缩进错误导致收集失败，保留；修正后`checkpoints-green-2.xml`：50通过。
- `checkpoint-budget-red.xml`：3失败；`checkpoint-budget-green.xml`：26通过。
- `append-red.xml`：模拟结果追加中断时触发KeyboardInterrupt；`append-green.xml`：相关组合21通过。
- [最终完整验证](verification-20261019T102527934113Z/verification.json)：160通过、无跳过，CLI与8项合成回放通过、summary重建一致。
- [原7个反例修复验证](fix-verification-20261019T102528075419Z.json)：全部符合修复判据；原审查JSON哈希不变。脚本为`verify_review_fixes.py`。
- [10-20最终检查](final-check-20261020T094242361047Z.json)：当前产品源码与160项回归/7反例快照哈希一致；最小独立运行副本8/8、重建一致且不含memory；21份文档127处本地链接无断链，两个Skill复核页面均包含两组输出，`git diff --check`通过。副本复用现有解释器，不是正式打包或重新安装验证。

早期`verification-20261019T102334552868Z/`为159项通过；之后新增结果追加中断回归并修复，最终为160项。不同测试组不能相加充当独立业务用例数。

本轮未使用真实设备/模型、未安装依赖、未commit/push。完整过程及交付状态见[整改记录](../../../docs/remediation-2026-10-19.md)。
