# 10-23本地材料验证索引

本目录记录本地演示、浏览器检查和材料核对；没有真实车机或被测模型API调用。Skill的AI执行证据另在`skills/mcp-eval-workspace/iteration-6/`。

| 检查 | 结果 | 证据 |
|---|---|---|
| 独立演示副本 | 8项合成回放通过、构造负面1项fail、重建一致 | [demo验证](demo-20261023T083910590905Z/verification.json)、[实际命令](demo-20261023T083910590905Z/commands.json) |
| 首次浏览器启动 | 完整Chromium启动SIGTRAP，未完成页面验证 | [失败记录](browser-20261023T084429463907Z/failure.md) |
| headless shell浏览器检查 | 六章节导航、移动宽度、交互回看、官方Benchmark可见，33.2秒视频可读 | [browser验证](browser-20261023T084549173782Z/verification.json)及同目录截图 |
| Creator结构/环境 | 官方结构检查、脚本帮助/环境检查通过 | [最终材料核对](checks-20261023T085959175761Z/verification.json)及同目录stdout/stderr |
| 自动触发准备 | 20条查询格式有效；缺claude CLI，授权未核验，未执行真实触发 | [trigger-env](checks-20261023T085959175761Z/trigger-env.stdout.txt)，预期退出2 |
| 来源与链接 | 产品源码与184项验证及新演示快照一致；Skill/公司原模板未变；18份Markdown及展示页175个本地链接无断链 | [最终材料核对](checks-20261023T085959175761Z/verification.json) |

本轮没有再次运行184项软件测试：产品源码未变，通过哈希核对与既有测试快照建立对应关系；新增自动化脚本使用实际输入/产物检查。独立演示复用已有解释器，不等于干净机器安装验证或正式完整打包。

官方静态复核页面以file方式打开时会尝试本地反馈API，出现一个已捕获console警告；无未捕获页面异常，输出与评分可见。没有代替用户填写反馈，也未获得导师认可。
