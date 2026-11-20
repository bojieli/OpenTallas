"""retap.py / sink_bins_from_place.py apply (QC-PLAN-R3 11-20): new sink bins re-derive density taps; forwarded clock
outputs and reset consumer taps that name the old taps are re-pointed in the same step (N46V0 bind EMIT class)."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retap  # noqa: E402
import sink_bins_from_place as SB  # noqa: E402

OLD = [("clk", 100.0, 100.0), ("clk_t1", 500.0, 100.0), ("clk_t2", 900.0, 100.0), ("clk_t3", 900.0, 900.0)]
# re-derived: one tap fewer, renumbered; the old clk_t3 site is now clk_t2, old clk_t2 site lies near new clk_t1
NEW = [("clk", 110.0, 100.0), ("clk_t1", 880.0, 120.0), ("clk_t2", 900.0, 905.0)]


def typ():
    return dict(clock=dict(tap_mode="density", sink_bins_file="old.json", landing_contract=dict(pins=[
        dict(name="fclk_out_a", dir="out", kind="clock", source_clock_port="clk_t3", source_clock_tap="clk_t3"),
        dict(name="fclk_out_b", dir="out", kind="clock", source_clock_port="clk_t2", source_clock_tap="clk_t2"),
        dict(name="fclk_out_c", dir="out", kind="clock", source_clock_port="clk"),
        dict(name="fclk_in_x", dir="in", kind="clock")])),
        reset=dict(consumer_localization=[
            dict(instance="u_bout_a", pin="rst_n", old_reset="rst_n", new_reset="rst_n_t3", clock_net="clk"),
            dict(instance="u_bin_b", pin="rst_n", old_reset="rst_n", new_reset="rst_n_t1", clock_net="clk"),
            dict(instance="u_bin_c", pin="rst_n", old_reset="rst_n", new_reset="rst_n_t0", clock_net="clk")]))


def pins(t):
    return {q["name"]: (q.get("source_clock_port"), q.get("source_clock_tap")) for q in t["clock"]["landing_contract"]["pins"]}


def test_forwarded_outputs_follow_the_nearest_new_tap():
    t = typ()
    ch = retap.repoint_type(t, OLD, NEW)
    assert pins(t)["fclk_out_a"] == ("clk_t2", "clk_t2")      # old clk_t3 (900,900) -> new clk_t2 (900,905)
    assert pins(t)["fclk_out_b"] == ("clk_t1", "clk_t1")      # old clk_t2 (900,100) -> new clk_t1 (880,120)
    assert pins(t)["fclk_out_c"] == ("clk", None)             # clk stays clk
    assert ["landing_contract.fclk_out_a", "source_clock_port", "clk_t3", "clk_t2", 5.0] in ch
    new_names = {n for n, _, _ in NEW}
    assert all(v in new_names for p in pins(t).values() for v in p if v)


def test_reset_consumer_taps_follow_the_same_map():
    t = typ()
    retap.repoint_type(t, OLD, NEW)
    r = {c["instance"]: c["new_reset"] for c in t["reset"]["consumer_localization"]}
    assert r == {"u_bout_a": "rst_n_t2", "u_bin_b": "rst_n_t0", "u_bin_c": "rst_n_t0"}   # old t1 (500,100) -> clk


def test_unchanged_taps_leave_the_type_identical():
    t = typ(); before = copy.deepcopy(t)
    assert retap.repoint_type(t, OLD, list(OLD)) == []
    assert t == before


def test_unknown_reset_tap_fails_closed():
    t = typ(); t["reset"]["consumer_localization"][0]["new_reset"] = "rst_n_t9"
    with pytest.raises(retap.RetapError):
        retap.repoint_type(t, OLD, NEW)


def test_apply_sets_bins_and_repoints_in_one_step():
    raw = dict(partition_types=dict(T=typ(), U=typ()))
    taps = lambda r, _p: (lambda tn: NEW if r["partition_types"][tn]["clock"]["sink_bins_file"] == "placed.json" else OLD)  # noqa: E731
    rep = SB.apply_bins(raw, {"T": "placed.json"}, None, taps_fn=taps)
    assert raw["partition_types"]["T"]["clock"]["sink_bins_file"] == "placed.json"
    assert set(rep) == {"T"}
    assert pins(raw["partition_types"]["T"])["fclk_out_a"] == ("clk_t2", "clk_t2")
    assert raw["partition_types"]["U"] == typ()                # untouched type keeps old bins and refs


def test_retap_cli_round_trip(tmp_path, monkeypatch):
    old = dict(partition_types=dict(T=typ())); new = copy.deepcopy(old)
    new["partition_types"]["T"]["clock"]["sink_bins_file"] = "placed.json"
    (tmp_path / "o.json").write_text(json.dumps(old)); (tmp_path / "n.json").write_text(json.dumps(new))
    monkeypatch.setattr(retap, "_plan_taps", lambda r, _p: (lambda tn: NEW if r["partition_types"][tn]["clock"]["sink_bins_file"] == "placed.json" else OLD))
    assert retap.main([str(tmp_path / "o.json"), str(tmp_path / "n.json"), str(tmp_path / "out.json"), "--report", str(tmp_path / "r.json")]) == 0
    out = json.loads((tmp_path / "out.json").read_text())
    assert pins(out["partition_types"]["T"])["fclk_out_b"] == ("clk_t1", "clk_t1")
    assert set(json.loads((tmp_path / "r.json").read_text())) == {"T"}


# ---- reset tree re-solve (COORD 11-20): N46V0/V0C bind 'control reset localization sle_sc_v2/v3: rst_n_t0:
# emitted/published reset edge mismatch'.  The bind emits the relays of the tree it re-solves on the NEW taps; the plan
# kept the collector_tree published on the OLD taps, so reset_consumers.localize saw relay d != published d.
from reset_consumers import ResetConsumerError, localize  # noqa: E402

# tree on the OLD taps: tap 0's terminal relay hangs on a0; tap 2 on b0
OLD_TREE = {"relays": [dict(name=n, q=q, d=d, depth=dp, xy=[0, 0]) for n, q, d, dp in [
    ("a", "a0", "rst_root_n", 1), ("a1", "rst_n_t0", "a0", 2), ("b", "b0", "rst_root_n", 1), ("b1", "rst_n_t2", "b0", 2)]]}
# the same type re-solved on the NEW taps: tap 0 moved to the b branch, tap 2 to the a branch
NEW_TREE = {"relays": [dict(name=n, q=q, d=d, depth=dp, xy=[0, 0]) for n, q, d, dp in [
    ("a", "a0", "rst_root_n", 1), ("a1", "rst_n_t2", "a0", 2), ("b", "b0", "rst_root_n", 1), ("b1", "rst_n_t0", "b0", 2)]]}


def emitted(tree):
    """the bind's RTL for a tree (root relay + relays) with one localized consumer u_bin_c on rst_n"""
    rel = "\n".join(f"ot_dp_rrelay {r['name']} (.clk(clk), .d({r['d']}), .q({r['q']}));" for r in tree["relays"])
    return ("module fx(input wire clk, arst_n, input wire [7:0] d, input wire ea);\n"
            "wire rst_root_n, a0, b0, rst_n_t0, rst_n_t2;\nwire rst_n = rst_n_t0;\n"
            "ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));\n" + rel + "\n"
            "ot_dp_st #(.W(8)) u_bin_c (.clk(clk), .rst_n(rst_n), .d(d), .ea(ea), .q(q), .eq(eq));\nendmodule\n")


