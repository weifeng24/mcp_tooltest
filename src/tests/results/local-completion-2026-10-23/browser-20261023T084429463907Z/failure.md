# 初次浏览器检查未完成

命令：`PYTHONPATH=.tools/browser python3 -B scripts/check_defense.py --record`，交付区Ubuntu Bash执行。

实际现象：Playwright启动现有`chromium-1194/chrome-linux/chrome`后，进程以SIGTRAP结束，报`TargetClosedError`。stderr包含`crashpad/snapshot/elf/elf_dynamic_array_reader.h:64 tag not found`；失败发生在页面加载之前，不能据此判断HTML有缺陷。

随后检查：该二进制`--version`可返回Chromium 141.0.7390.37，ldd未显示缺失依赖，但完整浏览器启动根因未确定。没有禁用或修改系统审计/动态加载配置。使用现有同版本`chromium_headless_shell-1194/chrome-linux/headless_shell`的最小渲染成功，检查脚本优先选择该无界面二进制，后续完整检查另存新目录。

本目录保留失败事实，不视为通过的浏览器证据。
