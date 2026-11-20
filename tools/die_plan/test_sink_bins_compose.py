"""sink_bins_compose.py (QC-PLAN-R3 V1, FABLE-CBC-QK-0130 s7): native bins + the flops plan rows add, at their sites."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sink_bins_compose as SC  # noqa: E402
import sink_bins_from_place as SB  # noqa: E402

B = 10.8


def plan():
    t = dict(module="m", outline_um=[400.0, 400.0], contents=[dict(inst="u_core", origin_um=[300.0, 300.0], outline_um=[20.0, 20.0])],
             buses=[dict(name="a_i", dir="in", width=8, face="W", window_um=[100.0, 120.0], leaf="u_core.a"),
                    dict(name="b_i", dir="in", width=4, face="S", window_um=[50.0, 70.0], leaf="u_core.b"),
                    dict(name="c_o", dir="out", width=2, face="E", window_um=[10.0, 20.0], leaf="u_core.c")],
             internal_stations=[dict(conn="bus:a_i", regs_um=[[100.0, 110.0], [200.0, 110.0]], bits=8)],
             clock=dict(tap_mode="density", sink_bins_file="bins/native_T.json", tap_max_sinks=1000))
    s = dict(module="s", outline_um=[100.0, 100.0], buses=[dict(name="x_o", dir="out", width=8), dict(name="y_o", dir="out", width=4)],
             clock=dict())
    return dict(partition_types=dict(T=t, S=s), budgets={},
                partitions=[dict(name="pT", type="T"), dict(name="pS", type="S")],
                ports=[dict(id="p1", src=dict(part="pS", bus="x_o"), dst=dict(part="pT", bus="a_i")),
                       dict(id="p2", src=dict(part="pS", bus="y_o"), dst=dict(part="pT", bus="b_i"))],
                lanes=[dict(id="l1", ports=["p1"], fixed_cycles=3), dict(id="l2", ports=["p2"], fixed_cycles=2)],
                latency=dict(lanes=dict(l1=dict(cycles=5, stations=0, clock_landing=0, pad=0),
                                        l2=dict(cycles=4, stations=0, clock_landing=0, pad=0))))


NATIVE = dict(bin_um=B, n=7, bins=[[5.4, 5.4, 7]], type="T", placed_kit="k", source="test")


def test_station_row_adds_width_plus_epoch_times_stages_at_its_sites():
    doc, rep = SC.compose_bins(plan(), "T", NATIVE, "bins/native_T.json")
    bins = {(x, y): n for x, y, n in doc["bins"]}
    assert bins[SC.snap(100.0, 110.0, B)] == 9 and bins[SC.snap(200.0, 110.0, B)] == 9     # (8 + 1 epoch) per stage
    assert rep["added"]["station"] == 18
    assert bins[(5.4, 5.4)] == 7                                                         # native kept


def test_lane_pad_adds_only_the_stages_the_stations_do_not_absorb():
    doc, rep = SC.compose_bins(plan(), "T", NATIVE, "bins/native_T.json")
    pads = {r["conn"]: r for r in rep["rows"] if r["cls"] == "pad"}
    # a_i: lane pad D = 5 - 2 = 3, 2 stations absorb 2 -> 1 stage x 9; b_i: D = 2, no station -> 2 x 5
    assert pads["bus:a_i"]["stages_added"] == 1 and pads["bus:a_i"]["flops"] == 9
    assert pads["bus:b_i"]["flops"] == 10
    assert rep["added"]["pad"] == 19
    assert doc["n"] == 7 + 18 + 19 and rep["ratio"] == round(doc["n"] / 7, 4)
    assert any(x["cls"] == "pad" for x in rep["approx"])                                  # pad sites are listed as approximate


def test_source_out_bus_stations_priced_in_fixed_cycles_are_not_padded_again():
    p = plan()
    p["partition_types"]["S"]["internal_stations"] = [dict(conn="bus:y_o", regs_um=[[50.0, 50.0]], bits=4)]
    _, rep = SC.compose_bins(p, "T", NATIVE, "n")
    assert {r["conn"]: r["flops"] for r in rep["rows"] if r["cls"] == "pad"}["bus:b_i"] == 5


def test_exact_bank_counts_one_flop_per_site():
    p = plan()
    p["partition_types"]["T"]["internal_stations"] = [dict(conn="bus:b_i", regs_um=[[60.0, 60.0]], bits=4,
                                                           bit_sites_um=[[[60.0 + i, 60.0] for i in range(5)]], bit_site_cell_um=[1.0, 0.27])]
    doc, rep = SC.compose_bins(p, "T", NATIVE, "n")
    assert rep["added"]["station"] == 5


def test_lockup_latches_on_long_pad_lines_and_landing_rings():
    p = plan()
    p["budgets"]["r_dly_lockup"] = {"T": {"seg": 1}}
    p["partition_types"]["T"]["clock"]["landing_contract"] = dict(bands=dict(a_i=dict(
        rect_um=[0.0, 0.0, 21.6, 10.8], clock_roles=dict(forwarded_write_flops=40, local_read_flops=10))))
    _, rep = SC.compose_bins(p, "T", NATIVE, "n")
    assert rep["added"]["landing"] == 10                       # local read flops only: forwarded writes are on fclk nets
    assert any("forwarded_write_flops" in x["why"] for x in rep["not_counted"])
    # a_i D 3, seg 1 -> 2 boundaries x 9; b_i D 2 -> 1 x 5
    assert rep["added"]["lockup"] == 2 * 9 + 5


def test_compose_twice_does_not_double_count(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bins").mkdir()
    (tmp_path / "bins/native_T.json").write_text(json.dumps(NATIVE))
    (tmp_path / "plan.json").write_text(json.dumps(plan()))
    import taps
    monkeypatch.setattr(taps, "_root", lambda: tmp_path)
    monkeypatch.setattr(SB, "apply_bins", lambda raw, m, path=None, taps_fn=None: [
        raw["partition_types"][tn]["clock"].__setitem__("sink_bins_file", f) for tn, f in m.items()] and {})
    assert SC.main(["plan.json", "p1.json", "--types", "T", "--bins-dir", "cb"]) == 0
    d1 = json.loads((tmp_path / "cb/T__composed.json").read_text())
    assert json.loads((tmp_path / "p1.json").read_text())["partition_types"]["T"]["clock"]["sink_bins_file"] == "cb/T__composed.json"
    assert d1["native_bins_file"] == "bins/native_T.json" and d1["native_n"] == 7
    assert SC.main(["p1.json", "p2.json", "--types", "T", "--bins-dir", "cb"]) == 0         # re-compose from the composed plan
    d2 = json.loads((tmp_path / "cb/T__composed.json").read_text())
    assert d2["bins"] == d1["bins"] and d2["n"] == d1["n"] and d2["native_bins_file"] == "bins/native_T.json"


def test_apply_path_calls_retap_in_the_same_step(tmp_path, monkeypatch):
    import retap
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bins").mkdir()
    (tmp_path / "bins/native_T.json").write_text(json.dumps(NATIVE))
    p = plan()
    p["partition_types"]["T"]["clock"]["landing_contract"] = dict(pins=[
        dict(name="fclk_out_a", dir="out", kind="clock", source_clock_port="clk_t2", source_clock_tap="clk_t2")])
    (tmp_path / "plan.json").write_text(json.dumps(p))
    import taps
    monkeypatch.setattr(taps, "_root", lambda: tmp_path)
    OLD = [("clk", 10.0, 10.0), ("clk_t1", 200.0, 10.0), ("clk_t2", 390.0, 390.0)]
    NEW = [("clk", 10.0, 10.0), ("clk_t1", 380.0, 385.0)]
    calls = []

    def fake(raw, _path):
        calls.append(_path)
        return lambda tn: NEW if raw["partition_types"][tn]["clock"]["sink_bins_file"].endswith("__composed.json") else OLD
    monkeypatch.setattr(retap, "_plan_taps", fake)
    assert SC.main(["plan.json", "out.json", "--types", "T", "--bins-dir", "cb", "--report", "r.json"]) == 0
    out = json.loads((tmp_path / "out.json").read_text())
    pin = out["partition_types"]["T"]["clock"]["landing_contract"]["pins"][0]
    assert pin["source_clock_port"] == "clk_t1" and pin["source_clock_tap"] == "clk_t1"
    rep = json.loads((tmp_path / "r.json").read_text())
    assert set(rep["retap"]) == {"T"} and len(calls) == 2
    assert out["partition_types"]["S"] == p["partition_types"]["S"]


def test_native_only_dump_drops_row_instances(tmp_path):
    t = tmp_path / "s.tsv"
    t.write_text("clk\tu_x.u_ist_a_i_0.q_reg_3_\tDFF\t1.0\t1.0\nclk\tu_lpad_b_i.r_0__1_\tDFF\t1.0\t1.0\n"
                 "clk_t1\tu_core.acc_reg\tDFF\t2.0\t2.0\nclk\tu_bin_a_i_pad0.q\tDFF\t3.0\t3.0\nclk\tu_bin_a_i.q\tDFF\t3.0\t3.0\n")
    assert len(SB.read_tsv(t)) == 5
    assert SB.read_tsv(t, native_only=True) == [(2.0, 2.0), (3.0, 3.0)]
    o = tmp_path / "b.json"
    assert SB.main(["bins", str(t), "--type", "T", "--out", str(o), "--native-only"]) == 0
    assert json.loads(o.read_text())["native_only"] is True


def test_a_wide_rank_spreads_over_its_footprint_and_keeps_its_count():
    p = plan()
    p["partition_types"]["T"]["buses"][0]["width"] = 2000
    doc, rep = SC.compose_bins(p, "T", NATIVE, "n")
    assert rep["added"]["station"] == 2 * 2001 and doc["n"] == 7 + sum(rep["added"].values())
    assert max(n for _, _, n in doc["bins"]) < 2001                                       # no rank in a single bin
