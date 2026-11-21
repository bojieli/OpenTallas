"""CBC-RULES-1119 r713 rule 4: bank reset relays (bank_reset_delta.py + reset_port_relays bank_taps / depth 16)."""
import copy
import json

import pytest

import bank_reset_delta as B
import reset_port_relays as R
import schema as S

HARD = """module h (
    input  wire clk,
    input  wire arst_n,
    input  wire [3:0] a, input wire [3:0] c,
    output wire [3:0] b
);
    wire rst_n = arst_n;  // delivered reset to the native hard partition
    ot_dp_st #(.W(3)) u_bin_a (.clk(clk), .rst_n(rst_n), .d(a[2:0]), .ea(a[3]), .q(a_q), .eq(a_eq));
    ot_dp_st #(.W(3)) u_bin_c (.clk(clk), .rst_n(rst_n), .d(c[2:0]), .ea(c[3]), .q(c_q), .eq(c_eq));
    ot_dp_st #(.W(3)) u_bout_b (.clk(clk), .rst_n(rst_n), .d(a_q), .ea(rst_n), .q(b[2:0]), .eq(b[3]));
    phy_core u_core (.clk(clk), .rst_n(rst_n));
endmodule
"""


def hard_t():
    return dict(hard=True, outline_um=[4000.0, 400.0], reset=dict(sync_stages=2, tap_um=[2000.0, 400.0]),
                buses=[dict(name="a", dir="in", face="N", width=3, window_um=[0.0, 40.0]),
                       dict(name="c", dir="in", face="N", width=3, window_um=[3960.0, 4000.0]),
                       dict(name="b", dir="out", face="N", width=3, window_um=[40.0, 80.0])])


SOFT = """module s (input wire clk, input wire arst_n, input wire [3:0] a, output wire [3:0] b);
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_n_t0));  // pad tap 0 depth 2 @ (10.0, 10.0)
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_root_n), .q(rst_n_t1));  // pad tap 1 depth 2 @ (990.0, 10.0)
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_root_n), .q(rst_n_t2));  // pad tap 2 depth 2 @ (500.0, 10.0)
    wire rst_n = rst_n_t2;
    ot_dp_st #(.W(3)) u_bin_a (.clk(clk), .rst_n(rst_n), .d(a[2:0]), .ea(a[3]), .q(a_q), .eq(a_eq));
    ot_dp_st #(.W(3)) u_bout_b (.clk(clk), .rst_n(rst_n), .d(a_q), .ea(rst_n), .q(b[2:0]), .eq(b[3]));
    ot_dp_st #(.W(3)) u_ft_f_o_0 (.clk(clk), .rst_n(rst_n), .d(a_q), .ea(a_eq), .q(f0), .eq(f0e));
endmodule
"""


def soft_t():
    return dict(outline_um=[1000.0, 200.0], reset=dict(sync_stages=2),
                buses=[dict(name="a", dir="in", face="S", width=3, window_um=[0.0, 40.0]),
                       dict(name="b", dir="out", face="S", width=3, window_um=[960.0, 1000.0])],
                ft_slots=[dict(name="f", stations=1, in_face="W", in_window_um=[50.0, 60.0], out_face="E",
                               out_window_um=[50.0, 60.0], width=3)])


def test_hard_equal_depth_chains_and_wavefront_depth():
    t = hard_t()
    r = B.type_delta("h", t, HARD)
    # a + b at the W end (span 40 um) and c at the E end; tap at x=2000 -> ~2000 um -> D = ceil(2000/405) = 5 for both
    assert [x["sinks"] for x in r["rows"]] == [["u_bin_a", "u_bout_b"], ["u_bin_c"]]
    assert {x["depth"] for x in r["rows"]} == {5} and r["added_reset_cycles"] == 5 and r["flops"] == 10
    assert t["reset"]["depth"] == 1 + 5 and t["reset"]["port_relays"] == r["rows"]
    assert all(d["hop_um"] <= 405 and d["leaf_span_um"] <= 405 for d in r["detail"])
    assert len(t["relay_sites"]) == 10 and t["relay_sites"]["u_prl_cbr0_4.q"] == r["detail"][0]["centroid"]
    out, rec = R.apply(HARD, t["reset"]["port_relays"])
    assert "u_bin_a (.clk(clk), .rst_n(prl_cbr0_4)," in out and "u_bin_c (.clk(clk), .rst_n(prl_cbr1_4)," in out
    assert ".ea(rst_n)" in out and "u_core (.clk(clk), .rst_n(rst_n))" in out    # epoch source and the core keep rst_n
    assert [x["reset"] for x in rec] == ["prl_cbr0_4", "prl_cbr1_4"]


def test_hard_leaf_max_splits_groups():
    r = B.type_delta("h", hard_t(), HARD, leaf_max=1)
    assert [x["sinks"] for x in r["rows"]] == [["u_bin_a"], ["u_bout_b"], ["u_bin_c"]]


