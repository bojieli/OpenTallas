"""RESET-RELAY-GEN-1530: reset_leg_plan.py (form R inst_taps, form L local relay seat + relay_depth) and
reset_port_relays.apply_inst_taps (bind / kit-rtl)."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import geom_rules  # noqa: E402
import kit_relay_depth as KRD  # noqa: E402
import reset_leg_plan as RLP  # noqa: E402
import reset_port_relays as PR  # noqa: E402

BOUND = """module dp_x (
    input  wire clk,
    input  wire arst_n,
    input  wire [3:0] d_i,
    output wire [3:0] q_o
);
    wire pad_rst_q;
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    ot_dp_rgate u_rrl_1 (.clk(clk), .d(rst_rl_0), .run(rn_rst_rl_0), .q(rst_n_t0));  // gated tap tap 0 depth 2 @ (500.0, 500.0)
    ot_dp_rgate u_rrl_2 (.clk(clk), .d(rst_rl_0), .run(rn_rst_rl_0), .q(rst_n_t1));  // gated tap tap 1 depth 2 @ (100.0, 900.0)
    ot_dp_rgate u_rrl_3 (.clk(clk), .d(rst_rl_0), .run(rn_rst_rl_0), .q(rst_n_t2));  // gated tap tap 2 depth 2 @ (900.0, 100.0)
    wire rst_n = rst_n_t0;
    cell_a u_u_fab_u_x_0 (
        .ck(clk),
        .rst_n(rst_n),
        .d(d_i)
    );
    cell_a u_u_fab_u_x_1 (
        .ck(clk),
        .rst_n(rst_n_t2),
        .d(d_i)
    );
    land_m u_u_land (
        .clk(clk),
        .rst_n(pad_rst_q),
        .d(d_i),
        .q(q_o)
    );
