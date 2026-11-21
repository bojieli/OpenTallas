"""FLOW-OPS-1000: a DRT iteration whose in-iteration count is still falling is never NO-PROGRESS (FABLE-PD-S81-1100 #2)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import noprog_watchdog as W  # noqa: E402

H = 3600.0


def _judge(active):
    lines = ["[INFO DRT-0195] Start 0th optimization iteration."]
    lines += ["    Completing %d%% with %d violations." % (p, v) for p, v in ((10, 20000), (50, 90000), (100, 151954))]
    lines += ["[INFO DRT-0199]   Number of violations = 151954.", "[INFO DRT-0195] Start 1st optimization iteration."]
    lines += ["    Completing %d%% with %d violations." % (p, v) for p, v in active]
    res = W.extract("drt", "\n".join(lines) + "\n")
    # col_h9_r0 rep 0d6487d7a8c6: iteration 0 ended after 3h46m, iteration 1 ran 2h20m more
    anchors = [(0.0, 0), (3.77 * H, 4), (6.1 * H, len(lines))]
    return W.judge(res, anchors, 6.15 * H, exact=True)


def test_falling_active_iteration_is_progress():
    v, why, _ = _judge([(10, 140000), (30, 120000), (50, 90000), (70, 60258)])
    assert v == "PROGRESS", why
    assert "active iteration" in why


def test_flat_active_iteration_still_no_progress():
    v, why, _ = _judge([(10, 151000), (30, 150900), (50, 151100), (70, 150950)])
    assert v == "NO-PROGRESS", why
