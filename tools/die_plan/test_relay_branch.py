"""S81-RLYBR-1 11-19: relay branch copies (bind post-pass), station chain joins (kit_istations), generator rows."""
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import kit_istations as KI
import relay_branch as RB
import schema

TEXT = """module t (
    input wire clk
);
    wire [7:0] w_u_r0_u_t2_xa;
    wire [7:0] w_u_r0_u_y_xa_3_0_o;
    wire [7:0] lp_q;
    wire [7:0] w_9_Y;
    // as-built a.u_t2
    core_t u_u_r0_u_t2 (
        .ck(clk),
        .xa(w_u_r0_u_t2_xa)
    );
    // as-built a.u_y_xa_3_0
    ot_s81_rly_k #(.ID(0), .RSREG(1), .W(8)) u_u_r0_u_y_xa_3_0 (
        .ck(clk),
        .i(w_u_r0_u_t2_xa[7:0]),
        .o(w_u_r0_u_y_xa_3_0_o),
        .rs(rs_a)
    );
    // as-built a.u_bs3
    core_b u_u_r0_u_bs3 (
        .ck(clk),
        .i_x0(w_u_r0_u_y_xa_3_0_o[7:0])
    );
    ot_dp_dly #(.W(8), .D(1)) u_y_xd_u_r0_u_t3_xai_0_0 (.clk(clk), .d(w_u_r0_u_y_xa_3_0_o[7:0]), .q(lp_q));  // relay_depth: stage 1/1
    assign w_9_Y = lp_q;
    // as-built a.u_t3
    core_c u_u_r0_u_t3 (
        .ck(clk), .xai(w_9_Y[7:0]),
        .cc(w_u_r0_u_t3_cc));
endmodule
"""


def test_apply_copies_relay_and_repoints_branch_through_stages():
    out, rep = RB.apply(TEXT, [{"inst": "u_r0_u_y_xa_3_0", "copies": [{"name": "u_r0_u_y_xa_3_t3_0", "sinks": ["u_r0_u_t3"]}]}])
    assert rep == [dict(relay="u_u_r0_u_y_xa_3_0", copy="u_u_r0_u_y_xa_3_t3_0", sinks=["u_u_r0_u_t3"], readers=1, D=0)]
    assert re.search(r"ot_s81_rly_k #\(\.ID\(1\), \.RSREG\(1\), \.W\(8\)\) u_u_r0_u_y_xa_3_t3_0 \(", out)   # fresh ID, same form
    assert "wire [7:0] w_u_r0_u_y_xa_3_t3_0_o;" in out
    assert ".d(w_u_r0_u_y_xa_3_t3_0_o[7:0])" in out                     # the relay_depth stage in front of t3 follows the copy
    assert ".i_x0(w_u_r0_u_y_xa_3_0_o[7:0])" in out                     # bs3 stays on the original
    assert re.search(r"u_u_r0_u_y_xa_3_t3_0 \(\n\s+\.ck\(clk\),\n\s+\.i\(w_u_r0_u_t2_xa\[7:0\]\),\n\s+\.o\(w_u_r0_u_y_xa_3_t3_0_o\)", out)
    assert RB.copies_distinct(out, rep) == [("u_u_r0_u_y_xa_3_0", "u_u_r0_u_y_xa_3_t3_0")]   # same reset: would merge
    out2 = out.replace(".rs(rs_a)\n    );\n    // as-built a.u_bs3", ".rs(rs_a)\n    );\n    // as-built a.u_bs3", 1)
    out2 = re.sub(r"(u_u_r0_u_y_xa_3_t3_0 \((?:.|\n)*?\.rs\()rs_a", r"\1rs_b", out2)
    assert RB.copies_distinct(out2, rep) == []


def test_apply_absent_and_stale_rows():
    assert RB.apply(TEXT, []) == (TEXT, [])
    with pytest.raises(RB.BranchError, match="not in the bound module"):
        RB.apply(TEXT, [{"inst": "u_r0_u_y_zz_0", "copies": [{"name": "x", "sinks": ["u_r0_u_t3"]}]}])
    assert RB.apply(TEXT, [{"inst": "u_r0_u_y_zz_0", "optional": True, "copies": [{"name": "x", "sinks": ["a"]}]}])[1] == []
    with pytest.raises(RB.BranchError, match="not fed by the relay"):
        RB.apply(TEXT, [{"inst": "u_r0_u_y_xa_3_0", "copies": [{"name": "u_r0_u_y_xa_3_s9_0", "sinks": ["u_r0_u_s9"]}]}])
    with pytest.raises(RB.BranchError, match="already used"):
        RB.apply(TEXT, [{"inst": "u_r0_u_y_xa_3_0", "copies": [{"name": "u_r0_u_bs3", "sinks": ["u_r0_u_t3"]}]}])


