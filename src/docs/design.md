# MCP 工具评测：技术与评测设计

状态：已按 2026-10-13 确认的意图（D013）收敛。需求与范围见 [proposal.md](../proposal.md)。本文件路径均相对于交付区 `src/`。

## 1. 设计约束

| 约束 | 影响 |
|---|---|
| 截止 2026-10-28（约 2 周） | 不做网页界面、数据库等外围；命令行＋文件化产物 |
| 真机仅 1—2 次、下周一次（adb 全权限） | 离线为主；录制回放驱动开发；上机窗口只做采集与正式批次 |
| 被测服务仅车端运行，传输为自研 binder/dds | 评测编排不直连服务；经 adb 在车上执行，开发机做编排/判定/报告 |
| 人工约 14 小时/周 | 范围聚焦 8 服务中的代表性子集，优先确定性强的工具 |
| 数据层为标准 MCP 语义（已核实） | 用例、判定、报告按标准 tools/list、tools/call 语义设计 |

## 2. 被测对象与协议事实（2026-10-13 只读核实）

- 源码：`/data/AIOS_Ark_2026-dev/AIRuntime/MCPServices/Linux`（同仓库多车型树重复检出，正式评测选定一棵基线树，候选 Ark 树）。
- Server：`mcp_service`（C++），8 个服务：MCPVehicleService、MCPVoiceService、MCPMapService、MCPVGuiService、MCPKanziService、MCPGuideService、AndroidCameraProxy、NVCameraProxy。
- 数据层：JSON-RPC 2.0 MCP 语义；tools/list 返回含 inputSchema/outputSchema 的工具定义；Client 端工具名带 `serviceId.` 前缀，RouteManager 路由时去除前缀。
- 传输层：自研 binder/dds（非标准 stdio/HTTP）。因此 IDE 无法直接挂载车端服务，L3 移出首版。
- 既有测试设施：`mcp_service -c -t` 客户端测试模式，由 `test_config_*.json` 配置驱动，支持 `--list/--all/--mcp/--service/--svcmap` 等；配置含 tools/call 用例与 resources 订阅项（`app/test/TEST_GUIDE.md`、`app/test/config/`）。

## 3. 总体架构

```text
开发机（Ubuntu）
└── mcp-eval（Python，src/src/mcp_eval/）
    ├── 配置加载：servers / models / cases / runs（JSON）
    ├── 执行层
    │   ├── device 通道：adb shell 驱动车机执行，抓取 stdout/logcat
    │   └── replay 通道：读取录制流量，离线回放同一批用例
    ├── L1 执行器：确定参数的 tools/list、tools/call、resources 断言
    ├── L2 执行器：模型决策循环（DeepSeek/Kimi API）→ 调用经 adb 下发 → 结果回填
    ├── 判定器：断言执行、错误分类、证据归档
    └── 报告器：summary.json + report.md（可离线重建）

车机（adb 连接，上机窗口）
└── mcp_service -s（被测 Server）
    └── 执行方式：复用自带 -c -t 客户端（配置由本工具生成并 push），
        或经 McpClientProxy 的等效调用；输出与日志回采
```

设计要点：

1. **双通道同一判定**：device 与 replay 两条执行路径产出同一格式的标准记录，判定器不感知来源；回放结果仅用于开发自测，报告结论只引用真机数据。
2. **复用而非重造**：L1 真机执行优先复用自带测试客户端（本工具负责生成配置、下发、采集、独立断言），避免在自研传输上重写客户端。
3. **L2 决策与执行分离**：模型在开发机决策，执行经 adb 下发；模型只见到 tools/list 与任务，不接触预期答案。

## 4. 技术选型

- 语言：Python 3（开发机侧全部组件）；依赖：`mcp` SDK（可选，用于协议结构校验）、`jsonschema`、`pytest`；模型 API 用各提供方官方接口或 OpenAI 兼容端点。
- adb 交互：`subprocess` 调用本机 adb，命令与输出全量留痕。
- 数据：配置与用例 JSON；事件流 JSONL；摘要 JSON＋Markdown 报告。
- 锁定依赖版本；`README.md` 提供完整安装与运行命令（实现后补）。

