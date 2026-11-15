"""KW-FIX-7: a launch error on one row does not end the wave pass."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


class AP:
    logs = []
    @classmethod
    def log(cls, m):
        cls.logs.append(m)


def test_launch_error_is_logged_and_returns_none(monkeypatch):
    AP.logs.clear()
    def boom(*a, **k):
        raise ValueError("resume helper differs from pinned scheduler commit")
    monkeypatch.setattr(K, "launch", boom)
    assert K.launch_safe(AP, {}, {}, "qwen_kvsys", {"item": "kv3_hgi_v7"}, "hub") is None
    assert "LAUNCH-SKIP qwen_kvsys/kv3_hgi_v7" in AP.logs[0] and "resume helper" in AP.logs[0]


def test_launch_result_passes_through(monkeypatch):
    seen = {}
    def ok(ap, cfg, st, die, r, hub, delay_s=0.0):
        seen["delay"] = delay_s
        return {"unit": "u"}
    monkeypatch.setattr(K, "launch", ok)
    assert K.launch_safe(AP, {}, {}, "d", {"item": "i"}, "hub", delay_s=2.5) == {"unit": "u"}
    assert seen["delay"] == 2.5
