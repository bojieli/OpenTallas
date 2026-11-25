"""NOPROG-TNS0-1124: a repair whose TNS is >= 0 (|TNS| row 0) is converged, never NO-PROGRESS, however long its log is silent."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import noprog_watchdog as W  # noqa: E402

H = 3600.0

# the tail of a real pregrt_ff_hold.log (epyc7 sle_st_b_v1__pv0e7b1dcc, 11-24): pass all 2, then a third repair_timing whose
# iteration-0 row is already clean, and the step then writes nothing for > 2 h while repair_timing works
LOG = """OT_HOLD_SDC repair_timing sha 4b6bcfb18750d2e7 io_golden 14246 session_missing 2587 reapplied_lines 30
[INFO RSZ-0046] Found 3 endpoints with hold violations.
Iteration | Resized | Buffers | Cloned Gates |   Area   |   WNS   |   TNS   | Endpoint
--------------------------------------------------------------------------------------
        0 |       0 |       0 |            0 |    +0.0% |  -3.991 |  -7.256 | u_a/D
    final |       0 |       3 |            0 |    +0.0% |   5.000 |   0.000 | u_b/D
--------------------------------------------------------------------------------------
[INFO RSZ-0032] Inserted 3 hold buffers.
[INFO RSZ-0506] Runtime: 7.42s
OT_PREGRT_FF_HOLD pass all 2 margin 5.0 wns 5.00004206704446 endpoints 0 insts 532713
OT_HOLD_SDC repair_timing sha 4b6bcfb18750d2e7 io_golden 14246 session_missing 2587 reapplied_lines 30
[INFO RSZ-0046] Found 68980 endpoints with hold violations.
Iteration | Resized | Buffers | Cloned Gates |   Area   |   WNS   |   TNS   | Endpoint
--------------------------------------------------------------------------------------
        0 |       0 |       0 |            0 |    +0.0% |   5.000 |   0.000 | u_b/D
"""


def res(series, growth_idx, n, name="repair_TNS"):
    return {"name": name, "series": series, "growth_idx": growth_idx, "n": n}


def test_real_pregrt_log_tns0_silent_is_progress():
    r = W.extract("other", LOG)
    assert r["name"] == "repair_TNS" and r["series"][-1][1] == 0, r
    now = 1_000_000.0
    anchors = [(now - 12 * H, 0), (now - 9 * H, r["n"])]          # the last line was written 9 h ago
    sw, z0 = W.step_window("/k/gen/x/pregrt_ff_hold.log")
    for exact in (True, False):
        v, why, detail = W.judge(r, anchors, now, window=sw, exact=exact, zero_needs_growth=z0)
        assert v == "PROGRESS", (why, detail)
        assert "converged" in why


def test_tns0_single_row_before_window_is_progress():
    # the exact shape of the 11-24 actions: "repair_TNS best 0 last 0 rows 1 | before-window best 0, window best -"
    now = 1_000_000.0
    anchors = [(now - 12 * H, 0), (now - 11 * H, 10)]
    for z0 in (True, False):
        assert W.judge(res([(5, 0.0)], 9, 10), anchors, now, window=2 * H, exact=True, zero_needs_growth=z0)[0] == "PROGRESS"
    # any TNS metric: GRT hold chunks too
    assert W.judge(res([(5, 3.0), (8, 0.0)], 9, 10, "grt_hold_TNS"), anchors, now, window=6 * H, exact=True)[0] == "PROGRESS"


def test_nonzero_flat_tns_still_no_progress():
    now = 1_000_000.0
    anchors = [(now - 5 * H, 0), (now - 2.5 * H, 10)]
    v, _, _ = W.judge(res([(2, 188478.0)], 9, 10), anchors, now, window=2 * H, exact=True, zero_needs_growth=True)
    assert v == "NO-PROGRESS"
    # TNS that fell to 0 earlier but is negative again (last row non-zero): judged as before
    v, _, _ = W.judge(res([(2, 0.0), (9, 495634.0)], 9, 10), anchors, now, window=2 * H, exact=True, zero_needs_growth=True)
    assert v == "NO-PROGRESS"


def test_tns_converged_helper():
    assert W.tns_converged(res([(1, 0.0)], 1, 2))
    assert not W.tns_converged(res([(1, 4.0)], 1, 2))
    assert not W.tns_converged(res([], 1, 2))
    assert not W.tns_converged(res([(1, 0.0)], 1, 2, "drt_violations"))      # 0 DRT violations is judged by the DRT rules
