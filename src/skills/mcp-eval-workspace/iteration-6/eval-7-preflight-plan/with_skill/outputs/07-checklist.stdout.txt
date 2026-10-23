# 上机预检（设备契约待现场核实）

所有命令在开发机 Ubuntu Bash、交付区根目录执行；adb shell 内的命令才在车机运行。

1. 核对连接：`adb devices`，目标序列号必须为 `SYNTHETIC-SERIAL-NOT-A-DEVICE` 且状态为 device。
2. 只读查看二进制用法：`adb -s SYNTHETIC-SERIAL-NOT-A-DEVICE shell mcp_service`。该源码无参数打印用法并返回非零，需人工核对是否包含 --toolscall。
3. 只读记录本地基线：`git -C /data/AIOS_Ark_2026-dev/lagvm/LINUX/android/vendor/mcp rev-parse HEAD`。这不是设备二进制版本证明。
4. 完整工具目录必须来自可追溯的 JSON 导出。当前 --mcp all 会执行已有测试，不能用作只读发现。
5. 冻结已核对的工具名、参数、预期及恢复方法后，先运行单条调用，再扩大批次。
6. 配置预检：`PYTHONPATH=src python3 -m mcp_eval run configs/runs/l1_device.json --dry-run`。预检不连接车机。
7. 正式运行：`PYTHONPATH=src python3 -m mcp_eval run configs/runs/l1_device.json`。仅 --toolscall 已实现，其他动作保留 blocked。
8. L2 需完整 tools_file 和模型密钥；先验证模型配置，再使用 l2_device.json。
9. 每次运行返回独立输出目录，保存 manifest、results、artifacts 与报告；按确认的业务方法恢复原状态并记录。

root、重启与状态修改按设备实际需要执行，不在预检中自动触发。未验证的响应/发现接口应明确记录为阻塞。

