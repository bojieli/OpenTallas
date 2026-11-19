"""PAD-REACH census (FABLE-FIX-KV-PV class D 11-19): bound RTL + plan geometry -> pad need per in bus."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pad_reach_census as C  # noqa: E402

SV = """module t_part_bound (input wire clk);
    ot_dp_st #(.W(4)) u_bin_c_i (.clk(clk), .rst_n(rst_n), .d(cland_c_i[3:0]), .ea(cland_c_i[4]), .q(c_i_q), .eq(c_i_eq));
    ot_dp_dly #(.W(1), .D(2)) u_pd2_c_i_0_t_3 (.clk(clk), .d(c_i_q[0]), .q(pd2_c_i_0_t_3));  // landing pad trunk: shared stages of pad 3 (tail split)
    ot_dp_dly_keep #(.W(1), .D(1)) u_pd1_c_i_0_a_3 (.clk(clk), .d(pd2_c_i_0_t_3[0]), .q(pd1_c_i_0_a_3));  // landing pad tail copy for core a: as-built relative timing
    ot_dp_dly_keep #(.W(1), .D(1)) u_pd1_c_i_0_b_3 (.clk(clk), .d(pd2_c_i_0_t_3[0]), .q(pd1_c_i_0_b_3));  // landing pad tail copy for core b: as-built relative timing
    ot_dp_dly #(.W(1), .D(1)) u_pd1_c_i_3 (.clk(clk), .d(c_i_q[3]), .q(pd1_c_i_3));  // landing pad: as-built relative timing
    ot_dp_dly #(.W(5), .D(2)) u_lpad_e_i (.clk(clk), .d({e_i_eb, e_i_b}), .q({e_i_eq, e_i_q}));  // lane pad: latency table 9 cycles
    core u_a (
        .clk(clk_c0),
        .x({c_i_q[2:1], pd1_c_i_0_a_3[0]}),
        .y(w_other[0])
    );
    core u_b (
        .clk(clk_c1),
        .x({pd1_c_i_3[0], c_i_q[1], pd1_c_i_0_b_3[0]}),
        .y(e_i_q[2])
    );
endmodule
"""


def _pins(x):
    return [dict(name=f"x[{i}]", layer="M4", xy=[x, 10.0 + i]) for i in range(3)] + [dict(name="y", layer="M4", xy=[x, 30.0])]


def _plan():
    hc = lambda inst, x: dict(inst=inst, module="core", origin_um=[x, 0.0], outline_um=[20.0, 40.0], pins=_pins(0.0),
                              physical_inst=f"u_bound.u_{inst}")
    return dict(partition_types=dict(t=dict(
        buses=[dict(name="c_i", dir="in", width=4), dict(name="e_i", dir="in", width=4), dict(name="o", dir="out", width=1)],
        hard_cores=[hc("a", 1000.0), hc("b", 2000.0)],
        clock=dict(landing_contract=dict(bands=dict(c_i=dict(rect_um=[0.0, 0.0, 20.0, 20.0])))))))


def test_bits_and_parse():
    assert C.bits_of("{a_q[2:1], p[0]}") == [("a_q", 2), ("a_q", 1), ("p", 0)]
    assert C.bits_of("w") == [("w", None)] and C.bits_of("{3{x}}") is None and C.bits_of("~(r)") is None
    dly, lpad, conns = C.parse(SV, {"u_a": "a", "u_b": "b"})
    assert lpad == {"e_i": 2} and dly["pd1_c_i_0_a_3"] == (1, "pd2_c_i_0_t_3[0]") and dly["pd1_c_i_3"] == (1, "c_i_q[3]")
    assert conns["u_b"]["x"] == [("pd1_c_i_3", 0), ("c_i_q", 1), ("pd1_c_i_0_b_3", 0)]
    assert C.resolve("pd1_c_i_0_a_3", 0, dly, {"c_i"}) == ("c_i", 0, 3) and C.resolve("w_other", 0, dly, {"c_i"}) is None


def test_census_need_short_and_lift():
    cfg = dict(hop_um=300.0, min_spread_um=400.0, route=True)
    r = C.census(_plan(), "t", SV, cfg)
    c = r["buses"]["c_i"]
    # bit 0 pad 3: cores a + b 1,000 um apart -> tail 2; band centre (10, 10) -> T (1500, 10) = 1,490 um -> trunk 5: need 7
    # bit 1 pad 0 on both cores: need 7 as well; bit 2 pad 0 (a only): shared, ceil(993 / 300) - 1 = 3; bit 3 pad 1 (b only): 6
    assert c["pads"] == 4 and c["split"] == 2 and c["cores"] == 2 and c["need"] == 7 and c["short"] == 7 and c["min_pad"] == 0
    assert r["max_short"] == 7 and r["max_hop_um"] > 1500
    e = r["buses"]["e_i"]                       # lane pad 2 counts as pad; no source point -> nothing priced
    assert e["lane_pad"] == 2 and e["min_pad"] == 2 and e["need"] == 0 and e["short"] == 0
    up = C.census(_plan(), "t", SV, cfg, lifts=[("^c_i$", 7)])
    assert up["max_short"] == 0 and up["buses"]["c_i"]["min_pad"] == 7 and up["max_hop_um"] <= 300.0
    assert C.census(_plan(), "t", SV, cfg, bus_re="^e_")["buses"].keys() == {"e_i"}
