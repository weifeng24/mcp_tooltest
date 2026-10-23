"""用本地Chromium检查阶段展示和官方复核页面，可录制合成执行记录回看视频。"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true", help="录制约35秒无旁白的已执行记录回看，不执行评测器")
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright

    temp = ROOT / ".tools/browser-tmp"
    temp.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(temp)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "tests/results/local-completion-2026-10-23" / f"browser-{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    cache = Path.home() / ".cache/ms-playwright"
    browsers = sorted(cache.glob("chromium_headless_shell-*/chrome-linux/headless_shell"))
    if not browsers:
        browsers = sorted(cache.glob("chromium-*/chrome-linux/chrome"))
    if not browsers:
        parser.error("未找到已有Chromium；需先准备项目内浏览器测试环境")
    console_errors, page_errors, external_requests = [], [], []
    result = {"recorded": False, "browser": str(browsers[-1]), "screenshots": [], "status": "running"}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(browsers[-1]), headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        context.route("https://**", lambda route: (external_requests.append(route.request.url), route.abort()))
        context.route("http://**", lambda route: (external_requests.append(route.request.url), route.abort()))
        page = context.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto((ROOT / "docs/defense/index.html").as_uri())
        page.wait_for_load_state("networkidle")
        assert page.locator("main section.slide").count() == 6
        for anchor in ("intro", "background", "solution", "skill", "demo", "result"):
            page.locator(f"nav a[href='#{anchor}']").click()
            assert page.locator(f"#{anchor}").is_visible()
        page.goto((ROOT / "docs/defense/index.html").as_uri())
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(out / "defense-desktop.png"))
        page.locator("#skill").screenshot(path=str(out / "defense-skill.png"))
        result["screenshots"] += ["defense-desktop.png", "defense-skill.png"]
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.goto((ROOT / "docs/defense/index.html").as_uri())
        page.screenshot(path=str(out / "defense-mobile.png"))
        result["screenshots"].append("defense-mobile.png")
        page.goto((ROOT / "docs/defense/offline-demo.html").as_uri())
        page.wait_for_load_state("networkidle")
        assert page.locator("[data-step]").count() == 5
        page.locator("[data-step='3']").click()
        assert '"fail": 1' in page.locator("#output").inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(out / "demo-mobile.png"))
        page.set_viewport_size({"width": 1366, "height": 900})
        page.goto((ROOT / "skills/mcp-eval-workspace/iteration-6/review.html").as_uri())
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Benchmark", exact=True).click()
        assert page.locator("#benchmark-content").get_by_text("Per-Eval Breakdown", exact=True).is_visible()
        page.screenshot(path=str(out / "skill-benchmark.png"))
        result["screenshots"] += ["demo-mobile.png", "skill-benchmark.png"]
        if args.record:
            recording_context = browser.new_context(viewport={"width": 1280, "height": 800},
                record_video_dir=str(out / "video"), record_video_size={"width": 1280, "height": 800})
            recording_page = recording_context.new_page()
            recording_page.goto((ROOT / "docs/defense/offline-demo.html").as_uri())
            recording_page.wait_for_load_state("networkidle")
            for step in range(5):
                recording_page.locator(f"[data-step='{step}']").click()
                recording_page.wait_for_timeout(6500)
            recording_page.screenshot(path=str(out / "demo-desktop.png"))
            video = recording_page.video
            recording_context.close()
            video.save_as(str(ROOT / "docs/defense/offline-demo.webm"))
            assert (ROOT / "docs/defense/offline-demo.webm").stat().st_size > 1000
            subprocess.run([sys.executable, "-B", "scripts/build_defense.py"], cwd=ROOT, check=True)
            page.goto((ROOT / "docs/defense/index.html").as_uri())
            page.wait_for_function("document.querySelector('video') && document.querySelector('video').readyState >= 1")
            result["video_seconds"] = page.locator("video").evaluate("element => element.duration")
            assert result["video_seconds"] > 30
            result["recorded"] = True
            result["screenshots"].append("demo-desktop.png")
        context.close()
        browser.close()
    result.update(status="passed" if not page_errors else "failed", page_errors=page_errors,
                  console_errors=console_errors, blocked_external_requests=external_requests,
                  six_sections=True, mobile_horizontal_overflow=False, official_benchmark_visible=True)
    (out / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evidence": str(out.relative_to(ROOT)), **result}, ensure_ascii=False, indent=2))
    assert not page_errors


if __name__ == "__main__":
    main()
