"""pytest: ADV-STALE-KEEPOUT on the KV pv_v2ne / pv_v5ne pattern (keepouts = old band geometry) and the pv_v6n bins undercount."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_stale_keepout as A  # noqa: E402

BANDS = {"ft0_i": [100.0, 100.0, 140.0, 300.0], "ft1_i": [500.0, 100.0, 540.0, 300.0]}


def test_all_displaced_pv_v2ne_pattern():
    ko = [[128.08, 100.0, 168.08, 300.0], [528.89, 100.0, 568.89, 300.0]]       # same size, moved ~28 um
    r = A.judge_keepouts(ko, BANDS)
    assert r["all_displaced"] and r["exact"] == 0


def test_current_copies_pass():
    ko = [list(BANDS["ft0_i"]), list(BANDS["ft1_i"])]
    r = A.judge_keepouts(ko, BANDS)
    assert r["exact"] == 2 and not r["all_displaced"] and not r["moved"] and not r["stale"]


def test_moved_overlap_flagged_and_baseline_stale():
    ko = [list(BANDS["ft0_i"]), [110.0, 100.0, 150.0, 300.0], [900.0, 900.0, 910.0, 910.0]]
    r = A.judge_keepouts(ko, BANDS)
    assert len(r["moved"]) == 1 and r["moved"][0][1] == "ft0_i"
    base = {"ft1_i": [900.0, 900.0, 910.0, 910.0]}          # the keepout is the OLD ft1_i rect, which then moved to [500,...]
    assert A.judge_keepouts(ko, BANDS, base)["stale"] == [([900.0, 900.0, 910.0, 910.0], "ft1_i")]


def test_bins_threshold():
    assert A.judge_bins(50235, 100445) > 0.4          # pv_v6n
    assert A.judge_bins(100000, 105000) is None       # within 10 %
    assert A.judge_bins(0, 5) is None and A.judge_bins(5, 0) is None


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-STALE-KEEPOUT not checked")
