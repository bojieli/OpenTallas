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
    assert loc["group"] == "u_u_land.u_rstr" and not loc["tree_fed"] and loc["out_leg_um"] > 800
    c = loc["centre"]
    assert abs(c[0] - 160) < 1 and abs(c[1] - 310) < 1
    for k in ("u_u_land.u_rstr.sync_q[0]", "u_u_land.u_rstr.sync_q[1]", "u_u_land.u_rstr.rst_n"):
        assert t["relay_sites"][k] == [round(c[0], 3), round(c[1], 3)]
    (row,) = t["relay_depth"]
    assert row["inst"] == "u_u_land" and row["port"] == "rst_n" and row["side"] == "sink"
    L = abs(995 - 160) + abs(10 - 310)
    assert row["D"] == -(-L // 300) - 1 == 3
    st = [t["relay_sites"][f"u_y_xd_u_u_land_rst_n_k0_{s}.q"] for s in range(3)]
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
        assert f"ot_dp_dly #(.W(1), .D(1)) u_y_xd_u_u_land_rst_n_k0_{s} (" in btxt


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
    """a REGIONS relay: each far copy at its own fanout; its inner stages and input leg are left alone"""
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
    assert e["copies"] == 2 and e["seated"] == 2
    rs = t["relay_sites"]
    assert rs["u_u_land.u_rstr.relay_q[0][0]"] == [100.0, 100.0]
    assert rs["u_u_land.u_rstr.relay_q[0][1]"] == [710.0, 690.0]           # L1 centre of (900, 900) and (520, 480)
    assert "u_u_land.u_rstr.sync_q[1]" not in rs                           # inner stage of a replicated relay stays
    assert not any(k.startswith("u_y_xd_") for k in rs)
    assert not t.get("relay_depth")                                        # source within reach of the synchroniser
