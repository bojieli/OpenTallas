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