def test_hard_too_deep_fails_closed():
    with pytest.raises(B.DeltaError, match="depth"):
        B.type_delta("h", hard_t(), HARD, reach=100.0)


def test_soft_nearest_equal_depth_tap_zero_cycles():
    t = soft_t()
    r = B.type_delta("s", t, SOFT)
    assert r["form"] == "bank_taps" and r["added_reset_cycles"] == 0 and r["flops"] == 0
    assert t["reset"]["bank_taps"] == [dict(tap=0, sinks=["u_bin_a"]), dict(tap=1, sinks=["u_bout_b"]),
                                       dict(tap=2, sinks=["u_ft_f_o_0"])]
    out, rec = R.apply_bank_taps(SOFT, t["reset"]["bank_taps"])
    assert "u_bin_a (.clk(clk), .rst_n(rst_n_t0)," in out and "u_bout_b (.clk(clk), .rst_n(rst_n_t1)," in out
    assert "u_ft_f_o_0 (.clk(clk), .rst_n(rst_n)," in out            # already on the leaf tap: untouched
    assert "u_bout_b (.clk(clk), .rst_n(rst_n_t1), .d(a_q), .ea(rst_n)" in out
    assert r["hop_max_um"] < r["was_hop_max_um"]


def test_soft_leaf_max_moves_to_next_tap():
    t = soft_t()
    B.type_delta("s", t, SOFT, leaf_max=1)
    assert sorted(x["tap"] for x in t["reset"]["bank_taps"]) == [0, 1, 2]


def test_soft_far_bank_fails_closed():
    with pytest.raises(B.DeltaError, match="local_taps_um"):
        B.type_delta("s", soft_t(), SOFT, reach=30.0)


def test_no_bank_on_rst_is_byte_as_plan():
    sv = SOFT.replace(".rst_n(rst_n)", ".rst_n(other)")
    t = soft_t()
    before = copy.deepcopy(t)
    assert B.type_delta("s", t, sv)["rows"] == [] and t == before


@pytest.mark.parametrize("rows,msg", [
    ([dict(tap=7, sinks=["u_bin_a"])], "not declared"),
    ([dict(tap=0, sinks=["u_nope"])], "not an emitted"),
    ([dict(tap=0, sinks=["u_bin_a"]), dict(tap=1, sinks=["u_bin_a"])], "duplicate sink"),
    ([dict(tap=0, sinks=["u_bin_a"], x=1)], "exactly tap, sinks"),
])
def test_bank_taps_fail_closed(rows, msg):
    with pytest.raises(R.PortRelayError, match=msg):
        R.apply_bank_taps(SOFT, rows)


def test_bank_taps_need_tree_leaf():
    with pytest.raises(R.PortRelayError, match="leaf alias"):
        R.apply_bank_taps(HARD, [dict(tap=0, sinks=["u_bin_a"])])


def test_port_relays_depth_16_and_ste_sink():
    sv = HARD.replace("ot_dp_st #(.W(3)) u_bin_c", "ot_dp_ste #(.W(3)) u_bin_c")
    out, _ = R.apply(sv, [dict(name="g", depth=16, sinks=["u_bin_c"])])
    assert "u_bin_c (.clk(clk), .rst_n(prl_g_15)," in out
    with pytest.raises(R.PortRelayError, match="1..16"):
        R.apply(sv, [dict(name="g", depth=17, sinks=["u_bin_c"])])


def test_schema_accepts_rows():
    import jsonschema
    rp = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["reset"]
    jsonschema.validate(dict(bank_taps=[dict(tap=3, sinks=["u_bin_a"])], port_relays=[dict(name="g", depth=12, sinks=["u_bin_a"])],
                             depth=13), rp)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dict(bank_taps=[dict(tap=3, sinks=[])]), rp)


def test_bind_applies_bank_taps_after_port_relays():
    import pathlib
    src = (pathlib.Path(__file__).with_name("bind.py")).read_text()
    assert src.index("reset_port_relays.apply(f.read_text(), port_relays)") < src.index(
        "reset_port_relays.apply_bank_taps(f.read_text(), bank_taps)")


def test_cli_byte_preserving(tmp_path):
    plan = dict(partition_types=dict(s=soft_t(), h=hard_t()), other=dict(k=[1, 2]))
    p = tmp_path / "p.json"
    p.write_text(json.dumps(plan, indent=1) + "\n")
    d = tmp_path / "rtl"
    d.mkdir()
    (d / "x_s.sv").write_text(SOFT)
    (d / "h.sv").write_text(HARD)
    out, rep = tmp_path / "o.json", tmp_path / "r.json"
    assert B.main([str(p), str(d), str(out), str(rep), "--types", "s,h"]) == 0
    o = json.loads(out.read_text())
    assert o["other"] == plan["other"] and o["partition_types"]["h"]["reset"]["depth"] == 6
    assert json.loads(rep.read_text())["s"]["form"] == "bank_taps"