def _hc(inst, x, y, pins):
    return {"inst": inst, "module": "m", "origin_um": [x, y], "outline_um": [20.0, 20.0], "orient": "R0",
            "pins": [{"name": p, "layer": "M4", "xy": [10.0, 10.0]} for p in pins]}


def plan_geo(t3_xy=(800.0, 800.0)):
    return {"partition_types": {"t": {"outline_um": [2000.0, 2000.0], "hard_cores": [
        _hc("u_r0.u_t2", 500.0, 500.0, ["xa"]), _hc("u_r0.u_bs3", 100.0, 500.0, ["i_x0"]),
        _hc("u_r0.u_t3", t3_xy[0], t3_xy[1], ["xai", "cc"])]}}}


def test_branch_rows_split_far_sinks_zero_cycles():
    rows, drows, rep = RB.branch_rows(plan_geo(), "t", TEXT)
    assert drows == []
    assert len(rows) == 1 and rows[0]["inst"] == "u_r0_u_y_xa_3_0"
    (c,) = rows[0]["copies"]
    assert c["D"] == 0 and c["sinks"] in (["u_r0_u_t3"], ["u_r0_u_bs3"])
    assert c["name"] in ("u_r0_u_y_xa_3_t3_0", "u_r0_u_y_xa_3_bs3_0")
    # the rows apply cleanly to the same module
    RB.apply(TEXT, rows)


def test_branch_rows_fit_one_box_no_row_and_far_branch_cycles():
    near = plan_geo((560.0, 560.0))
    near["partition_types"]["t"]["hard_cores"][1]["origin_um"] = [440.0, 500.0]
    assert RB.branch_rows(near, "t", TEXT)[0] == []
    far = plan_geo((1100.0, 1100.0))
    rows, drows, _ = RB.branch_rows(far, "t", TEXT, add_cycles=True)
    c = rows[0]["copies"][0]
    assert c["sinks"] == ["u_r0_u_t3"] and c["D"] == 1                  # 1200 um flight: one declared stage
    assert drows == []                                                  # t3 reads through an assign: reported, no row
    text2 = TEXT.replace(".xai(w_9_Y[7:0])", ".xai(w_u_r0_u_y_xa_3_0_o[7:0])")
    rows, drows, _ = RB.branch_rows(far, "t", text2, add_cycles=True)
    assert drows == [dict(inst="u_r0_u_t3", port="xai", side="sink", D=1, path_um=1200.0,
                          note="S81-RLYBR-1: far branch of u_r0_u_y_xa_3_0 via copy u_r0_u_y_xa_3_t3_0")]


def test_cluster_box_rule():
    s = {"a": (0.0, 0.0), "b": (100.0, 0.0), "c": (1500.0, 0.0)}
    assert RB.cluster((50.0, 0.0), s) == [["a", "b"], ["c"]]
    assert RB.cluster((700.0, 0.0), {"a": (0.0, 0.0), "c": (1400.0, 0.0)}) == [["a"], ["c"]]   # each fits with the source alone
    assert RB.cluster((700.0, 0.0), {"a": (300.0, 0.0), "c": (1100.0, 0.0)}) == [["a", "c"]]


OUTBUS = """module t (
    input wire clk,
    output wire [8:0] fo
);
    wire [3:0] w_u_bn3_d_st;
    wire [3:0] w_6_Y;
    wire [3:0] w_7_Y;
    // as-built a.u_cf
    core_cf u_u_cf (
        .rs(w_u_cf_rs)
    );
    // as-built a.u_bn3
    core_bn u_u_bn3 (
        .d_st(w_u_bn3_d_st)
    );
    assign w_6_Y = w_u_cf_rs[3:0];
    assign w_7_Y = w_u_bn3_d_st[3:0];
    ot_dp_st #(.W(8)) u_bout_fo (.clk(clk), .rst_n(rst_n), .d({w_7_Y[3:0], w_6_Y[3:0]}), .ea(rst_n), .q(fo[7:0]), .eq(fo[8]));
endmodule
"""


