# 常见报错与处理

| 报错/现象 | 含义 | 处理 |
|---|---|---|
| `环境变量 DEEPSEEK_API_KEY 未设置` | 密钥未 export | 在当前 shell `export DEEPSEEK_API_KEY=<key>` 后重试；不要写入文件 |
| `HTTP 400 ... function.name ... pattern` | 工具名含点号等 API 非法字符 | 已由 `ToolNameMapper` 处理；若仍出现，检查是否绕过了 ModelLoop 直接构造 tools |
| `HTTP 401` | 密钥无效或过期 | 确认 key 未轮换/未复制错；重新 export |
| `error_category=parse_failed` | 车机输出中未提取到 JSON-RPC | 基础设施问题，记录为 unassessed；上机时校准自带客户端输出格式后收紧解析 |
| `error_category=no_recording` | 回放找不到匹配录制 | 正常：表示该用例尚未在真机录制；补录或换 device 通道 |
| `error_category=adb_setup_failed` | adb 写配置失败 | 检查设备连接、root、workdir 可写 |
| L2 一直 `max_rounds` 停止 | 模型反复调用不给结论 | 检查工具结果是否回填成功；降低任务难度或调整 max_rounds 后再判 |
| 报告数字与 results.jsonl 不一致 | 报告过期 | 重新运行或调用 write_report 重建；报告必须可从结果文件重建 |

原则：凡是证据不足以得出"工具行为如何"结论的情况，一律标 unassessed 并记录原因，不用推测补齐。