def test_ft_slot_without_windows_is_unplaced():
    t = soft_t()
    del t["ft_slots"][0]["in_window_um"]
    r = B.type_delta("s", t, SOFT)
    assert r["unplaced"] == ["u_ft_f_o_0"] and all("u_ft_f_o_0" not in x["sinks"] for x in r["rows"])


def test_bus_without_face_window_is_unplaced():
    t = soft_t()
    del t["buses"][0]["face"]
    r = B.type_delta("s", t, SOFT)
    assert "u_bin_a" in r["unplaced"]


def test_u_bin_nearest_tap_from_landing_ring_boxes():
    """FABLE-PD-KV-1840: a KV bus sited per port (no face window) was `unplaced` and kept the leaf tap ~1,400 um away; its
    position is the centre of its landing-ring box in the kit landing_placement.tcl: nearest tap, 0 cycles"""
    tcl = "set cland_groups {\n  {u_cland_a {10.0 10.0 30.0 30.0} ring:a}\n  {u_cland_c {960.0 20.0 980.0 40.0} ring:c@1.4+ff}\n}\n"
    pos = B.landing_positions(tcl)
    assert pos == {"u_bin_a": (20.0, 20.0), "u_bin_c": (970.0, 30.0)}
    t = dict(outline_um=[1000.0, 1000.0], reset=dict(sync_stages=2),
             buses=[dict(name="a", dir="in", width=3), dict(name="c", dir="in", width=3), dict(name="b", dir="out", width=3)])
    sv = SOFT.replace("    ot_dp_st #(.W(3)) u_bout_b", "    ot_dp_st #(.W(3)) u_bin_c (.clk(clk), .rst_n(rst_n), .d(a[2:0]), .ea(a[3]), .q(c_q), .eq(c_eq));\n"
                      "    ot_dp_st #(.W(3)) u_bout_b")
    rep = B.type_delta("s", t, sv, pos, reach=405.0)
    assert rep["form"] == "bank_taps" and rep["added_reset_cycles"] == 0
    got = {x["inst"]: x for x in rep["detail"]}
    assert got["u_bin_a"]["tap"] == 0 and got["u_bin_c"]["tap"] == 1
    assert got["u_bin_c"]["hop_um"] < got["u_bin_c"]["was_hop_um"]
    assert "u_bout_b" in rep["unplaced"]


def test_pin_centroid_places_u_bout_and_hierarchical_u_bin():
    """RESET-RELAY-GEN-R3 11-21: u_bout banks (no landing ring) and hierarchical pv u_bin buses were `unplaced`; the centroid of
    the bus's kit pins.json pins is their position (--pins), landing rings keep priority"""
    pins = [dict(bus="b", bit=0, x=960.0, y=30.0), dict(bus="b", bit=1, x=980.0, y=30.0), dict(bus="z", bit=0, x=1.0, y=1.0)]
    pos = B.pin_positions(pins)
    assert pos["u_bout_b"] == (970.0, 30.0) == pos["u_bin_b"] and pos["u_bout_z"] == (1.0, 1.0)
    t = dict(outline_um=[1000.0, 1000.0], reset=dict(sync_stages=2),
             buses=[dict(name="a", dir="in", width=3), dict(name="b", dir="out", width=3)])
    rep = B.type_delta("s", t, SOFT, {"u_bin_a": (20.0, 20.0), **pos}, reach=405.0)
    assert "u_bout_b" not in (rep.get("unplaced") or [])
    got = {x["inst"]: x for x in rep["detail"]}
    assert got["u_bout_b"]["tap"] == 1 and got["u_bout_b"]["hop_um"] < got["u_bout_b"]["was_hop_um"]


def test_far_bank_gets_local_tap_terminal_not_a_long_hop():
    """RESET-RELAY-GEN-R3 11-21 (COORD): KV pv v3/v3n 397 um, v7 355 um nearest-tap hops; with --local-taps (reach 300) a bank with no
    tap within reach gets a reset.local_taps_um site (cluster centroid), 0 cycles, and stays out of bank_taps until the second pass"""
    t = dict(outline_um=[1000.0, 1000.0], reset=dict(sync_stages=2),
             buses=[dict(name="a", dir="in", width=3), dict(name="b", dir="out", width=3)])
    pos = {"u_bin_a": (20.0, 20.0), "u_bout_b": (500.0, 900.0)}
    with pytest.raises(B.DeltaError):
        B.type_delta("s", copy.deepcopy(t), SOFT, pos, reach=300.0)
    tt = copy.deepcopy(t)
    rep = B.type_delta("s", tt, SOFT, pos, reach=300.0, local_taps=True)
    assert rep["added_reset_cycles"] == 0 and rep["local_taps"] == [dict(xy=[500.0, 900.0], banks=["u_bout_b"])]
    assert tt["reset"]["local_taps_um"] == [[500.0, 900.0]]
    assert all("u_bout_b" not in r["sinks"] for r in rep["rows"]) and all(d["hop_um"] <= 300.0 for d in rep["detail"])
