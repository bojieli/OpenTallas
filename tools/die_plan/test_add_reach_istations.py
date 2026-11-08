"""DIE-HBM-91-REACH 11-08: add_reach_istations.py puts FIRM internal stations (every hop <= 405 um) on long type buses
that have none, raises the lane fixed_cycles by the same count (PIN CYCLES = source + destination stations), names
the out-bus types for asbuilt internal_stations_types, and skips (lists) the buses one chain cannot serve."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_reach_istations as A  # noqa: E402

RTL = """module hbm_arch_q_t (input wire clk, input wire [64:0] L5_i, input wire [8:0] L6_i, input wire [8:0] L8_i,
    output wire [8:0] L9_o);
    wire [63:0] L5_i_q;
    ot_dp_st #(.W(64)) u_bin_L5_i (.clk(clk), .rst_n(rst_n), .d(L5_i[63:0]), .ea(L5_i[64]), .q(L5_i_q), .eq(L5_i_eq));
    ot_dp_st #(.W(8)) u_bin_L6_i (.clk(clk), .rst_n(rst_n), .d(L6_i[7:0]), .ea(L6_i[8]), .q(L6_i_q), .eq(L6_i_eq));
    ot_dp_st #(.W(8)) u_bin_L8_i (.clk(clk), .rst_n(rst_n), .d(L8_i[7:0]), .ea(L8_i[8]), .q(L8_i_q), .eq(L8_i_eq));
    ot_dp_st #(.W(8)) u_bout_L9_o (.clk(clk), .rst_n(rst_n), .d({w_u_far__y[7:0]}), .ea(e), .q(L9_o[7:0]), .eq(L9_o[8]));
    ot_far u_far (
        .a(L5_i_q[63:0]),
        .y(w_u_far__y)
    );
    ot_near u_near (
        .a(L6_i_q[7:0])
    );
    ot_w u_w (
        .a(L8_i_q[3:0])
    );
    ot_e u_e (
        .a(L8_i_q[7:4])
    );