## 5. 配置与记录契约

### 5.1 配置对象

| 配置 | 关键字段 | 说明 |
|---|---|---|
| server | 基线树、设备序列号、服务清单、test_config 模板 | 对应一棵源码树＋一台设备 |
| model | provider、model、base_url、api_key 环境变量名、生成参数 | DeepSeek/Kimi/OpenRouter 各一条；密钥只引用环境变量 |
| case | case_id、层次、类别（正向/负面/边界）、服务、工具、参数、断言、预期来源 | 见 [用例设计](../tests/cases/README.md) |
| run | 执行通道（device/replay）、模型引用、重复次数、超时、输出目录 | 每次运行固化快照 |

### 5.2 记录与判定

- 每条结果：`run_id`、`case_id`、`channel`、请求/响应原文、耗时、错误类别、`execution_status`（completed/timeout/error/blocked/not_run）、`verdict`（pass/fail/unassessed）、证据路径。
- 判定优先级：已证实的违规（如禁止调用发生）→ fail；时限内未满足要求且证据完整 → fail；必要条件与证据齐全 → pass；证据缺失/冲突 → unassessed。
- 指标按层次×模型×类别分组：通过率、判定覆盖率、错误分类分布、耗时；分母固定为运行计划条目数，未执行计 unassessed；回放数据单独标记，不与真机混算。

## 6. 用例与指标设计

详见 [tests/cases/README.md](../tests/cases/README.md)。核心指标：

- L1：工具枚举完整性（tools/list 与预期服务/工具集一致）、调用成功率、参数校验正确性（边界/越界行为符合预期）、错误可诊断性（错误类别明确且含可操作信息）。
- L2：选工具准确率、参数正确率、任务完成率、平均调用轮数与耗时；双模型对比表。
- 负面控制：无需工具任务不调用（L2）；未知工具/越界参数被正确拒绝（L1）。

## 7. AI 交互与培训衔接

- **L2 循环**：任务（自然语言）→ tools/list → 模型输出调用决策 → 参数校验 → adb 执行 → 结果回填 → 终止判定（完成/超轮/超时）。最大轮数与单次超时强约束。
- **Vibe Coding**：开发过程保留需求→实现→验证的迭代记录（用户已确认允许）。
- **Skill（必交）**：`mcp-eval` 流程 Skill——封装 adb 环境检查、配置选择、评测执行、报告解读；初版在核心工具可用后编写，经 Skills Creator 整改并留痕（`skills-creator/fix-log.md`）。
- **Bad Case→Good Case**：评测报告的失败分类直接驱动工具描述/参数的改进建议；若时间允许做一次小范围前后对比。

## 8. 验证设计

- 评测器自测（离线）：录制回放驱动；已知正确/错误/缺失证据输入，验证判定与指标计算；报告可重建。
- 真机验证（上机窗口）：L1 全量批次＋L2 双模型批次；抓 logcat 与服务日志交叉核对。
- 交付验证：第三方按 README 回放模式复现报告。

## 9. 风险与对策

| 风险 | 对策 |
|---|---|
| 上机时间晚于中期检查 | 中期用回放模式演示并如实标注；真机数据随后补齐 |
| 自带测试客户端输出不稳定 | 上机先用最小命令验证输出格式；准备 logcat 交叉通道 |
| Kimi API 工具调用能力受限 | 先用 DeepSeek 打通 L2；Kimi 作为第二模型，失败则报告降级说明 |
| 车机状态依赖（如空调实际状态） | 用例优先选幂等读取与可恢复设置；执行前后记录状态 |

## 10. 技术参考

- MCP 官方架构与 Tools 规范（2026-07-28 与 2025-11-25 两版，2026-10-13 查阅）。
- 仓库文档：`MCP_Agent.md`（协议数据格式 §9）、`app/test/TEST_GUIDE.md`、`app/test/config/test_config_ark.json`。
