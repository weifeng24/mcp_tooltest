# MCP 工具评测

面向公司车载 `mcp_service`（8 个服务）的可用性评测与回归验证工具：接口层（L1）验证工具枚举、调用、参数约束与错误行为；模型层（L2）验证大模型选工具与填参能力。配置化支持多模型切换（DeepSeek / Kimi / OpenRouter）。

交付物：MCP 工具集（被测工具清单与用例）、评测工具（`src/mcp_eval/`）、评测报告（`docs/report.md`，待真机数据），另含评测流程 Skill（`skills/`）。

## 快速开始

### 环境要求

- Python ≥ 3.10（开发机实测 3.10.12）
- adb ≥ 1.0.41（仅真机模式需要）
- 依赖安装：`pip install -r requirements.txt`（jsonschema、pytest）

### 五分钟验证（离线回放模式，无需车机）

在交付区根目录（`src/`）执行：

```bash
# 1. 单元测试（75 项）
python3 -m pytest -q

# 2. 回放冒烟：7 条 L1 用例全链路（配置→执行→判定→报告）
PYTHONPATH=src python3 -m mcp_eval run configs/runs/replay_smoke.json

# 3. 查看生成的报告
cat tests/results/replay-smoke/report.md
```

回放使用 `recordings/DEV_SYNTHETIC_NOT_REAL.jsonl`（手工构造的开发样本，**非真机数据**）。回放数据仅证明工具链路可用，报告中 `replay` 通道与 `device` 通道分组统计，结论只引用 device 数据。

## 命令一览

| 命令 | 说明 |
|---|---|
| `python3 -m pytest -q` | 运行单元测试 |
| `PYTHONPATH=src python3 -m mcp_eval run <run配置> [--dry-run]` | 执行评测；`--dry-run` 只校验与展示计划 |
| `PYTHONPATH=src python3 -m mcp_eval gen-config <用例JSON>` | 由单条用例生成车机 test_config |
| `PYTHONPATH=src python3 -m mcp_eval checklist` | 输出上机日检查清单（按 server 配置填充命令） |
| `PYTHONPATH=src python3 scripts/api_smoke.py <model配置>` | 模型 API 冒烟（需先 export 对应密钥环境变量） |

## 真机模式（上机日）

1. 在 `configs/servers/ark_mcp_service.json` 填写 `device_serial`。
2. 按 `PYTHONPATH=src python3 -m mcp_eval checklist` 逐步执行：环境确认 → 协议采集 → L1 批次 → L2 批次 → 状态恢复 → 证据回采。
3. L2 批次前设置密钥环境变量（`DEEPSEEK_API_KEY`、`KIMI_API_KEY`），密钥不写入任何配置或代码。
4. 结果与报告输出到 `tests/results/<run-id>/`。

## 架构

```text
mcp_eval/
├── config.py        # 四类 JSON 配置的加载与校验
├── records.py       # 标准记录（device/replay 同一格式）
├── device.py        # adb 通道：车机执行、输出采集、超时映射
├── replay.py        # 回放通道：录制 JSONL 离线复现
├── judge.py         # 判定：10 种断言 + 判定优先级
├── report.py        # 分层指标与 Markdown 报告（可重建）
├── model_loop.py    # L2 模型决策循环（轮数/超时强约束、错误回填）
├── providers/       # DeepSeek/Kimi/OpenRouter（OpenAI 兼容接口）
└── runner.py        # 运行编排；__main__.py 为 CLI 入口
```

设计细节见 [docs/design.md](docs/design.md)。

## 目录结构

```text
src/                         # 本地开发与交付区根目录
├── README.md  proposal.md  midterm.md
├── pytest.ini  requirements.txt
├── src/
│   ├── mcp_eval/            # 评测工具源码
│   └── tests/               # 单元测试（75 项）
├── configs/                 # server/model/run 配置（密钥只引用环境变量名）
├── scripts/api_smoke.py     # 模型 API 冒烟
├── recordings/              # 录制样本（DEV_SYNTHETIC_NOT_REAL 为开发合成数据）
├── tests/
│   ├── cases/               # 评测用例（l1/ 7 条、l2/ 4 条）+ 设计说明
│   └── results/             # 运行结果、报告与验证记录
├── docs/                    # design.md（技术设计）、report.md（结题报告，待真机数据）
├── tasks/                   # plan.md、todo.md
├── skills/                  # 评测流程 Skill（必交项）
└── skills-creator/          # Skills Creator 整改记录
```

工作区路径中 `src/src/` 是交付区下的源码目录。正式提交目录是否需含“姓名拼音－课题简称”层级，以部门指定位置为准。

## 验证与交付记录

| 记录 | 说明 |
|---|---|
| [tests/results/replay-smoke/](tests/results/replay-smoke/report.md) | 回放冒烟报告（7/7，replay 通道） |
| [tests/results/api-smoke-2026-10-16.md](tests/results/api-smoke-2026-10-16.md) | L2 真实 API 冒烟（发现并修复工具名 API 命名冲突） |
| [tests/results/planning-validation-2026-10-13.md](tests/results/planning-validation-2026-10-13.md) | 需求与方案文档核验 |
| [midterm.md](midterm.md) | 中期检查（待开展） |
| [skills-creator/fix-log.md](skills-creator/fix-log.md) | Skill 整改记录（待执行） |

## 工作区资料

公司任务资料见 [../docs/README.md](../docs/README.md)，跨对话状态见 [../memory/CURRENT.md](../memory/CURRENT.md)。这些链接依赖当前工作区布局；正式打包前须补齐独立使用说明。
