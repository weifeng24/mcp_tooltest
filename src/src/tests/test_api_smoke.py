"""API 冒烟脚本的离线验证：真实网络边界由脚本化 provider 替代。"""
import importlib.util
import sys
from pathlib import Path

from mcp_eval.providers.base import ProviderError, ProviderResponse, ToolCallDecision


def load_script():
    path = Path(__file__).resolve().parents[2] / "scripts/api_smoke.py"
    spec = importlib.util.spec_from_file_location("api_smoke_test_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_uses_stateful_mock_and_strict_verdict(monkeypatch, capsys):
    module = load_script()
    class Script:
        first = True
        def chat(self, messages, tools, **kwargs):
            if self.first:
                self.first = False
                return ProviderResponse(tool_calls=[ToolCallDecision("1", "HvacService_setTemp", {"temperature": 22})])
            return ProviderResponse(content="已设置22度")
    monkeypatch.setattr(module, "create_provider", lambda _: Script())
    monkeypatch.setattr(sys, "argv", ["api_smoke.py", "configs/models/deepseek.json"])
    assert module.main() == 0
    output = capsys.readouterr().out
    assert "synthetic" in output and "verdict:          pass" in output


def test_smoke_provider_failure_cannot_exit_success(monkeypatch, capsys):
    module = load_script()
    class Broken:
        def chat(self, messages, tools, **kwargs):
            raise ProviderError("offline test outage")
    monkeypatch.setattr(module, "create_provider", lambda _: Broken())
    monkeypatch.setattr(sys, "argv", ["api_smoke.py", "configs/models/deepseek.json"])
    assert module.main() == 1
    assert "unassessed" in capsys.readouterr().out