def test_join_rows_far_slice_nearest_station():
    p = {"partition_types": {"t": {"outline_um": [2000.0, 2000.0],
        "buses": [{"name": "fo", "width": 8, "dir": "out", "face": "W"}],
        "hard_cores": [_hc("u_cf", 1400.0, 500.0, ["rs"]), _hc("u_bn3", 300.0, 1250.0, ["d_st"])],
        "internal_stations": [{"conn": "bus:fo", "launch": "u_cf.rs", "capture": "face flop", "from_um": [1410.0, 510.0],
                               "regs_um": [[1410.0, 860.0], [1410.0, 1200.0], [1170.0, 1290.0], [830.0, 1290.0], [480.0, 1290.0]],
                               "to_um": [140.0, 1296.0]}]}}}
    joins, rep = RB.join_rows(p, "t", OUTBUS)
    assert joins == {"bus:fo": [dict(bits=[4, 7], stage=4, src="u_u_bn3.d_st", src_um=[310.0, 1260.0],
                                     stage0_um=1500.0, stage_um=200.0)]}


def test_join_stations_keeps_stage_count():
    decl, body, cq, ceq, names = KI.join_stations("fo", 8, "{a[3:0], b[3:0]}", "rst_n", 5, [{"bits": [4, 7], "stage": 4}])
    txt = "\n".join(body)
    assert names == [f"u_ist_fo_{j}" for j in range(5)] and cq == "fo_is4_q"
    assert "assign fo_jd = {a[3:0], b[3:0]};" in txt
    assert re.search(r"u_ist_fo_0 \(.*\.d\(\{4'b0, fo_jd\[3:0\]\}\)", txt)            # the far slice is not wired to station 0
    assert len(re.findall(r"u_isj_fo_0_\d ", txt)) == 4                                 # 4 local flops ...
    assert re.search(r"u_ist_fo_4 \(.*\.d\(\{fo_j0_s3_q, fo_is3_q\[3:0\]\}\)", txt)    # ... then station 4: 5 registers per bit
    assert re.search(r"u_ist_fo_1 \(.*\.d\(fo_is0_q\)", txt)
    with pytest.raises(SystemExit, match="bad join"):
        KI.join_stations("fo", 8, "x", "rst_n", 5, [{"bits": [4, 9], "stage": 4}])
    with pytest.raises(SystemExit, match="bad join"):
        KI.join_stations("fo", 8, "x", "rst_n", 5, [{"bits": [4, 7], "stage": 5}])


def test_schema_keys():
    import jsonschema
    pt = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    jsonschema.validate([{"inst": "u_r0_u_y_xa_3_0", "copies": [{"name": "u_r0_u_y_xa_3_t3_0", "sinks": ["u_r0_u_t3"], "D": 0}]}],
                        pt["relay_branch"])
    jsonschema.validate([{"bits": [1155, 1156], "stage": 4, "src": "u_u_r0_u_bn3.d_st"}],
                        pt["internal_stations"]["items"]["properties"]["join"])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate([{"bits": [1, 2], "stage": 0}], pt["internal_stations"]["items"]["properties"]["join"])


def test_bind_hook_refuses_mergeable_copy():
    from test_relay_depth import vehicle
    b, part = vehicle([])
    t = b.plan["partition_types"]["src"]
    t.pop("relay_depth", None)
    b.F.cells.append(SimpleNamespace(path="x.u_sink2", ports={"i": [1, 2, 3], "ck": [9]}, module="core_sink", params={}))
    b.G.dirs[2] = {"i": "input", "ck": "input"}
    b.G.kind.append("leaf")
    b.members[part] = [0, 1, 2]
    b.sinks.update({(2, "i", k): ("int", 0, "o", k, 0) for k in range(3)})
    b.sinks[(2, "ck", 0)] = ("clk", "core")
    b.rel_of = lambda ci: ("u_y_rt_1", "u_sink", "u_sink2")[ci]
    text, _ = b.emit_type("src", part)
    t["relay_branch"] = [{"inst": "u_y_rt_1", "copies": [{"name": "u_y_rt_sink2_1", "sinks": ["u_sink2"]}]}]
    with pytest.raises(bind.BindError, match="relay_branch src: copy inputs identical"):
        b.emit_type("src", part)