def sc_type():
    t = typ()
    t["clock"]["landing_contract"]["collector_tree"] = copy.deepcopy(OLD_TREE)
    t["reset"]["consumer_localization"] = [dict(instance="u_bin_c", pin="rst_n", old_reset="rst_n", new_reset="rst_n_t0",
                                                clock_net="clk")]
    return t


def _fns():
    taps = lambda r, _p: (lambda tn: NEW if r["partition_types"][tn]["clock"]["sink_bins_file"] == "placed.json" else OLD)  # noqa: E731
    tree = lambda r, _p: (lambda tn: copy.deepcopy(NEW_TREE if r["partition_types"][tn]["clock"]["sink_bins_file"] == "placed.json" else OLD_TREE))  # noqa: E731
    return taps, tree


def test_stale_published_tree_reproduces_the_sc_rst_n_t0_mismatch():
    t = sc_type()
    t["clock"]["sink_bins_file"] = "placed.json"          # bins changed, tree NOT re-solved (V0C)
    with pytest.raises(ResetConsumerError, match="rst_n_t0: emitted/published reset edge mismatch"):
        localize(emitted(NEW_TREE), t["reset"]["consumer_localization"], t["clock"]["landing_contract"]["collector_tree"])


def test_apply_resolves_and_republishes_the_reset_tree_in_the_same_step():
    raw = dict(partition_types=dict(T=sc_type()))
    taps, tree = _fns()
    rep = SB.apply_bins(raw, {"T": "placed.json"}, None, taps_fn=taps, tree_fn=tree)
    t = raw["partition_types"]["T"]
    assert t["clock"]["landing_contract"]["collector_tree"] == NEW_TREE
    assert any(c[0] == "landing_contract.collector_tree" for c in rep["T"])
    # rst_n_t0 (old clk at 100,100) -> new clk; the republished tree is the one the bind emits: localize passes
    assert t["reset"]["consumer_localization"][0]["new_reset"] == "rst_n_t0"
    txt, rs = localize(emitted(NEW_TREE), t["reset"]["consumer_localization"], t["clock"]["landing_contract"]["collector_tree"])
    assert ".rst_n(rst_n_t0)" in txt and rs[0]["depth"] == 2


