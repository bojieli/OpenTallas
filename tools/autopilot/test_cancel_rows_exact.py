"""FLOW-FIX-0100 (FABLE-FLOW-2350): cancel-rows --event/--attempt select exactly one (item, event, attempt) row (folds in S81-DIE-R5's cancel_exact.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def rows():
    mk = lambda ev, att, st="RUNNING": {"die": "s81", "item": "t1", "event": ev, "attempt": att, "status": st, "block_sha": "b" * 12}
    return {"items": {"k1": mk("E1", 2), "k2": mk("E1", 3), "k3": mk("E2", 2), "k4": mk("E1", 1, "FAIL")}}


def run(**kw):
    st = rows()
    _stops, done = KW.cancel_rows_core(None, {"dies": {"s81": {}}}, st, "s81", "t1", "why", "own", "STRUCTURAL", {}, dry=True, **kw)
    return sorted(d[0] for d in done)


def test_event_and_attempt_select_exact_rows():
    assert run() == ["k1", "k2", "k3"]
    assert run(event="E1") == ["k1", "k2"]
    assert run(event="E1", attempt="2") == ["k1"]
    assert run(event="E2", attempt=2) == ["k3"]
    assert run(event="E9", attempt="2") == []


def test_cli_accepts_event_and_attempt():
    src = (Path(__file__).resolve().parent / "kit_wave.py").read_text()
    assert '"--event"' in src and '"--attempt"' in src and "event=a.event, attempt=a.attempt" in src
