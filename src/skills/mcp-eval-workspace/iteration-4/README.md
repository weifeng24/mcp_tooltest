# iteration-4：独立上下文行为复测

执行日期：2026-10-20。由主会话分别启动4场景×有/无Skill共8个独立代理，均完成。每个代理单独写本组outputs，两个回放执行使用独立批次；未运行pytest或真实设备/API。

结果：[benchmark.md](benchmark.md)、[benchmark.json](benchmark.json)、[官方复核页面](review.html)。有Skill19/20，无Skill17/20。双方场景4均漏掉独立回读及恢复建议；无Skill场景1未看帮助、场景2未明确计划分母。核心判定多数相同，不能声称稳定增益或速度优势。

基线没有读取目标Skill或其他组答案；但场景1—3的无Skill代理按项目规则读取了包含历史摘要的索引/记忆，不能称为完全盲评。访问记录来自各组access-log和Task返回，不是操作系统强隔离证明。Task未提供耗时/token，全部保留null；不同任务间标准差不代表重复运行稳定性。

本轮被测Skill未在执行中修改，旧版快照与哈希保存在`skill-snapshot/`、`skill-hashes.json`。评分后针对双方遗漏补充通用状态核对规则；局部新旧版本复测另存iteration-5，不改本轮原回答和得分。自动触发、用户反馈和导师验收仍待完成。
