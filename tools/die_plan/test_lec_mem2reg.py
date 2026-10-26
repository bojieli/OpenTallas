"""Retry only the unmappable slang array; never turn a gold elaboration failure into proof."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def test_multiclock_array_retry_preserves_failure_then_reelaborates(monkeypatch, tmp_path):
    scripts = []
    monkeypatch.setattr(lec, "gold_script", lambda *args, slang_extra=(): tuple(slang_extra))
    def run(script, path, log):
        scripts.append(script)
        if not script:
            raise lec.Unproven("yosys gold.ys failed: ERROR: Unsupported cell type: $mem_v2 (delay.r)")
        return "real gold AIG generated"
    monkeypatch.setattr(lec, "run_yosys", run)
    rec, log = {}, []
    assert lec.run_gold({}, tmp_path, "slang", {}, tmp_path, log, rec) == "real gold AIG generated"
    assert scripts == [(), ("--no-implicit-memories",)]
    assert rec["gold_no_implicit_memories"] is True
    assert "re-reading" in log[0]


@pytest.mark.parametrize("frontend,reason", [
    ("verilog", "Unsupported cell type: $mem_v2"),
    ("slang", "gold output has an undriven wire"),
    ("slang", "Unsupported cell type: $mystery"),
])
def test_unrelated_gold_errors_remain_unproven(monkeypatch, tmp_path, frontend, reason):
    calls = []
    monkeypatch.setattr(lec, "gold_script", lambda *args, slang_extra=(): tuple(slang_extra))
    def run(script, path, log):
        calls.append(script)
        raise lec.Unproven(reason)
    monkeypatch.setattr(lec, "run_yosys", run)
    rec = {}
    with pytest.raises(lec.Unproven, match=reason.replace("$", r"\$")):
        lec.run_gold({}, tmp_path, frontend, {}, tmp_path, [], rec)
    assert calls == [()]
    assert not rec


def test_retry_failure_stays_unproven(monkeypatch, tmp_path):
    monkeypatch.setattr(lec, "gold_script", lambda *args, slang_extra=(): tuple(slang_extra))
    def run(script, path, log):
        raise lec.Unproven("still unmappable" if script else "Unsupported cell type: $mem_v2")
    monkeypatch.setattr(lec, "run_yosys", run)
    with pytest.raises(lec.Unproven, match="still unmappable"):
        lec.run_gold({}, tmp_path, "slang", {}, tmp_path, [], {})