def test_unchanged_taps_keep_the_published_tree():
    raw = dict(partition_types=dict(T=sc_type())); before = copy.deepcopy(raw)
    taps, tree = _fns()
    assert retap.repoint(copy.deepcopy(raw), raw, taps_fn=taps, tree_fn=tree) == {}
    assert raw == before


def test_hard_tree_is_never_republished():
    raw = dict(partition_types=dict(T=sc_type()))
    raw["partition_types"]["T"]["clock"]["landing_contract"]["collector_tree"]["hard"] = True
    taps, tree = _fns()
    SB.apply_bins(raw, {"T": "placed.json"}, None, taps_fn=taps, tree_fn=tree)
    assert raw["partition_types"]["T"]["clock"]["landing_contract"]["collector_tree"]["relays"] == OLD_TREE["relays"]


def test_foreign_or_stale_published_tree_is_reported_not_overwritten():
    raw = dict(partition_types=dict(T=sc_type()))
    foreign = dict(entry="sync", core_resets=[], relays=[])           # e.g. the cb landing collector form
    raw["partition_types"]["T"]["clock"]["landing_contract"]["collector_tree"] = foreign
    taps, tree = _fns()
    rep = SB.apply_bins(raw, {"T": "placed.json"}, None, taps_fn=taps, tree_fn=tree)
    assert raw["partition_types"]["T"]["clock"]["landing_contract"]["collector_tree"] == foreign
    assert ["landing_contract.collector_tree", "tree_not_own", 0, 0, 0] in rep["T"]


def test_start_transport_raw_resets_follow_the_tap_map():
    """N46V0F bind: 'writer START raw reset rr_t99 has no registered wavefront driver' (slw_sc_v1): the START stages
    name the raw reset of tap i, which moves with the taps."""
    t = typ()
    t["clock"]["landing_writer_start"] = {"depth": 2, "branches": {"x_ctl_o": {"stages": [
        {"xy_um": [900, 900], "raw_reset": "rr_t3"}, {"xy_um": [900, 100], "raw_reset": "rr_t2"}]}}}
    t["clock"]["landing_reader_start"] = {"branches": {"x_i": {"stages": [{"xy_um": [100, 100], "raw_reset": "rr_t0"}]}}}
    t["clock"]["landing_local_resets"] = [{"name": "start_0", "raw": "rst_rl_7", "consumers": ["u_a"]}]
    ch = retap.repoint_type(t, OLD, NEW)
    st = t["clock"]["landing_writer_start"]["branches"]["x_ctl_o"]["stages"]
    assert [s["raw_reset"] for s in st] == ["rr_t2", "rr_t1"]          # old t3 -> new t2, old t2 -> new t1
    assert t["clock"]["landing_reader_start"]["branches"]["x_i"]["stages"][0]["raw_reset"] == "rr_t0"
    assert t["clock"]["landing_local_resets"][0]["raw"] == "rst_rl_7"   # relay names: reset_anchor at bind
    assert ["landing_writer_start", "raw_reset", "rr_t3", "rr_t2", 5.0] in ch
