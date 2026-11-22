"""RETIRED-HOSTS-1122 (FLOW-OPS-R2): autopilot never ssh's a retired build host; auto-resign rows on one become SKIP, not WAIT for ever."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP  # noqa: E402
import auto_resign as AR  # noqa: E402


def test_rpy_and_rbash_never_ssh_a_retired_host(monkeypatch):
    calls = []
    monkeypatch.setattr(AP, "sh", lambda *a, **k: calls.append(a) or (0, "", ""))
    for h in ("epyc1", "epyc3", "epyc4", "epyc5", "epyc6"):
        assert AP.rpy(h, "print(1)", {})["error"].startswith("RETIRED-HOST")
        assert AP.rbash(h, "true")[0] == 255
    assert calls == []
    AP.rpy("epyc10", "print(1)", {})
    assert calls                                   # a live host is still probed


def test_judge_skips_retired_host_rows():
    act, why = AR.judge({"die": "s81", "name": "x", "host": "epyc4"}, {"error": "RETIRED-HOST epyc4: retired build host"}, {}, {})
    assert act == "SKIP" and why.startswith("RETIRED-HOST")
    act, _ = AR.judge({"die": "s81", "name": "x", "host": "epyc7"}, {"error": "probe rc 255: timeout"}, {}, {})
    assert act == "WAIT"