endmodule
"""


def dump(tmp, cells, nets, pins=()):
    """geom_dump.tcl format: C id kind master x0 y0 x1 y1 name / N sig drv sinks / P k name io sig layer x y"""
    lines = ["D\t0\t0\t1000\t1000"]
    for i, (kind, nm, x, y) in enumerate(cells):
        lines.append(f"C\t{i}\t{kind}\tDFF\t{x - 0.5}\t{y - 0.5}\t{x + 0.5}\t{y + 0.5}\t{nm}")
    for k, nm, x, y in pins:
        lines.append(f"P\t{k}\t{nm}\tINPUT\tSIGNAL\tM4\t{x}\t{y}")
    for sig, drv, sinks in nets:
        lines.append("\t".join(["N", sig, drv] + list(sinks)))
    p = tmp / "geom.tsv"
    p.write_text("\n".join(lines) + "\n")
    return geom_rules.Design(str(p))


def cells_nets():
    cells = [
        ("S", "u_bound.u_rrl_1/q$_DFF_P_", 500, 500),                                  # 0 tap 0 (leaf)
        ("S", "u_bound.u_rrl_2/q$_DFF_P_", 100, 900),                                  # 1 tap 1
        ("S", "u_bound.u_rrl_3/q$_DFF_P_", 900, 100),                                  # 2 tap 2
        ("B", "u_bound.rsz_buf_0", 300, 700),                                           # 3 buffer on the leaf net
        ("S", "u_bound.u_u_fab_u_x_0.u_st.g_seg[0].cnt[0]$_DFFE_PN0P_", 120, 880),       # 4 fab x0 sinks near tap 1
        ("S", "u_bound.u_u_fab_u_x_0.u_st.g_seg[1].cnt[0]$_DFFE_PN0P_", 140, 860),       # 5
        ("S", "u_bound.u_u_fab_u_x_1.u_st.g_seg[0].cnt[0]$_DFFE_PN0P_", 880, 120),       # 6 x1 already at its tap
        ("S", "u_bound.pad_rst_q_reg$_DFF_P_", 995, 10),                                 # 7 land reset source at the E face
        ("S", "u_bound.u_u_land.u_rstr.sync_q[0]$_DFF_PN0_", 990, 12),                   # 8 local relay at the port
        ("S", "u_bound.u_u_land.u_rstr.sync_q[1]$_DFF_PN0_", 990, 14),                   # 9
        ("S", "u_bound.u_u_land.u_rstr.rst_n$_DFF_PN0_", 990, 16),                       # 10
        ("S", "u_bound.u_u_land.tag[0][0]$_DFFE_PP_", 150, 300),                         # 11 land logic far W
        ("S", "u_bound.u_u_land.tag[0][1]$_DFFE_PP_", 170, 320),                         # 12
    ]
    nets = [
        ("rst_n_t0", "i0", ["i3"]),
        ("rsz_net_0", "i3", ["i4", "i5"]),
        ("rst_n_t1", "i1", []),
        ("rst_n_t2", "i2", ["i6"]),
        ("pad_rst_q", "i7", ["i8", "i9", "i10"]),
        ("u_u_land.u_rstr.s0", "i8", ["i9"]),
        ("u_u_land.u_rstr.s1", "i9", ["i10"]),
        ("u_u_land.rst_l", "i10", ["i11", "i12"]),
    ]
    return cells, nets


def plan_type():
    return dict(outline_um=[1000, 1000], module="dp_x")


def test_form_r_and_l(tmp_path):
    D = dump(tmp_path, *cells_nets())
    t = plan_type()
    rep = RLP.type_delta("x", t, BOUND, D, reach=300, stage_sites=True)
    # form R: u_u_fab_u_x_0 sits ~380-400 um from the leaf tap 0 (via its leaf alias) and next to tap 1
    assert t["reset"]["inst_taps"] == [dict(tap=1, sinks=["u_u_fab_u_x_0"])]
    e = rep["inst_taps"][0]
    assert e["tap_rtl"] == 0 and e["tap_was"] == [0] and e["tap"] == 1 and e["leg_was_um"] == 760 and e["leg_um"] == 80
    # x1 already on its nearest tap: untouched
    assert all(r["sinks"] != ["u_u_fab_u_x_1"] for r in t["reset"]["inst_taps"])
    # form L: u_rstr seated at the land centre, D stages on u_u_land.rst_n over the ~1,000 um leg, sites on the line
    loc = rep["local"][0]
    assert loc["group"] == "u_u_land.u_rstr" and not loc["tree_fed"] and loc["legs_over_before"] == 1
    c = loc["centre"]
    assert abs(c[0] - 160) < 1 and abs(c[1] - 310) < 1
    for k in ("u_u_land.u_rstr.sync_q[0]", "u_u_land.u_rstr.sync_q[1]", "u_u_land.u_rstr.rst_n"):
        assert t["relay_sites"][k] == [round(c[0], 3), round(c[1], 3)]
    (row,) = t["relay_depth"]
    assert row["inst"] == "u_land" and row["port"] == "rst_n" and row["side"] == "sink"     # RD-LEAF-1122: bind leaf name
    assert "land_m u_" + row["inst"] + " (" in BOUND          # bind.py instantiates leaf rel as u_<rel> and matches sv_id(rel)
    L = abs(995 - 160) + abs(10 - 310)
    assert row["D"] == -(-L // 300) - 1 == 3
    st = [t["relay_sites"][f"u_y_xd_u_land_rst_n_0_{s}.q"] for s in range(3)]               # bind.py emit_lp stage names
    hops = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip([[995, 10]] + st, st + [c])]
    assert max(hops) <= 300
    assert rep["added_reset_cycles"] == 3 and rep["legs_over_after"] == 0 and rep["legs_over_before"] == 2


def test_kit_rtl_stages_the_row_and_bind_retaps(tmp_path):
    D = dump(tmp_path, *cells_nets())
    t = plan_type()
    RLP.type_delta("x", t, BOUND, D, reach=300)
    txt, recs = PR.apply_inst_taps(BOUND, t["reset"]["inst_taps"])
    assert "cell_a u_u_fab_u_x_0 (\n        .ck(clk),\n        .rst_n(rst_n_t1)," in txt
    assert recs[0]["moved"] == ["u_u_fab_u_x_0"] and recs[0]["cycles_added"] == 0
    # idempotent (kit-rtl after a bind that already applied it)
    txt2, recs2 = PR.apply_inst_taps(txt, t["reset"]["inst_taps"])
    assert txt2 == txt and recs2[0]["bound"] == ["u_u_fab_u_x_0"]
    # KIT-RD-1 stages the form L row; the stage wires carry the names reset_leg_plan sites
    btxt, rec = KRD.apply(txt, "x", t["relay_depth"], lambda i: "u_" + RLP.sv_id(i), RLP.sv_id)
    assert rec["applied"] == 1
    for s in range(3):     # the sited key is <stage instance>.q (Yosys flop name of the ot_dp_dly stage)
        assert f"ot_dp_dly #(.W(1), .D(1)) u_y_xd_u_land_rst_n_k0_{s} (" in btxt


def test_apply_inst_taps_fail_closed():
    with pytest.raises(PR.PortRelayError):
        PR.apply_inst_taps(BOUND, [dict(tap=7, sinks=["u_u_fab_u_x_0"])])          # tap net not declared
    with pytest.raises(PR.PortRelayError):
        PR.apply_inst_taps(BOUND, [dict(tap=1, sinks=["u_u_land"])])               # rst_n is a signal, not the tree
    with pytest.raises(PR.PortRelayError):
        PR.apply_inst_taps(BOUND, [dict(tap=1, sinks=["u_rrl_2"], port="q")])      # a tree relay
    with pytest.raises(PR.PortRelayError):
        PR.apply_inst_taps(BOUND, [dict(tap=1, sinks=["u_u_fab_u_x_0"]), dict(tap=2, sinks=["u_u_fab_u_x_0"])])
    with pytest.raises(PR.PortRelayError):
        PR.apply_inst_taps(BOUND.replace("wire rst_n = rst_n_t0;", ""), [dict(tap=1, sinks=["u_u_fab_u_x_0"])])
    assert PR.apply_inst_taps(BOUND, []) == (BOUND, [])


def test_no_far_leg_is_byte_as_plan(tmp_path):
    cells, nets = cells_nets()
    cells = [c if i not in (4, 5) else (c[0], c[1], 520, 520) for i, c in enumerate(cells)]
    cells = [c if i not in (11, 12) else (c[0], c[1], 985, 20) for i, c in enumerate(cells)]
    D = dump(tmp_path, cells, nets)
    t = plan_type()
    before = json.dumps(t, sort_keys=True)
    rep = RLP.type_delta("x", t, BOUND, D, reach=300)
    assert json.dumps(t, sort_keys=True) == before
    assert rep["legs_over_before"] == 0 and not rep["inst_taps"] and not rep["local"]


def test_no_tap_in_reach_lists_local_tap(tmp_path):
    cells, nets = cells_nets()
    cells = [c if i not in (4, 5) else (c[0], c[1], 520 if i == 4 else 480, 120) for i, c in enumerate(cells)]
    cells[1] = ("S", cells[1][1], 100, 990)                         # tap 1 away too
    cells[0] = ("S", cells[0][1], 100, 600)                         # leaf tap far west
    cells[2] = ("S", cells[2][1], 990, 990)                         # tap 2 far NE
    D = dump(tmp_path, cells, nets)
    t = plan_type()
    rep = RLP.type_delta("x", t, BOUND, D, reach=300, local_taps=True)
    nl = [e for e in rep["needs_local_tap"] if e["inst"] == "u_u_fab_u_x_0"]
    assert nl and abs(nl[0]["centre"][0] - 500) < 1 and abs(nl[0]["centre"][1] - 120) < 1
    assert [500.0, 120.0] in t["reset"]["local_taps_um"]


def test_cli_keeps_plan_style(tmp_path):
    D = dump(tmp_path, *cells_nets())  # noqa: F841  (writes geom.tsv)
    plan = dict(partition_types=dict(x=plan_type()), other=dict(a=1))
    pp = tmp_path / "plan.json"
    pp.write_text(json.dumps(plan, indent=1) + "\n")
    (tmp_path / "x_bound.sv").write_text(BOUND)
    rc = RLP.main([str(pp), "x", str(tmp_path / "x_bound.sv"), str(tmp_path / "geom.tsv"), str(tmp_path / "out.json"),
                   str(tmp_path / "rep.json")])
    assert rc == 0
    out = json.loads((tmp_path / "out.json").read_text())
    assert out["other"] == dict(a=1) and out["partition_types"]["x"]["reset"]["inst_taps"]
    assert (tmp_path / "out.json").read_text().startswith('{\n "partition_types"')


def test_replicated_relay_seats_each_copy(tmp_path):
    """a REGIONS relay: each far copy at its own fanout; an inner stage that then spans over reach is split"""
    cells = [
        ("S", "u_bound.u_rrl_1/q$_DFF_P_", 500, 500),
        ("S", "u_bound.pad_rst_q_reg$_DFF_P_", 510, 500),
        ("S", "u_bound.u_u_land.u_rstr.sync_q[1]$_DFF_PN0_", 505, 505),          # 2 sync
        ("S", "u_bound.u_u_land.u_rstr.relay_q[0][0]$_DFF_PN0_", 505, 505),      # 3 copy 0
        ("S", "u_bound.u_u_land.u_rstr.relay_q[0][1]$_DFF_PN0_", 505, 505),      # 4 copy 1
        ("S", "u_bound.u_u_land.a$_DFF_PN0_", 100, 100),                          # 5 region 0
        ("S", "u_bound.u_u_land.b$_DFF_PN0_", 900, 900),                          # 6 region 1
        ("S", "u_bound.u_u_land.c$_DFF_PN0_", 520, 480),                          # 7 near: copy stays
    ]
    nets = [("pad_rst_q", "i1", ["i2", "i3", "i4"]), ("s1", "i2", ["i3", "i4"]), ("r0", "i3", ["i5"]),
            ("r1", "i4", ["i6", "i7"])]
    D = dump(tmp_path, cells, nets)
    t = plan_type()
    rep = RLP.type_delta("x", t, BOUND, D, reach=300)
    (e,) = rep["local"]
    rs = t["relay_sites"]
    assert rs["u_u_land.u_rstr.relay_q[0][0]"] == [100.0, 100.0]
    # COORD 11-21: copy 1 feeds (900, 900) and (520, 480), 800 um apart: it is split (register duplication, 0 cycles); the
    # near sink keeps the original (seated at it), the far one gets copy __rs1 at its site
    sp = {r["flop"]: r for r in t["relay_split"]}
    (c1,) = sp["u_u_land.u_rstr.relay_q[0][1]"]["clones"]
    assert c1 == dict(name="u_u_land.u_rstr.relay_q[0][1]__rs1", sinks=["u_u_land.b"]) and rs[c1["name"]] == [900.0, 900.0]
    assert rs["u_u_land.u_rstr.relay_q[0][1]"] == [520.0, 480.0]              # the original: at its own cluster (c)
    # the synchroniser then feeds copies 1,600 um apart: split too, and listed after the row whose copy it drives
    assert list(sp)[:2] == ["u_u_land.u_rstr.relay_q[0][1]", "u_u_land.u_rstr.sync_q[1]"]
    # then the entry-chain branch stages, deepest first (each drives one synchroniser copy)
    assert all(k.startswith("u_y_xd_u_land_rst_n_0_") for k in list(sp)[2:])
    assert [int(k.split("_")[-1][0]) for k in list(sp)[2:]] == sorted((int(k.split("_")[-1][0]) for k in list(sp)[2:]), reverse=True)
    assert e["copies"] == 6 and e["split_flops"] == 2
    # its source (510, 500) is then over reach from the far copy: equal-depth stages, every hop within reach
    (row,) = t["relay_depth"]
    assert row["inst"] == "u_land" and rep["legs_over_after"] == 0


def test_hard_core_sinks_are_not_retapped(tmp_path):
    """a macro reset sink is positioned by its pin, which the dump does not carry: form R leaves hard cores alone"""
    cells, nets = cells_nets()
    cells = [(("M",) + c[1:]) if i in (4, 5) else c for i, c in enumerate(cells)]
    D = dump(tmp_path, cells, nets)
    t = plan_type()
    rep = RLP.type_delta("x", t, BOUND, D, reach=300)
    assert not rep["inst_taps"] and "inst_taps" not in t.get("reset", {})


# ---- COORD 11-21: relay split (k_cover register duplication) and relay_depth D > 4
SPLIT_BOUND = """module dp_y (
    input  wire clk,
    input  wire [3:0] d_i
);
    wire lp_q;
    lep_m u_u_lep (
        .clk(clk),
        .rst_n(lp_q),
        .d(d_i)
    );
