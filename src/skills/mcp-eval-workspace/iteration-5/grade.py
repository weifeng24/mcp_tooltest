"""场景4局部新旧Skill复测；分数不与全四场景总分混合。"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUOTES = {
    "with_skill": ["N02 判为 `fail`", "越界拒绝行为未满足", "保留规范版本", "区分接受、截断或未生效，再按现场已确认的方法恢复", "不能据此次响应将预期改为成功"],
    "old_skill": ["N02 应判为 `fail`", "未得到预期的越界拒绝结果", None, None, "不能根据实际结果倒改预期"],
}


def main():
    meta = json.loads((HERE / "eval-4/eval_metadata.json").read_text())
    rows = []
    for group, quotes in QUOTES.items():
        directory = HERE / "eval-4" / group
        answer = (directory / "outputs/answer.md").read_text()
        expectations = []
        for index, (text, quote) in enumerate(zip(meta["expectations"], quotes)):
            if quote:
                assert quote in answer
                evidence = "outputs/answer.md: " + quote
            else:
                evidence = ("旧版回答保留了请求响应，但未明确保留规范/工具版本。" if index == 2
                            else "旧版回答说明状态不能推断，但没有建议独立回读区分接受/截断及现场恢复。")
            expectations.append({"text": text, "passed": quote is not None, "evidence": evidence})
        passed = sum(item["passed"] for item in expectations)
        summary = {"passed": passed, "failed": 5 - passed, "total": 5, "pass_rate": passed / 5}
        (directory / "grading.json").write_text(json.dumps({"expectations": expectations, "summary": summary}, ensure_ascii=False, indent=2) + "\n")
        task_id = "ses_ea774b093ffeQ9TZAuEW6iSCQM" if group == "with_skill" else "ses_ea774b088ffeYToWwh2g2RdNeH"
        (directory / "timing.json").write_text(json.dumps({"task_id": task_id, "total_tokens": None, "duration_ms": None,
              "total_duration_seconds": None, "reason": "Task未提供可信耗时/token"}, ensure_ascii=False, indent=2) + "\n")
        rows.append({"configuration": group, **summary})
    (HERE / "comparison.json").write_text(json.dumps({"scope": "场景4局部复测；旧版Skill基线，不是无Skill基线",
          "results": rows, "causal_claim": False, "automatic_trigger_tested": False,
          "limitations": ["每版仅一次，不证明稳定增益", "共享项目历史摘要，不是完全盲评", "新版全四场景未重新运行"]}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