endmodule
"""


def plan(fixed=0):
    core = lambda n, x, y: dict(inst=n, module="m_" + n, origin_um=[x, y], outline_um=[40.0, 40.0])
    t = dict(module="hbm_arch_q_t", outline_um=[2000.0, 1200.0],
             buses=[dict(name="L5_i", dir="in", width=64, kind="data", face="N", window_um=[90.0, 110.0]),
                    dict(name="L6_i", dir="in", width=8, kind="data", face="N", window_um=[150.0, 160.0]),
                    dict(name="L8_i", dir="in", width=8, kind="data", face="S", window_um=[990.0, 1010.0]),
                    dict(name="L9_o", dir="out", width=8, kind="data", face="N", window_um=[200.0, 210.0])],
             hard_cores=[core("far", 1600.0, 100.0), core("near", 150.0, 1000.0), core("w", 10.0, 600.0),
                         core("e", 1940.0, 600.0)])
    src = dict(module="hbm_arch_q_s", outline_um=[100.0, 100.0], buses=[])
    lanes = [dict(id=f"L{k}", ports=[f"L{k}_0"]) for k in (5, 6, 8, 9)]
    lanes[0]["fixed_cycles"] = fixed
    ports = [dict(id=f"L{k}_0", src=dict(part="NE_s", bus=f"L{k}_o"), dst=dict(part="NE_t", bus=f"L{k}_i"))
             for k in (5, 6, 8)]
    ports.append(dict(id="L9_0", src=dict(part="NE_t", bus="L9_o"), dst=dict(part="NE_s", bus="L9_i")))
    return dict(partition_types=dict(q_t=t, q_s=src), partitions=[dict(name="NE_t", type="q_t"), dict(name="NE_s", type="q_s")],
                lanes=lanes, ports=ports, latency=dict(lanes={}), note="base")


def run(tmp_path, monkeypatch, raw):
    (tmp_path / "hbm_arch_q_t.sv").write_text(RTL)
    monkeypatch.setattr(A, "lat_delta", lambda a, b: {})
    return A.apply(raw, tmp_path, ["q_t"])


def hops(e, leaf=None):
    pts = [e["from_um"]] + e["regs_um"] + [leaf or e["to_um"]]
    return [A.man(a, b) for a, b in zip(pts, pts[1:])]


def test_long_in_and_out_buses_get_one_chain_with_every_hop_within_reach(tmp_path, monkeypatch):
    raw, led = run(tmp_path, monkeypatch, plan())
    ist = {e["conn"]: e for e in raw["partition_types"]["q_t"]["internal_stations"]}
    assert set(ist) == {"bus:L5_i", "bus:L9_o"}
    for e in ist.values():
        assert e["regs_um"] and max(hops(e)) <= 405.0 + 1e-6
        assert e["launch"] == "face bus " + e["conn"][4:] and e["capture"] == "far"
    assert led["native_types"] == ["q_t"]


def test_short_bus_is_untouched_and_branch_bus_is_listed_not_stationed(tmp_path, monkeypatch):
    raw, led = run(tmp_path, monkeypatch, plan())
    rows = {r["bus"]: r for r in led["rows"]}
    assert "L6_i" not in rows                                  # 0 .. 405 um: no station
    assert rows["L8_i"]["verdict"] == "SKIP" and rows["L8_i"]["reason"].startswith("branch")
    assert led["skipped"] == {"branch": 1}


def test_pin_cycles_equal_the_added_stations_on_each_lane(tmp_path, monkeypatch):
    raw, led = run(tmp_path, monkeypatch, plan())
    ist = {e["conn"]: e for e in raw["partition_types"]["q_t"]["internal_stations"]}
    fx = {L["id"]: L.get("fixed_cycles", 0) for L in raw["lanes"]}
    assert fx["L5"] == len(ist["bus:L5_i"]["regs_um"]) and fx["L9"] == len(ist["bus:L9_o"]["regs_um"])
    assert fx["L6"] == 0 and fx["L8"] == 0
    assert led["lanes_fixed_cycles"] == {"L5": fx["L5"], "L9": fx["L9"]}


def test_lane_with_existing_fixed_cycles_is_skipped(tmp_path, monkeypatch):
    raw, led = run(tmp_path, monkeypatch, plan(fixed=3))
    rows = {r["bus"]: r for r in led["rows"]}
    assert rows["L5_i"]["verdict"] == "SKIP" and rows["L5_i"]["reason"].startswith("fixed")
    assert next(L for L in raw["lanes"] if L["id"] == "L5")["fixed_cycles"] == 3


def test_out_bus_skipped_when_the_receiver_already_has_stations(tmp_path, monkeypatch):
    p = plan()
    p["partition_types"]["q_s"]["internal_stations"] = [dict(conn="bus:L9_i", from_um=[0, 0], to_um=[1, 1], regs_um=[[0.5, 0.5]])]
    raw, led = run(tmp_path, monkeypatch, p)
    rows = {r["bus"]: r for r in led["rows"]}
    assert rows["L9_o"]["reason"].startswith("out_receiver") and led["native_types"] == []


def test_cli_writes_plan_and_ledger(tmp_path, monkeypatch):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "hbm_arch_q_t.sv").write_text(RTL)
    (tmp_path / "p.json").write_text(json.dumps(plan()))
    monkeypatch.setattr(A, "lat_delta", lambda a, b: {})
    assert A.main([str(tmp_path / "p.json"), str(tmp_path / "o.json"), str(tmp_path / "l.json"),
                   "--bound-rtl", str(tmp_path / "rtl"), "--types", "q_t"]) == 0
    o = json.loads((tmp_path / "o.json").read_text())
    assert o["note"].startswith("DIE-HBM-91-REACH istareach_1108")
    assert json.loads((tmp_path / "l.json").read_text())["added_entries"] == 2


def test_target_deep_in_abutted_cores_gets_the_nearest_free_point_not_a_recursion_error():
    import hub_repack as HR
    rects = [HR._core_rect(dict(origin_um=[300.0 + 100.0 * i, 300.0 + 100.0 * j], outline_um=[100.0, 100.0]))
             for i in range(5) for j in range(5)]
    R = HR.Raster(1200.0, 1200.0, rects)
    q = A.free_near(HR, R, (550.0, 550.0))
    assert q is not None and R.free(*q) and R.core_at(q, 0) is None
