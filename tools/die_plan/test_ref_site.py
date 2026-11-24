"""pytest: REF-SITE resolves name / index references to xy (QC sle_sc_v3 seam index crossing the tap count)."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_site as RS  # noqa: E402


def _grid(n, far=None):
    g = [("clk", 0.0, 0.0)] + [(f"clk_t{i}", 10.0 * i, 0.0) for i in range(1, n)]
    if far is not None:
        g[far] = (g[far][0], 1184.0, 0.0)
    return g


def _plan(node="rst_n_t4"):
    return {"partition_types": {"A": {"clock": {"landing_contract": {
        "collector_children": [{"name": "c0", "node": node, "status_pins_xy_um": [[5.0, 0.0], [6.0, 0.0]]}],
        "collector_tree": {"relays": [{"q": "rst_n_t1", "xy": [0, 0], "d": "rst_root_n"}]}},
        "landing_raw_branches": [{"name": "b", "stages": [{"original": "rst_n_t1", "xy_um": [3000.0, 0.0]}]}]}}}}


def _with_grid(monkeypatch, n, far=None):
    monkeypatch.setitem(sys.modules, "schema", types.SimpleNamespace(tap_grid=lambda P, tn: _grid(n, far)))


def test_index_refs_skip_collector_tree_and_label_by_name():
    refs = RS.index_refs(_plan()["partition_types"]["A"])
    paths = sorted(p for p, *_ in refs)
    assert paths == [".clock.landing_contract.collector_children[c0].node", ".clock.landing_raw_branches[b].stages[0].original"]


def test_seam_index_then_tap_after_tap_count_grows(monkeypatch):
    raw = _plan()
    _with_grid(monkeypatch, 4)                       # 4 taps: index 4 = seam output 0 (unsited)
    old, n0 = RS.type_refs(None, raw, "A")
    k = ".clock.landing_contract.collector_children[c0].node"
    assert n0 == 4 and old[k][0] == "seam"
    _with_grid(monkeypatch, 6, far=4)                # 6 taps: index 4 is now clock tap 4, 1184 um away
    new, n1 = RS.type_refs(None, raw, "A")
    assert new[k][0] == "reset" and new[k][2] == (1184.0, 0.0)
    rr = RS.reach_rows(new, 405.0)
    assert [r[0] for r in rr] == [k] and rr[0][2] > 1100       # transport stage (3000 um, by design) is not a REACH row
    mv, kind = RS.moved_rows(new, old)
    assert kind and kind[0][0] == k and kind[0][3] == "reset" and kind[0][4] > 1100


def test_moved_site_and_same_site(monkeypatch):
    raw = _plan("rst_n_t2")
    _with_grid(monkeypatch, 4)
    a, _ = RS.type_refs(None, raw, "A")
    _with_grid(monkeypatch, 4, far=2)
    b, _ = RS.type_refs(None, raw, "A")
    mv, kind = RS.moved_rows(b, a)
    assert [m[0] for m in mv] == [".clock.landing_contract.collector_children[c0].node"] and not kind
    assert RS.moved_rows(a, a) == ([], [])


def test_adv_ref_site_never_raises():
    import adv_ref_site as A
    assert A.findings(None, "p")[0].startswith("WARN ADV-REF-SITE")
