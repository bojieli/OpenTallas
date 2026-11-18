"""FLOW-2200 G: the heavy fleet-wide reaps take turns (one per pass) and are skipped past the step budget, never starved more than 2 passes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW


def test_one_heavy_reap_per_pass():
    for n in range(6):
        st = {"pass_n": n}
        due = [x for x in KW.HEAVY_REAPS if KW.heavy_due(st, x, now=10.0, start=0.0)]
        assert due == [KW.HEAVY_REAPS[n % 3]]


def test_non_heavy_phases_always_run():
    assert KW.heavy_due({"pass_n": 5}, "collect")


def test_over_budget_defers_then_runs_after_two_skips():
    st = {"pass_n": 0}
    late = KW.STEP_BUDGET_S + 5
    assert KW.heavy_due(st, "reap_dead", now=late, start=0.0) is False               # its turn, but the step is over budget
    st["pass_n"] = 1
    assert KW.heavy_due(st, "reap_dead", now=late, start=0.0) is False               # not its turn
    st["pass_n"] = 3
    assert KW.heavy_due(st, "reap_dead", now=late, start=0.0) is False               # its turn again, over budget again (deferred twice)
    st["pass_n"] = 4
    assert KW.heavy_due(st, "reap_dead", now=late, start=0.0) is True                # starved twice: runs now