endmodule
"""


def split_design(tmp):
    g = "u_bound.u_u_lep.u.u_rstr"
    cells = [
        ("S", "u_bound.u_lpad.q[0]$_DFF_P_", 500, 20),                       # 0 signal-register source (S face)
        ("S", f"{g}.root_r$_DFF_PN0_", 500, 30),                             # 1 entry (fed by a flop: may split)
        ("S", f"{g}.g_group[0].group_r$_DFF_PN0_", 500, 40),                 # 2
        ("S", f"{g}.g_local[0].local_r$_DFF_PN0_", 500, 50),                 # 3 drives two far corners
        ("S", f"{g}.g_local[1].local_r$_DFF_PN0_", 500, 60),                 # 4 drives the NW corner
        ("S", "u_bound.u_u_lep.u.a[0]$_DFF_PN0_", 50, 50),                   # 5
        ("S", "u_bound.u_u_lep.u.a[1]$_DFF_PN0_", 70, 60),                   # 6
        ("S", "u_bound.u_u_lep.u.b[0]$_DFF_PN0_", 950, 950),                 # 7
        ("S", "u_bound.u_u_lep.u.b[1]$_DFF_PN0_", 930, 940),                 # 8
        ("S", "u_bound.u_u_lep.u.c[0]$_DFF_PN0_", 50, 950),                  # 9
        ("S", "u_bound.u_u_lep.u.c[1]$_DFF_PN0_", 60, 930),                  # 10
    ]
    nets = [("lp_q", "i0", ["i1"]), ("root", "i1", ["i2"]), ("grp", "i2", ["i3", "i4"]),
            ("rr0", "i3", ["i5", "i6", "i7", "i8"]), ("rr1", "i4", ["i9", "i10"])]
    return dump(tmp, cells, nets)


def test_k_cover_radius():
    import random
    rnd = random.Random(7)
    pts = [(f"p{i}", (rnd.uniform(0, 1500), rnd.uniform(0, 900))) for i in range(400)]
    cl = RLP.k_cover(pts, 300)
    assert sorted(k for q in cl for k, _ in q) == sorted(k for k, _ in pts)
    for q in cl:
        C = RLP.centre([xy for _k, xy in q])
        assert max(RLP.l1(C, xy) for _k, xy in q) <= 300 + 1e-6
    assert len(RLP.k_cover(pts[:1], 300)) == 1


def test_replicated_relay_is_split_and_staged(tmp_path):
    D = split_design(tmp_path)
    t = plan_type()
    rep = RLP.type_delta("y", t, SPLIT_BOUND, D, reach=300)
    g = "u_u_lep.u.u_rstr"
    rows = {r["flop"]: r for r in t["relay_split"]}
    # local_r[0] feeds the SW and NE corners: one copy per corner, each seated within reach of its sinks
    l0 = rows[f"{g}.g_local[0].local_r"]["clones"]
    assert len(l0) == 1 and l0[0]["name"] == f"{g}.g_local[0].local_r__rs1"
    # the group and root flops split above their copies; every hop of the built tree is within reach
    assert f"{g}.g_group[0].group_r" in rows and f"{g}.root_r" in rows
    (row,) = t["relay_depth"]
    assert row["inst"] == "u_lep" and row["port"] == "rst_n" and row["side"] == "sink"
    # the stage chain: straight stages to P, a stage at P, branch levels to the root copies (equal stage count per copy)
    st = [k for k in t["relay_sites"] if k.startswith("u_y_xd_u_lep_rst_n_0_")]
    assert len([k for k in st if "__rs" not in k]) == row["D"]
    assert rep["legs_over_after"] == 0 and rep["legs_over_before"] == 2   # the two local_r legs
    assert all(r["flop"] in rows for r in t["relay_split"])
    # split rows run deepest first: a row's sinks exist (original flops or copies made by an EARLIER row)
    made = set()
    for r in t["relay_split"]:
        for cl in r["clones"]:
            for s in cl["sinks"]:
                assert "__rs" not in s or s in made, (r["flop"], s)
            made.add(cl["name"])
    # each split copy is within reach of its own sinks
    for r in t["relay_split"]:
        for cl in r["clones"]:
            if cl["name"] in t["relay_sites"]:
                c = t["relay_sites"][cl["name"]]
                for s in cl["sinks"]:
                    p = t["relay_sites"].get(s)
                    if p:
                        assert RLP.l1(c, p) <= 300 + 1e-6


def test_top_pin_fed_entry_is_not_split(tmp_path):
    g = "u_bound.u_u_lep.u.u_rstr"
    cells = [("S", f"{g}.sync_q[0]$_DFF_PN0_", 500, 30),
             ("S", "u_bound.u_u_lep.u.a[0]$_DFF_PN0_", 50, 50), ("S", "u_bound.u_u_lep.u.b[0]$_DFF_PN0_", 950, 950)]
    D = dump(tmp_path, cells, [("arst_n", "p0", ["i0"]), ("q", "i0", ["i1", "i2"])], pins=[(0, "arst_n", 500, 0)])
    t = plan_type()
    rep = RLP.type_delta("y", t, SPLIT_BOUND, D, reach=300)
    assert "relay_split" not in t
    assert rep["split"] and rep["split"][0]["unsplit"].startswith("fed by a top-level pin")


def test_relay_depth_over_four_stages(tmp_path):
    D = dump(tmp_path, *cells_nets())
    t = plan_type()
    rep = RLP.type_delta("x", t, BOUND, D, reach=120, stage_sites=True)
    (row,) = [r for r in t["relay_depth"] if r["inst"] == "u_land"]
    assert row["D"] > 4 and not rep["relay_depth"][0]["over_cap"]
    import schema
    sch = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    assert sch["relay_depth"]["items"]["properties"]["D"]["maximum"] >= row["D"]
    assert "relay_split" in sch


def test_kit_istations_emits_relay_split():
    import kit_istations as KI
    t = {"relay_sites": {"u_a.r__rs1": [10.0, 20.0], "u_a.r": [1.0, 2.0]},
         "relay_split": [{"flop": "u_a.r", "clones": [{"name": "u_a.r__rs1", "sinks": ["u_b.x[0]", "u_b.x[1]"]}]}]}
    tcl = KI.relay_sites_only_tcl("t", t)
    assert "proc rs_split_all" in tcl
    assert "rs_split_all [list {{u_a.r} {{{u_a.r__rs1} {{u_b.x[0]} {u_b.x[1]}}}}}]" in tcl
    assert tcl.index("rs_split_all [list") < tcl.index("rs_place_all [dict")
    for bad in ({"flop": "u_a.r", "clones": [{"name": "u_c.r__rs1", "sinks": ["s"]}]},
                {"flop": "u_a.r", "clones": [{"name": "u_a.r__rs1", "sinks": []}]},
                {"flop": "u_a.r", "clones": [{"name": "u_a.r__rs1", "sinks": ["a b"]}]}):
        with pytest.raises(SystemExit):
            KI.relay_sites_only_tcl("t", {"relay_sites": {}, "relay_split": [bad]})


# ---- COORD 11-21 (FABLE-CLOSURE-1730, CORE-LIB-LIMITS-1330 lever 4): reset forwards (form F), flattened relays, crr relay
# flops, hard-macro reset pins, stage sites by default
FWD_BOUND = """module dp_f (
    input  wire clk,
    input  wire [1:0] dn_i
);
    wire [1:0] dn_b;
    wire dn_eb;
    wire [1:0] dn_q;
    wire dn_eq;
    wire w_vsw_q;
    wire w_inv;
    ot_dp_st #(.W(2)) u_bin_dn (.clk(clk), .rst_n(1'b1), .d(dn_i), .ea(1'b0), .q(dn_b), .eq(dn_eb));
    ot_dp_dly #(.W(3), .D(1)) u_lpad_dn (.clk(clk), .d({dn_eb, dn_b}), .q({dn_eq, dn_q}));
    ot_s81sl_crr u_u_crr_vsw (
        .clk(clk),
        .d(dn_q[0]),
        .q(w_vsw_q)
    );
    ot_rst_relay u_u_vp_u_rr (
        .clk(clk),
        .rst_n_in(dn_q[0]),
        .rst_n(w_rr)
    );
    assign w_inv = !dn_q[0];
    hard_core u_hc (
        .clk(clk),
        .rst_n(dn_q[1]),
        .d(dn_b)
    );
    assign y = dn_q[1] & w_vsw_q;