INBUS = """module t (
    input wire clk
);
    wire [7:0] fi_q;
    wire fi_eq;
    wire [5:0] w_1_Y;
    wire [1:0] w_2_Y;
    ot_dp_dly #(.W(9), .D(3)) u_lpad_fi (.clk(clk), .d({fi_eb, fi_b}), .q({fi_eq, fi_q}));  // lane pad
    assign w_1_Y = fi_q[5:0];
    assign w_2_Y = fi_q[7:6];
    // as-built a.u_t3
    core_t u_u_t3 (
        .xai(w_1_Y[5:0])
    );
    // as-built a.u_bn5
    core_b u_u_bn5 (
        .rs(w_2_Y[1:0])
    );
endmodule
"""


def test_trunk_rows_reaim_majority_minority_keeps_old_sites():
    old = [[600.0, 0.0], [1000.0, 0.0], [1300.0, 300.0]]
    p = {"partition_types": {"t": {"outline_um": [1500.0, 1500.0],
        "buses": [{"name": "fi", "width": 8, "dir": "in", "face": "S"}],
        "hard_cores": [_hc("u_t3", 600.0, 40.0, ["xai"]), _hc("u_bn5", 1300.0, 700.0, ["rs"])],
        "internal_stations": [{"conn": "bus:fi", "launch": "face bus fi", "capture": "u_t3.xai", "from_um": [100.0, 0.0],
                               "regs_um": old, "to_um": [1310.0, 710.0]}]}}}
    rows, rep = RB.trunk_rows(p, "t", INBUS)
    r = rows["bus:fi"]
    assert r["to_um"] == [610.0, 50.0] and r["majority_bits"] == 6 and r["minority"] == [[6, 7]]
    assert len(r["regs_um"]) == 3 and r["new_last_um"] <= 405 and r["old_last_um"] > 405
    assert r["relay_sites"] == {**{f"u_lpad_fi.r[{j}][{b}]": old[j] for j in (0, 1) for b in (6, 7)},
                                **{f"u_lpad_fi.q[{b}]": old[2] for b in (6, 7)}}
    for x, y in r["regs_um"]:                                                    # no station inside a hard core
        assert not (595 < x < 625 and 35 < y < 65)
    p["partition_types"]["t"]["internal_stations"][0]["regs_um"] = [[300.0, 0.0], [450.0, 0.0], [560.0, 0.0]]
    assert RB.trunk_rows(p, "t", INBUS)[0] == {}                                 # already aimed at the majority


def test_branch_rows_routed_length_makes_a_branch_far():
    """bs0 class: flight fits one box, the route round a macro wall does not -> the far sink gets its copy + 1 stage"""
    p = plan_geo((560.0, 560.0))
    t = p["partition_types"]["t"]
    t["hard_cores"][1]["origin_um"] = [300.0, 480.0]                       # bs3 pin (310, 490): 220 um flight from t2
    t["hard_cores"][1]["pins"] = [{"name": "i_x0", "layer": "M4", "xy": [10.0, 0.0]}]     # pins on the core edge
    t["hard_cores"][0]["pins"] = [{"name": "xa", "layer": "M4", "xy": [10.0, 0.0]}]
    t["hard_cores"][2]["pins"] = [{"name": p_, "layer": "M4", "xy": [10.0, 0.0]} for p_ in ("xai", "cc")]
    t["hard_cores"].append({"inst": "u_wall", "module": "w", "origin_um": [400.0, 0.0], "outline_um": [20.0, 1300.0]})
    rows, _d, _r = RB.branch_rows(p, "t", TEXT, add_cycles=True)
    assert rows and rows[0]["copies"][0]["sinks"] == ["u_r0_u_bs3"] and rows[0]["copies"][0]["D"] >= 1
    rows, _d, rep = RB.branch_rows(p, "t", TEXT)                         # default: copy kept at D 0, need reported
    assert rows[0]["copies"][0]["D"] == 0 and any(r.get("need_D", 0) >= 1 for r in rep)


