"""基于公司HTML样式生成独立阶段展示稿及本机合成演示记录页面。"""
import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/defense"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    template = DEST / "company-template.html"
    if not template.exists():
        shutil.copy2(ROOT.parent / "docs/2026-TS-Force-AI实战演练-校招生答辩模板.html", template)
    source = template.read_text(encoding="utf-8")
    style = re.search(r"<style>(.*?)</style>", source, re.S)[1]
    body = (DEST / "body.html").read_text(encoding="utf-8")
    video = ('<video controls preload="metadata" src="offline-demo.webm" aria-label="本机合成执行记录回看录屏"></video>'
             '<p>无旁白录屏；内容为已执行合成命令的记录回看，配套讲解见speaker-notes.md。</p>'
             if (DEST / "offline-demo.webm").exists() else '<p class="pending">本机离线记录回看已可打开；录屏正在制作。</p>')
    body = body.replace("@@VIDEO@@", video)
    navigation = '<nav><div class="logo">TS-Force · MCP评测</div><ul>' + "".join(
        f'<li><a href="#{anchor}">{label}</a></li>' for anchor, label in (
            ("intro", "概览"), ("background", "目标"), ("solution", "方案"), ("skill", "Skill"), ("demo", "演示"), ("result", "总结"))) + '</ul></nav>'
    extra = 'ul,ol{padding-left:20px}p+ p,li+li{margin-top:8px}a{color:#2454c4;overflow-wrap:anywhere}.pending{padding:12px;background:#fff7e6;border-left:3px solid #d97706;border-radius:6px;margin-top:12px}.hero-note{color:#c9d6ff;margin-top:20px;max-width:720px}.action-link{display:inline-block;background:#1a2b6d;color:white;padding:12px 18px;border-radius:10px;margin:16px 8px 16px 0}video{display:block;width:100%;max-width:960px;border-radius:12px;background:#14213d;margin-top:16px}.module-table{table-layout:fixed}.module-table td{overflow-wrap:anywhere}.slide{scroll-margin-top:56px}@media(max-width:560px){nav{padding:12px}.meta{gap:20px}.stat{min-width:120px}.module-table{font-size:12px}.module-table td,.module-table th{padding:8px}}'
    page = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MCP工具评测 · 阶段答辩稿</title><style>' + style + extra + '</style></head><body>' + navigation + body + '</body></html>'
    (DEST / "index.html").write_text(page, encoding="utf-8")
    session = json.loads((DEST / "demo-session.json").read_text())
    payload = json.dumps(session, ensure_ascii=False).replace("<", "\\u003c")
    buttons = "".join(f'<button data-step="{index}">{html.escape(step["title"])}</button>' for index, step in enumerate(session["steps"]))
    demo = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MCP评测 · 离线执行记录回看</title><style>
body{margin:0;font:16px/1.6 "Microsoft YaHei",sans-serif;background:#f5f7fb;color:#1f2430}main{max-width:1120px;margin:auto;padding:30px 20px}h1{color:#1a2b6d;margin:0}.notice{padding:12px 16px;background:#fff7e6;border-left:4px solid #d97706}#steps{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}button{border:1px solid #b6c4e0;background:white;color:#1a2b6d;border-radius:8px;padding:10px;cursor:pointer;font:inherit}button[aria-pressed=true]{background:#1a2b6d;color:white}.terminal{padding:20px;border-radius:12px;background:#102033;color:#d8edf4;min-height:310px}pre{font:14px/1.55 monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:12px 0}#command{color:#8edfc2}a{color:#2454c4;overflow-wrap:anywhere}#source{font-size:13px;color:#58657c}#caption{font-weight:600}@media(max-width:600px){main{padding:20px 12px}pre{font-size:12px}.terminal{padding:14px}h1{font-size:26px}}
</style></head><body><main><h1>评测过程与证据回看</h1><p class="notice">SYNTHETIC · 本机合成数据。下方回看已实际执行的命令记录，不是实时终端，也不证明车机或真实模型能力。</p><div id="steps">''' + buttons + '''</div><div class="terminal"><div id="caption"></div><pre id="command"></pre><pre id="output"></pre></div><p id="source"></p><p><a id="raw" href="#">查看本步原始stdout</a> · <a href="index.html#demo">返回答辩稿</a></p></main><script>
const data = ''' + payload + ''';
function showStep(i){const step=data.steps[i];document.getElementById('caption').textContent=step.title+' · 实际退出码 '+step.returncode;document.getElementById('command').textContent=step.display_command;document.getElementById('output').textContent=step.display_output||step.stdout;document.getElementById('source').textContent='记录时间 '+data.recorded_at+' | '+data.presentation_mode;document.getElementById('raw').href='../../'+step.stdout_path;document.querySelectorAll('[data-step]').forEach((b,k)=>b.setAttribute('aria-pressed',String(k===i)));}
document.querySelectorAll('[data-step]').forEach((b)=>b.addEventListener('click',()=>showStep(Number(b.dataset.step))));showStep(0);
</script></body></html>'''
    (DEST / "offline-demo.html").write_text(demo, encoding="utf-8")
    (DEST / "build-metadata.json").write_text(json.dumps({"company_template_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        "skill_runtime_sha256": hashlib.sha256((ROOT / "skills/mcp-eval/SKILL.md").read_bytes()).hexdigest(),
        "status": "stage_draft_not_final_acceptance", "outputs": ["index.html", "offline-demo.html"],
        "external_assets": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("已生成 docs/defense/index.html 与 offline-demo.html；阶段稿，真实业务与验收待补。")


if __name__ == "__main__":
    main()
