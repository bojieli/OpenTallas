"""PREGRT-HOLD-WATCHDOG-1123: pregrt_ff_hold gets a 2 h window (a flat non-zero TNS is NO-PROGRESS); NOPROG-TNS0-1124: TNS 0 is PROGRESS."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import noprog_watchdog as W  # noqa: E402

H = 3600.0


def res(series, growth_idx, n):
    return {"name": "repair_TNS", "series": series, "growth_idx": growth_idx, "n": n}


def test_step_window():
    assert W.step_window("/k/work/pregrt_ff_hold.log") == (2 * H, True)
    assert W.step_window("/k/run/logs/5_1_grt.tmp.log") == (W.WINDOW_S, False)


def test_reached_zero_but_silent_is_progress_tns0_1124():
    # NOPROG-TNS0-1124 reverses the 1123 zero half: repair_TNS 0 (TNS >= 0) is converged, never NO-PROGRESS, even when silent
    now = 1_000_000.0
    anchors = [(now - 12 * H, 0), (now - 11 * H, 10)]          # the last line was written 11 h ago
    r = res([(5, 0.0)], 9, 10)
    v, why, _ = W.judge(r, anchors, now, window=2 * H, exact=True, zero_needs_growth=True)
    assert v == "PROGRESS", why
    r2 = dict(res([(5, 0.0)], 4, 10))
    anchors2 = [(now - 3 * H, 0), (now - 1.5 * H, 6), (now - 1.4 * H, 10)]
    r2["growth_idx"] = 0
    assert W.judge(r2, anchors2, now, window=2 * H, exact=True, zero_needs_growth=True)[0] == "PROGRESS"
    assert W.judge(r2, anchors2, now, window=2 * H, exact=True)[0] == "PROGRESS"


def test_reached_zero_and_writing_is_progress():
    now = 1_000_000.0
    anchors = [(now - 3 * H, 0), (now - 0.2 * H, 10)]
    v, _, _ = W.judge(res([(5, 0.0)], 9, 10), anchors, now, window=2 * H, exact=True, zero_needs_growth=True)
    assert v == "PROGRESS"


def test_flat_metric_two_hours():
    now = 1_000_000.0
    anchors = [(now - 5 * H, 0), (now - 2.5 * H, 10)]
    v, _, _ = W.judge(res([(2, 495634.0), (9, 495634.0)], 9, 10), anchors, now, window=2 * H, exact=True, zero_needs_growth=True)
    assert v == "NO-PROGRESS"
