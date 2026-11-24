"""pytest: ADV-COLSYNC on the QC su_c case (plan rst_n_t88 vs sidecar rst_n_t84; node not in tree; row 1237 um away)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_colsync as A  # noqa: E402


def lc(node, xy=(1217.76, 524.85)):
    return {"collector_root_node": "rst_root_n",
            "collector_tree": {"relays": [{"q": "rst_n_t84", "xy": [1200.0, 520.0]}, {"q": "rst_n_t40", "xy": [100.0, 100.0]}]},
            "collector_children": [{"index": 0, "node": node, "xy_um": list(xy)}], "collector_local_sources": []}


SIDE = {"children": [{"index": 0, "node": "rst_n_t84"}], "local_sources": [], "collector_root_node": "rst_root_n"}


def test_stale_index_flagged_three_ways():
    nd, nm, nf, nr, worst, sample = A.judge_type(lc("rst_n_t88"), SIDE)
    assert nd == 1 and nm == 1 and "rst_n_t88" in sample


def test_far_row_flagged():
    nd, nm, nf, nr, worst, _ = A.judge_type(lc("rst_n_t40"), {"children": [{"index": 0, "node": "rst_n_t40"}], "collector_root_node": "rst_root_n"})
    assert (nd, nm, nf) == (0, 0, 1) and worst > 1000


def test_synced_row_passes():
    assert A.judge_type(lc("rst_n_t84"), SIDE)[:3] == (0, 0, 0)


def test_no_sidecar_is_not_run_and_never_raises():
    assert "NOT-RUN" in A.findings({"partition_types": {}}, "p", None)[0]
    assert A.findings(None, "p", None, sidecar="x")[0].startswith("WARN ADV-COLSYNC not checked")
