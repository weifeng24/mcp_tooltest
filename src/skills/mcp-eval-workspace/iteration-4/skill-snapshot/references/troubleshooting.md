# 故障处理与结论边界

| 情况 | 处理 |
|---|---|
| provider_error / HTTP 401 | 模型接入失败，不能满足“正确不调用”用例；核对同一终端的环境变量及提供方凭据状态，不在答复中显示密钥 |
| response_missing / response_ambiguous | 未取得唯一目标响应，保留全部 stdout/stderr；核对实际二进制日志，不取最后一个 JSON 猜测 |
| unsupported_action | 当前适配没有该动作；发现/资源操作不能改用 --mcp all 伪装完成 |
| no_recording | 没有相应请求的下一条录制，记录 blocked；不循环使用最后一次成功 |
| adb_timeout_remote_state_unknown | 本机停止等待不等于远端操作停止；先核对车况/进程状态，再按已确认恢复方法处理 |
| max_rounds / max_tool_calls | 已达到预算，不能判任务完成；分析逐轮证据，不能仅增大限额掩盖问题 |
| tools_file 不可读 | 需要完整工具 JSON；摘要日志不能还原 Schema；说明阻塞而不补造工具定义 |
| 报告需重建 | 使用批次 manifest 和 results 执行 rebuild；不采用最新配置覆盖历史口径 |

实际运行前先看 `--help`，流程细节参考交付根目录 README 与 docs/device-readiness.md。遇到未覆盖错误时保留原始证据及明确的未知项。