# CBC-RULES-1119: generic transport relays (QC / KV / HEAD bind-emitted ot_dp_dly one-liners)
DLY = """module q (
    input wire clk
);
    wire [3:0] w_a_x;
    wire [3:0] s0_q;
    wire [3:0] s1_q;
    core_a u_a (
        .ck(clk),
        .x(w_a_x)
    );
    ot_dp_dly #(.W(4), .D(1)) u_tp_x_0 (.clk(clk), .d(w_a_x), .q(s0_q));
    ot_dp_dly #(.W(4), .D(2)) u_tp_x_1 (.clk(clk), .d(s0_q), .q(s1_q));
    core_b u_b (
        .ck(clk),
        .xi(s1_q[3:0])
    );
    core_c u_c (
        .ck(clk),
        .xi(s1_q[3:0])
    );
endmodule
"""


def test_transport_relay_copy_is_kept_dly_and_never_merge_flagged():
    out, rep = RB.apply(DLY, [{"inst": "tp_x_1", "copies": [{"name": "tp_x_c_1", "sinks": ["c"]}]}])
    assert "ot_dp_dly_keep #(.W(4), .D(2)) u_tp_x_c_1 (.clk(clk), .d(s0_q), .q(w_tp_x_c_1_q));" in out
    assert "wire [3:0] w_tp_x_c_1_q;" in out
    assert re.search(r"u_c \(\n\s+\.ck\(clk\),\n\s+\.xi\(w_tp_x_c_1_q\[3:0\]\)", out)
    assert re.search(r"u_b \(\n\s+\.ck\(clk\),\n\s+\.xi\(s1_q\[3:0\]\)", out)
    assert rep[0]["kept"] is True and RB.copies_distinct(out, rep) == []


def test_transport_chain_only_last_stage_is_a_candidate():
    N = RB.Netlist(DLY)
    assert RB.relay_ports(N.st[N.by_inst["u_tp_x_0"]]) == ("d", "q")
    plan = {"partition_types": {"q": {"outline_um": [2000, 200], "hard_cores": [
        dict(inst="a", module="core_a", origin_um=[0, 0], outline_um=[10, 10]),
        dict(inst="b", module="core_b", origin_um=[100, 0], outline_um=[10, 10]),
        dict(inst="c", module="core_c", origin_um=[1900, 0], outline_um=[10, 10])]}}}
    rows, drows, rep = RB.branch_rows(plan, "q", DLY, None, 405.0)
    assert [r["inst"] for r in rows] == ["tp_x_1"]          # stage 0 feeds stage 1, so only stage 1 splits
    assert rows[0]["copies"][0]["sinks"] == ["c"]


def test_branch_rows_default_keeps_stage_count():
    # FABLE-PD-S81-0253 11-19: the far-branch sink stages raised col_h10_r0_p1 internal depth 3 -> 13 with no K delta
    far = plan_geo((1100.0, 1100.0))
    text2 = TEXT.replace(".xai(w_9_Y[7:0])", ".xai(w_u_r0_u_y_xa_3_0_o[7:0])")
    rows, drows, rep = RB.branch_rows(far, "t", text2)
    assert drows == [] and all(c["D"] == 0 for r in rows for c in r["copies"])
    assert [r["need_D"] for r in rep if "need_D" in r] == [1]


# CBC-RULES-1119 hierarchical pin view (QC: hard cores inside soft wrappers)
HIER = """module q (
    input wire clk
);
    wire [3:0] s1_q;
    wire [3:0] w_a_x;
    // as-built c16_E0_0.u_t_0_0
    qfd_tile u_u_t_0_0 (
        .ck(clk),
        .x(w_a_x)
    );
    ot_dp_dly #(.W(4), .D(1)) u_pd_x (.clk(clk), .d(w_a_x), .q(s1_q));
    // as-built dvs_W0.u_core.u_sub.u_r4
    qfd_station u_u_r4 (
        .ck(clk),
        .xi(s1_q[3:0])
    );
    // as-built dvs_W0.u_core.u_sub.u_r7
    qfd_station u_u_r7 (
        .ck(clk),
        .xi(s1_q[3:0])
    );
endmodule
"""


