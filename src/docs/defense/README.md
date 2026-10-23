# 阶段答辩稿与离线演示

材料快照：2026-10-23。基于公司HTML模板，已填入可核验的项目范围、方案、开发验证和Skill行为结果。真实业务基线、真机结果、培训分类与个人协作实例明确待补，本稿不是正式结题或导师认可版本。

## 查看方式

在本机Ubuntu文件管理器进入项目`src/docs/defense/`，双击`index.html`，用浏览器打开。页面包含封面及六个章节；顶部导航可跳转。若浏览器默认打开源代码，右键文件选择已有浏览器“打开方式”。预期看到郑炜峰、MCP工具评测、阶段材料标记及当前证据边界。

演示章节可打开`offline-demo.html`，点击五个步骤查看已执行命令及结果；原始stdout链接指向交付区`tests/results/`。这是执行记录回看，不会在浏览器中运行Python、连接设备或发起模型请求。缺文件时须保留完整交付目录，不要只拷贝一个HTML后声称证据仍齐全。

`offline-demo.webm`为无旁白屏幕录制，可在展示页播放或单独打开。录制内容为本机合成命令记录回看，不是真实车机画面，也不是实时执行终端。配套讲解见[speaker-notes.md](speaker-notes.md)。

## 文件与证据

- `index.html`：六部分阶段展示稿，复用公司模板样式。
- `company-template.html`：原公司模板的副本；`body.html`为本项目填充内容。
- `demo-session.json`：实际命令、原始stdout/stderr路径、退出码、执行副本及本机验证。
- `offline-demo.html`：独立浏览器回看页；页面明确synthetic和记录回看来源。
- `build-metadata.json`：模板及Skill摘要、生成范围。
- [Skill官方复核页面](../../skills/mcp-eval-workspace/iteration-6/review.html)：可查看七场景两组输出和评分。

## 生成与检查

Ubuntu Bash，工作目录为交付区根目录`src/`。以下是维护命令，正常查看无需重新执行。先按根README准备Python依赖；需要重新录屏时另需Playwright与可用Chromium。

```bash
python3 scripts/build_defense.py --help
python3 scripts/build_defense.py
```

该命令重新生成两个HTML，读取已有demo-session，不重新评测。没有demo-session时先处理缺失输入，不能用手写成功输出补齐。

```bash
PYTHONPATH=src .venv/bin/python scripts/prepare_local_demo.py
```

该命令仅在交付区建立新的隔离运行副本，实际运行合成回放、构造的异常场景及报告重建，并更新demo-session。异常场景预期退出1（发现失败），脚本整体验证成功仍返回0。运行失败时先查看所打印证据路径，不删除失败批次。

本机实际验证复用了`tests/results/remediation-2026-10-16/.venv/bin/python`；没有重新安装产品依赖。浏览器检查依赖安装在`.tools/browser`，检查脚本为`scripts/check_defense.py`，不是产品运行依赖。

## 正式提交前

以真实采集素材更新业务结果和演示，补培训定义与本人经历，完成导师review和计时演练。HTML能否替代框架所列PPT、最终文件名及提交入口按部门明确口径处理。
