"""GRT-LABEL-NOTICE-1122 (COORD flow review item 3): a GRT-LABEL DESIGN-FAIL job whose overflow is flat or rising >= 3 h gets ONE notice to its owner."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noprog_watchdog as nw  # noqa: E402


def row(ov, **kw):
    r = {"host": "epyc10", "unit": "oth-x-1", "container": "dpkit-t15-1", "type": "ot_s81sl_leaf__t15", "verdict": nw.GRT_LABEL, "kind": "grt",
         "why": "DESIGN-FAIL: GRT-0273 (clock NDR dropped under congestion)", "grt_ovf": ov, "age_h": 5.0, "gb": 20, "lane": "LEAF-R10", "kit": "/x/k"}
    r.update(kw)
    return r


def test_notice_after_3h_flat_once():
    seen, t0 = {}, 1_000_000.0
    assert nw.grt_label_notice_pass([row(6617)], seen, t0, post=False) == []
    assert nw.grt_label_notice_pass([row(6600)], seen, t0 + 2 * 3600, post=False) == []
    out = nw.grt_label_notice_pass([row(6700)], seen, t0 + 3 * 3600 + 1, post=False)
    assert len(out) == 1 and out[0][0] == "LEAF-R10" and "6617 -> 6700" in out[0][1]
    assert nw.grt_label_notice_pass([row(6700)], seen, t0 + 4 * 3600, post=False) == []     # once


def test_falling_overflow_restarts_clock_and_others_skipped():
    seen, t0 = {}, 1_000_000.0
    nw.grt_label_notice_pass([row(10000)], seen, t0, post=False)
    assert nw.grt_label_notice_pass([row(9000)], seen, t0 + 3 * 3600 + 1, post=False) == []   # fell 10 %: clock restarts
    assert len(nw.grt_label_notice_pass([row(9000)], seen, t0 + 6 * 3600 + 2, post=False)) == 1
    s2 = {}
    for r in (row(5, verdict="KEEP"), row(5, why="GRT overflow trend"), row(None)):
        nw.grt_label_notice_pass([r], s2, t0, post=False)
        assert nw.grt_label_notice_pass([r], s2, t0 + 4 * 3600, post=False) == []
    # a wave attempt is left to grt_flat_pass (it cancels through the wave)
    w = row(5, lane="", kit="/r/kit-wave/s81/E1/items/t15/attempt_2", age_h=5.0)
    nw.grt_label_notice_pass([w], s2, t0, post=False)
    assert nw.grt_label_notice_pass([w], s2, t0 + 4 * 3600, post=False) == []
