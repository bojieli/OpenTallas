"""KW-FIX-23: a retry item@N releases attempt N only if N launched before the entry was first seen."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as kw


def _cfg(retry):
    return {"dies": {"s81": {"retry": list(retry)}}}


def _st(attempt, started):
    return {"items": {"s81|t50|babc": {"die": "s81", "item": "t50", "attempt": attempt, "started": started}}}


def test_release_of_failed_attempt_kept():
    st = _st(3, 100.0)
    cfg = _cfg(["t50@3"])
    kw.prune_stale_retries(cfg, st, now=200.0)
    assert cfg["dies"]["s81"]["retry"] == ["t50@3"]


def test_future_attempt_entry_is_stale_when_reached():
    st = _st(3, 100.0)
    cfg = _cfg(["t50@3", "t50@4", "t50@5"])
    kw.prune_stale_retries(cfg, st, now=200.0)          # first seen at 200
    st["items"]["s81|t50|babc"].update(attempt=4, started=300.0)
    cfg = _cfg(["t50@3", "t50@4", "t50@5"])             # config reloads each tick
    logs = []
    kw.prune_stale_retries(cfg, st, log=logs.append, now=400.0)
    assert cfg["dies"]["s81"]["retry"] == ["t50@3", "t50@5"]
    assert logs and "t50@4" in logs[0]
    cfg = _cfg(["t50@4"])
    kw.prune_stale_retries(cfg, st, log=logs.append, now=500.0)
    assert cfg["dies"]["s81"]["retry"] == [] and len(logs) == 1   # logged once


def test_entry_for_running_attempt_kept():
    st = _st(2, 100.0)
    cfg = _cfg(["t50@2"])
    kw.prune_stale_retries(cfg, st, now=150.0)
    assert cfg["dies"]["s81"]["retry"] == ["t50@2"]


def test_unknown_item_kept():
    st = {"items": {}}
    cfg = _cfg(["x@1"])
    kw.prune_stale_retries(cfg, st, now=1.0)
    assert cfg["dies"]["s81"]["retry"] == ["x@1"]


def test_default_clock_and_string_times():
    """13:57 hub crash: now defaulted to the now_s() display string; started may be a string; old seen strings"""
    st = {"items": {"a": {"die": "s", "item": "x", "attempt": 3, "started": "100.5"},
                    "b": {"die": "s", "item": "y", "attempt": 2, "started": "bad"}},
          "retry_seen": {"s|x@3": "2026-11-06 13:57 PST"}}
    cfg = {"dies": {"s": {"retry": ["x@3", "y@2"]}}}
    assert kw.prune_stale_retries(cfg, st) == {}
    assert cfg["dies"]["s"]["retry"] == ["x@3", "y@2"]
    assert all(isinstance(v, float) for v in st["retry_seen"].values())


def test_new_event_release_not_judged_by_older_event():
    """KW-FIX-33: t12@3 first seen on event E1; the plan moves to E2, whose attempt 3 launches and fails; COORD's
    release of t12@3 on E2 must not inherit E1's first-seen time"""
    st = _st(2, 100.0)
    cfg = {"dies": {"s81": {"event": "E1", "retry": ["t50@3"]}}}
    kw.prune_stale_retries(cfg, st, now=200.0)                       # first seen on E1 at 200
    st["items"]["s81|t50|babc"].update(attempt=3, started=300.0)    # E2's attempt 3
    cfg = {"dies": {"s81": {"event": "E2", "retry": ["t50@3"]}}}
    assert kw.prune_stale_retries(cfg, st, now=400.0) == {}
    assert cfg["dies"]["s81"]["retry"] == ["t50@3"]
    assert st["retry_seen"]["s81|E2|t50@3"] == 400.0 and st["retry_seen"]["s81|E1|t50@3"] == 200.0


def test_legacy_key_migrates_to_current_event_without_rearm():
    """rollout: a legacy die|item@N time moves to the current event key once, so a stale entry stays stale"""
    st = _st(4, 300.0)
    st["retry_seen"] = {"s81|t50@4": 200.0}
    st["retry_stale_logged"] = {"s81|t50@4": 250.0}
    cfg = {"dies": {"s81": {"event": "E1", "retry": ["t50@4"]}}}
    logs = []
    kw.prune_stale_retries(cfg, st, log=logs.append, now=500.0)
    assert cfg["dies"]["s81"]["retry"] == [] and logs == []          # still stale, already logged
    assert st["retry_seen"] == {"s81|E1|t50@4": 200.0}
    assert st["retry_stale_logged"] == {"s81|E1|t50@4": 250.0}
    st["items"]["s81|t50|babc"].update(attempt=4, started=600.0)    # a later event: fresh entries
    cfg = {"dies": {"s81": {"event": "E2", "retry": ["t50@4"]}}}
    kw.prune_stale_retries(cfg, st, log=logs.append, now=700.0)
    assert cfg["dies"]["s81"]["retry"] == ["t50@4"]
    assert st["retry_seen"]["s81|E2|t50@4"] == 700.0


def test_stale_logged_once_per_event():
    st = _st(3, 300.0)
    st["retry_seen"] = {"s81|E1|t50@3": 200.0}
    logs = []
    for now in (400.0, 500.0):
        cfg = {"dies": {"s81": {"event": "E1", "retry": ["t50@3"]}}}
        kw.prune_stale_retries(cfg, st, log=logs.append, now=now)
    assert len(logs) == 1 and "s81|E1|t50@3" in st["retry_stale_logged"]