def test_hier_pin_view_nested_and_alias():
    hc = [dict(inst="u_t00", module="qfd_tile_a", origin_um=[0, 0], outline_um=[100, 100]),
          dict(inst="u_bound.u_u_r4.u_h9.u_m.g_bank[0].u_m", module="sram", origin_um=[1000, 0], outline_um=[20, 20]),
          dict(inst="u_bound.u_u_r4.u_hb.u_m.g_bank[0].u_m", module="sram", origin_um=[1040, 0], outline_um=[20, 20]),
          dict(inst="u_bound.u_u_r7.u_h9.u_m.g_bank[0].u_m", module="sram", origin_um=[1900, 1500], outline_um=[20, 20])]
    plan = {"partition_types": {"q": {"outline_um": [2000, 2000], "hard_cores": hc}}}
    G = RB.Geometry(plan, "q", RB.Netlist(HIER))
    assert G.pin("u_u_t_0_0", "x") == (50.0, 50.0)                    # alias by the as-built tail u_t_0_0 = u_t00
    assert G.pin("u_u_r4", "xi") == (1030.0, 10.0)                    # centroid of the two cores inside u_u_r4
    assert G.pin("u_u_r7", "xi") == (1910.0, 1510.0)
    assert G.pin("u_pd_x", "d") is None
    rows, drows, rep = RB.branch_rows(plan, "q", HIER, None, 405.0)
    assert [r["inst"] for r in rows] == ["pd_x"] and drows == []
    assert {tuple(c["sinks"]) for c in rows[0]["copies"]} <= {("u_r4",), ("u_r7",)}


def test_gate_named_bus_with_measured_leg_only():
    # COORD 11-19 05:55: no whole-type mode -- a candidate is written only when named and a measured leg supports it
    rows = [dict(inst="r0_u_y_xa_1_0", copies=[dict(name="r0_u_y_xa_1_bs0_0")]), dict(inst="r1_u_z_0", copies=[dict(name="r1_u_z_bs0_0")])]
    trunks = {"bus:frame_i": {"regs_um": []}}
    legs = {"T": [(900.0, "u_bound.u_r0_u_y_xa_1_0.q_reg[3]", "u_bound.u_core.d", "logic"),
                  (700.0, "u_bound.u_lpad_frame_i.r[0][1]", "u_bound.u_c2.d", "channel")]}
    r, j, t, rep = RB.gate("T", set(), legs, rows, {}, trunks)
    assert r == [] and t == {} and all(not g["emitted"] for g in rep)
    r, j, t, rep = RB.gate("T", {("T", "r0_u_y_xa_1_0"), ("T", "r1_u_z_0"), ("T", "frame_i")}, legs, rows, {}, trunks)
    assert [x["inst"] for x in r] == ["r0_u_y_xa_1_0"] and list(t) == ["bus:frame_i"]
    assert any(g["name"] == "r1_u_z_0" and "no measured leg" in g["why"] for g in rep if not g["emitted"])
    assert RB.leg_for(legs["T"], RB._names("r0_u_y_xa_1")) is None          # a prefix of another relay is not it


def test_merge_branch_rows_keeps_earlier_copies():
    """FAM-S81-COL-R4 11-21: a re-run's row for a relay that already has copies adds to them, never replaces them"""
    import relay_branch as RB
    old = [{"inst": "u_y_xa_4_0", "copies": [{"name": "u_y_xa_4_bs6_0", "sinks": ["u_bs6"], "D": 0}], "note": "kept ['u_bs5', 'u_t4']"},
           {"inst": "u_y_xa_9_0", "copies": [{"name": "u_y_xa_9_bs1_0", "sinks": ["u_bs1"], "D": 0}], "note": "x"}]
    new = [{"inst": "u_y_xa_4_0", "copies": [{"name": "u_y_xa_4_bs5_0", "sinks": ["u_bs5"], "D": 0},
                                             {"name": "dup", "sinks": ["u_bs6"], "D": 0}], "note": "kept ['u_t4']"},
           {"inst": "u_y_cc_4_0", "copies": [{"name": "u_y_cc_4_t4_0", "sinks": ["u_t4"], "D": 0}], "note": "y"}]
    out = {r["inst"]: r for r in RB.merge_branch_rows(old, new)}
    assert [c["name"] for c in out["u_y_xa_4_0"]["copies"]] == ["u_y_xa_4_bs6_0", "u_y_xa_4_bs5_0"]
    assert out["u_y_xa_4_0"]["note"] == "kept ['u_t4']"
    assert set(out) == {"u_y_xa_4_0", "u_y_xa_9_0", "u_y_cc_4_0"}
