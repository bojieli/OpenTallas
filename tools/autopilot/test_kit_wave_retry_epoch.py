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
