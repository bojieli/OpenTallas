"""EMIT-HEARTBEAT-1123 (COORD): the QC V4 seal bind was killed by the no-progress watchdog (exit 143) during ~2.3 h of silent
emit; emit now prints "EMIT n/N types" every $OT_BIND_EMIT_BEAT_S seconds from the serial loop, the parallel poll loop and the top."""
import io
import os
import sys
import time
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import bind  # noqa: E402
import bind_emit_par  # noqa: E402


def test_beat_rate_limited_and_forced():
    buf = io.StringIO()
    b = bind.EmitBeat(7, every=3600, out=buf)
    b.beat(); b.beat()
    assert buf.getvalue() == ""
    b.done = 3
    b.beat(force=True)
    assert buf.getvalue().startswith("EMIT 3/7 types (types, ")


def test_thread_beats_while_a_type_is_slow_and_stops():
    buf = io.StringIO()
    b = bind.EmitBeat(2, every=0.05, out=buf)
    b._stop = None
    import threading
    b.start()
    t0 = time.time()
    while buf.getvalue().count("EMIT 0/2") < 2 and time.time() - t0 < 5:
        time.sleep(0.01)
    b.stop()
    n = buf.getvalue().count("\n")
    assert n >= 2 and b._th is None
    time.sleep(0.15)
    assert buf.getvalue().count("\n") == n                        # stopped: no more lines


def test_env_period_and_zero_disables(monkeypatch):
    monkeypatch.setenv("OT_BIND_EMIT_BEAT_S", "0")
    b = bind.EmitBeat(1, out=io.StringIO())
    b.start()
    assert b._th is None and b.every == 0
    monkeypatch.setenv("OT_BIND_EMIT_BEAT_S", "junk")
    assert bind.EmitBeat(1).every == 60.0


class _B:
    def __init__(self, n, sleep):
        self.by_type = {f"t{i}": [f"p{i}"] for i in range(n)}
        self.sleep = sleep

    def _emit_one(self, tn, ps, out, files):
        time.sleep(self.sleep)


def test_parallel_poll_loop_beats(tmp_path, monkeypatch):
    """the parent of the forked workers beats from its poll loop; a worker failing for this toy binder is fine (ParUnsafe)"""
    if not hasattr(os, "fork"):
        return
    buf = io.StringIO()
    b = bind.EmitBeat(2, every=0.05, out=buf)
    monkeypatch.setattr(bind_emit_par, "hist_load", lambda out: {})
    try:
        bind_emit_par.run(_B(2, 0.4), str(tmp_path / "rtl"), [], 2, rec_path=str(tmp_path / "rec.json"), beat=b)
    except Exception:  # noqa: BLE001 - only the beat lines are under test
        pass
    assert "EMIT 0/2 types (types j=2, running " in buf.getvalue()
