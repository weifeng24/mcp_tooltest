# 故障处理与结论边界

| 情况 | 处理 |
|---|---|
| provider_error / HTTP 401 | 模型接入失败，不能满足“正确不调用”用例；核对同一终端的环境变量及提供方凭据状态，不在答复中显示密钥 |
| response_missing / response_ambiguous | 未取得唯一目标响应，保留全部 stdout/stderr；核对实际二进制日志，不取最后一个 JSON 猜测 |
| unsupported_action | 当前适配没有该动作；发现/资源操作不能改用 --mcp all 伪装完成 |
| no_recording | 没有相应请求的下一条录制，记录 blocked；不循环使用最后一次成功 |
| adb_timeout_remote_state_unknown | 本机停止等待不等于远端操作停止；先核对车况/进程状态，再按已确认恢复方法处理 |
| 非法参数返回成功 | 冻结规范要求拒绝且请求关联完整时判fail；保留规范版本、请求响应及计划项，建议独立回读区分接受、截断或未生效，并按已确认方法恢复。不得倒改预期；未取得实际回读时不推断最终状态 |
| interrupted / execution_in_progress | 查看当前item的artifact检查点；executed是尝试项数，不能把部分执行当未执行。先核对远端状态再决定恢复或重试；未开始条目才not_run |
| max_rounds / max_tool_calls | 已达到预算，不能判任务完成；分析逐轮证据，不能仅增大限额掩盖问题 |
| tools_file 不可读 | 需要完整工具 JSON；摘要日志不能还原 Schema；说明阻塞而不补造工具定义 |
| 报告需重建 | 使用批次 manifest 和 results 执行 rebuild；不采用最新配置覆盖历史口径 |

实际运行前先看 `--help`，流程细节参考交付根目录 README 与 docs/device-readiness.md。遇到未覆盖错误时保留原始证据及明确的未知项。