endmodule
"""


def fwd_design(tmp):
    cells = [
        ("S", "u_bound.u_bin_dn.q[0]$_DFF_P_", 995, 500),                    # 0 face station
        ("S", "u_bound.u_lpad_dn.q[0]$_DFF_P_", 990, 500),                   # 1 the reset bit at the face
        ("S", "u_bound.u_u_crr_vsw/q$_DFF_P_", 100, 500),                    # 2 crr relay 890 um away
        ("S", "u_bound.u_u_vp_u_rr.rst_n[0]$_DFF_PN0_", 150, 520),           # 3 flattened bound relay
        ("S", "u_bound.u_u_vp.a$_DFF_PN0_", 120, 540),                       # 4 vp logic
        ("S", "u_bound.u_u_x.b$_DFF_P_", 80, 480),                           # 5 crr load
        ("S", "u_bound.u_bin_dn.q[1]$_DFF_P_", 995, 510),                    # 6
        ("S", "u_bound.u_lpad_dn.q[1]$_DFF_P_", 990, 510),                   # 7 data + core reset (not reset-only)
        ("M", "u_bound.u_hc", 400, 100),                                      # 8 hard core, reset pin far from its centre
    ]
    nets = [("b0", "i0", ["i1"]), ("q0", "i1", ["i2", "i3"]), ("rr", "i3", ["i4"]), ("vsw", "i2", ["i5"]),
            ("b1", "i6", ["i7"]), ("q1", "i7", ["i8"])]
    D = dump(tmp, cells, nets)
    return D


def test_reset_only_and_bit_of():
    W = RLP._widths(FWD_BOUND)
    assert RLP.bit_of("{dn_eq, dn_q}", 0, W) == "dn_q[0]" and RLP.bit_of("{dn_eq, dn_q}", 2, W) == "dn_eq"
    assert RLP.reset_only(FWD_BOUND, "dn_q[0]")                 # crr .d, relay rst_n_in, inverted copy
    assert not RLP.reset_only(FWD_BOUND, "dn_q[1]")             # also used as data (y = dn_q[1] & ...)
    assert RLP.fwd_entry(FWD_BOUND, "u_lpad_dn.q[0]") == ("u_lpad_dn", "d", [0, 0], "dn_q[0]")
    assert RLP.fwd_entry(FWD_BOUND, "u_u_vp.a") is None


def test_reset_forward_lane_pad_bit(tmp_path):
    D = fwd_design(tmp_path)
    t = plan_type()
    rep = RLP.type_delta("f", t, FWD_BOUND, D, reach=300)
    rows = {(r["inst"], r["port"]): r for r in t["relay_depth"]}
    # the reset bit moves to its fanout (crr + vp relay ~850 um W of the face); its own input bit is staged from the face
    r = rows[("lpad_dn", "d")]
    assert r["bits"] == [0, 0] and r["D"] >= 2 and "form F" in r["note"]
    x, y = t["relay_sites"]["u_lpad_dn.q[0]"]
    assert x < 300
    st = sorted(k for k in t["relay_sites"] if k.startswith("u_y_xd_lpad_dn_d_0_"))
    assert len(st) == r["D"]                                     # stage sites by default, spread on the leg
    pts = [(995.0, 500.0)] + [tuple(t["relay_sites"][k]) for k in st] + [(x, y)]
    assert max(RLP.l1(a, b) for a, b in zip(pts, pts[1:])) <= 300 + 1e-6
    # bit 1 also carries data: untouched (no row, no site)
    assert ("lpad_dn", "d") in rows and all(rr.get("bits") != [1, 1] for rr in t["relay_depth"])
    assert "u_lpad_dn.q[1]" not in t["relay_sites"]
    assert any(e["form"] == "F" for e in rep["local"]) and rep["legs_over_after"] == 0
    # KIT-RD-1 stages bit 0 of the concatenated pad input
    btxt, rec = KRD.apply(FWD_BOUND, "f", t["relay_depth"], lambda i: "u_" + RLP.sv_id(i), RLP.sv_id)
    assert rec["applied"] == len(t["relay_depth"])
    assert "assign rdk_lpad_dn_d_k0_in = {dn_eb, dn_b};" in btxt


def test_flat_relay_and_crr_are_groups(tmp_path):
    D = fwd_design(tmp_path)
    G = RLP.Geo(D)
    gs = RLP.local_groups(G)
    assert "u_u_vp_u_rr" in gs and "u_u_crr_vsw" in gs


def test_macro_reset_pin_xy(tmp_path):
    cells = [("S", "u_bound.u_f.q$_DFF_P_", 0, 0), ("M", "u_bound.u_hc", 500, 500)]
    p = tmp_path / "g.tsv"
    lines = ["D\t0\t0\t1000\t1000"]
    for i, (k, nm, x, y) in enumerate(cells):
        lines.append(f"C\t{i}\t{k}\tDFF\t{x - 0.5}\t{y - 0.5}\t{x + 0.5}\t{y + 0.5}\t{nm}")
    lines += ["MR\t1\t20\t30", "N\tSIGNAL\ti0\ti1"]
    p.write_text("\n".join(lines) + "\n")
    G = RLP.Geo(geom_rules.Design(str(p)))
    assert G.sxy(1) == (20.0, 30.0) and G.sxy(0) == G.xy(0)


def test_forward_into_hard_core_reset_pin(tmp_path):
    """form M: dn_q[1] (data AND a core reset) drives u_hc.rst_n from the face; the core's reset pin (MR) is ~1,000 um
    away: D stages on the core's rst_n port only (the data use of the bit keeps its latency), sited on the line"""
    D = fwd_design(tmp_path)
    p = tmp_path / "geom.tsv"
    p.write_text(p.read_text() + "MR\t8\t300\t20\n")
    D = geom_rules.Design(str(p))
    t = plan_type()
    rep = RLP.type_delta("f", t, FWD_BOUND, D, reach=300)
    (row,) = [r for r in t["relay_depth"] if r["inst"] == "hc"]
    L = abs(990 - 300) + abs(510 - 20)
    assert row["port"] == "rst_n" and row["side"] == "sink" and row["D"] == -(-L // 300) - 1 and "form M" in row["note"]
    k = t["relay_depth"].index(row)
    st = [t["relay_sites"][f"u_y_xd_hc_rst_n_0_{s}.q"] for s in range(row["D"])]
    pts = [(990.0, 510.0)] + [tuple(x) for x in st] + [(300.0, 20.0)]
    assert max(RLP.l1(a, b) for a, b in zip(pts, pts[1:])) <= 300 + 1e-6
    assert "u_lpad_dn.q[1]" not in t["relay_sites"]           # the data register is not moved
    assert any(e["form"] == "M" for e in rep["local"])


def nested_design(tmp, far=1900.0):
    """bk_sel shape: reset tap flop at (2000, 400), hard cores NESTED below u_core (u_core.u_sel.g_q[0].u_q, .u_c, u_tx),
    one core far away (reset pins `far` um to the W), one near; MR rows carry the pin name"""
    cells = [
        ("S", "u_bound.u_rrl_1/q$_DFF_P_", 2000, 400),                              # 0 tap
        ("M", "u_bound.u_core.u_sel.g_q\\[0\\].u_q", 100, 100),                   # 1 far core
        ("M", "u_bound.u_core.u_sel.u_c", 2000, 350),                               # 2 near core
        ("M", "u_bound.u_core.u_tx", 1000, 600),                                    # 3 mid core, 2 levels shallower
        ("M", "u_bound.u_other.u_hc", 1990, 380),                                   # 4 another group, near
    ]
    nets = [("rst", "i0", ["i1", "i2", "i3", "i4"])]
    D = dump(tmp, cells, nets)
    p = tmp / "geom.tsv"
    p.write_text(p.read_text().replace("D\t0\t0\t1000\t1000", "D\t0\t0\t3000\t3000", 1) + f"MR\t1\t{2000 - far}\t140\trst\nMR\t2\t2050\t340\trst_n\nMR\t3\t1200\t640\trst\n"
                 "MR\t4\t2000\t390\trst\n")
    return geom_rules.Design(str(p))


def test_nested_hard_core_reset_pins(tmp_path):
    """form N: a hard core below a bound instance (any depth) gets D stages on its reset pins, sited on the line; the cores
    of one top-level group all get the largest D (they release together); a near group is untouched; row in
    reset_pin_relay, NOT relay_depth (bind would refuse a row with no bound call)"""
    D = nested_design(tmp_path)
    t = plan_type()
    rep = RLP.type_delta("n", t, FWD_BOUND, D, reach=300)
    rows = {r["inst"]: r for r in t["reset_pin_relay"]}
    assert set(rows) == {"u_core.u_sel.g_q[0].u_q", "u_core.u_sel.u_c", "u_core.u_tx"}   # u_other.u_hc: leg <= 300
    L = abs(2000 - 100) + abs(400 - 140)
    Dn = -(-L // 300) - 1
    assert {r["D"] for r in rows.values()} == {Dn} and Dn >= 6
    assert rows["u_core.u_sel.u_c"]["ports"] == ["rst_n"] and rows["u_core.u_sel.g_q[0].u_q"]["ports"] == ["rst"]
    assert not t.get("relay_depth")
    r = rows["u_core.u_sel.g_q[0].u_q"]
    pts = [(2000.0, 400.0)] + [tuple(t["relay_sites"][RLP.NESTED_KEY.format(inst=r["inst"], port="rst", s=s)])
                               for s in range(Dn)] + [(100.0, 140.0)]
    assert max(RLP.l1(a, b) for a, b in zip(pts, pts[1:])) <= 300 + 1e-6 and r["hop_um"] <= 300
    assert rep["legs_over_before"] == 2 and rep["legs_over_after"] == 0 and rep["added_reset_cycles"] == Dn


def test_nested_rows_in_schema():
    import schema
    props = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    assert "reset_pin_relay" in props


def test_stage_site_over_a_hard_core_is_snapped_to_a_legal_site(tmp_path):
    """a form N stage line that crosses another hard core: the stage site inside the (grown) core moves to the nearest legal
    site and the hops are re-checked (reported in site_snaps / snap_hop_um)"""
    cells = [
        ("S", "u_bound.u_rrl_1/q$_DFF_P_", 1000, 100),                                    # 0 source
        ("M", "u_bound.u_core.u_a", 100, 100),                                           # 1 target core, pins at (150, 100)
        ("M", "u_bound.u_core.u_wall", 433, 100),                                        # 2 a core ON the line (stage 2 at x 433)
    ]
    D = dump(tmp_path, cells, [("rst", "i0", ["i1"])])
    p = tmp_path / "geom.tsv"
    lines = p.read_text().splitlines()
    lines = [("C\t2\tM\tDFF\t413\t0\t453\t200\tu_bound.u_core.u_wall" if ln.startswith("C\t2\t") else ln) for ln in lines]
    p.write_text("\n".join(lines) + "\nMR\t1\t150\t100\trst\n")
    D = geom_rules.Design(str(p))
    t = plan_type()
    rep = RLP.type_delta("n", t, FWD_BOUND, D, reach=300)
    c = 4.32
    assert rep["site_snaps"], "a stage site fell inside the wall core"
    for xy in t["relay_sites"].values():
        assert not (413 - c < xy[0] < 453 + c and 0 - c < xy[1] < 200 + c)
    assert all(h["hop_um"] >= 0 for h in rep["snap_hop_um"])


def test_stage_rows_carry_a_lockup_latch_by_default(tmp_path):
    """FABLE-CLOSURE-1930 lever 2: same-edge reset stages across clock taps are zero-logic hold pairs; the rows the tool emits
    carry lockup: true (kit-rtl / bind add an ot_dp_lk negative-level latch after every stage, 0 cycles); --no-lockup = same edge"""
    D = fwd_design(tmp_path)
    p = tmp_path / "geom.tsv"
    p.write_text(p.read_text() + "MR\t8\t300\t20\n")
    D = geom_rules.Design(str(p))
    t = plan_type()
    RLP.type_delta("f", t, FWD_BOUND, D, reach=300)
    rows = [r for r in t["relay_depth"] if r["inst"] == "hc"]
    assert rows and all(r["lockup"] is True for r in t["relay_depth"])
    t2 = plan_type()
    RLP.type_delta("f", t2, FWD_BOUND, D, reach=300, lockup=False)
    assert not any("lockup" in r for r in t2["relay_depth"])
    btxt, rec = KRD.apply(FWD_BOUND, "f", t["relay_depth"], lambda i: "u_" + RLP.sv_id(i), RLP.sv_id)
    n_stage = sum(r["D"] for r in rec["rows"] if r["how"] == "kit-rtl")
    assert btxt.count("ot_dp_lk #(") == n_stage > 0 and rec["needs_cells"] == ["ot_dp_lk"]
    assert "u_lk_xd_" in btxt
    btxt2, rec2 = KRD.apply(FWD_BOUND, "f", t2["relay_depth"], lambda i: "u_" + RLP.sv_id(i), RLP.sv_id)
    assert "ot_dp_lk" not in btxt2 and "needs_cells" not in rec2


def test_stage_key_is_the_bind_stage_instance():
    """RD-LEAF-1122: a relay_sites stage key names the flop of the stage bind.py emits for the row (emit_lp:
    short_id('u_y_xd_' + sv_id(leaf) + '_' + port + '_' + k + '_' + s, 100)), also for a port with '__'."""
    import bind
    for leaf, port in (("astk_WN", "g_phys_fault_u_fault__rst_n"), ("u_land", "rst_n"), ("seq_g_fan_0_u_fan", "rst_n")):
        for s in range(3):
            key = RLP.STAGE_KEY.format(sid=RLP.sv_id(leaf), port=RLP.sv_id(port), k=5, s=s)
            assert key == bind.short_id("u_y_xd_" + bind.sv_id(leaf) + "_" + port + "_0_" + str(s), 100) + ".q"


def test_merged_core_reset_port_stages_every_native_pin(tmp_path):
    """ASTK-MERGE-1122: a core whose native_port_adapter merges native reset pins into rst_n (kv3_astk) gets the SAME
    stages on every native pin of the group; only the port's own chain is sited (the adapter keeps it)."""
    D = fwd_design(tmp_path)
    p = tmp_path / "geom.tsv"
    p.write_text(p.read_text() + "MR\t8\t300\t20\n")
    D = geom_rules.Design(str(p))
    t = plan_type()
    t["hard_cores"] = [dict(inst="hc", module="hard_core", native_port_adapter=dict(merge={"rst_n": ["rst_n", "u_a__rst_n", "u_b__rst_n"]}))]
    RLP.type_delta("f", t, FWD_BOUND, D, reach=300)
    rows = [r for r in t["relay_depth"] if r["inst"] == "hc"]
    assert [r["port"] for r in rows] == ["rst_n", "u_a__rst_n", "u_b__rst_n"]
    assert len({r["D"] for r in rows}) == 1
    assert all(k.startswith("u_y_xd_hc_rst_n_0_") for k in t["relay_sites"] if k.startswith("u_y_xd_hc_"))
