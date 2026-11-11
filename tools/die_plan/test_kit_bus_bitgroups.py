"""KIT-ISTATIONS 11-11: per-bit-group sites of a multi-core bus chain (kit_bus_bitgroups, kit_istations integration)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_bus_bitgroups as BG  # noqa: E402
import kit_istations as KI  # noqa: E402

# 2-core in bus (8 bits): core a reads [3:0] at x=100, core b reads [7:4] at x=2000, face at x=1000, y=0..; depth 2
FACE, A_END, B_END = (500.0, 0.0), (100.0, 600.0), (900.0, 600.0)


def row(core, bits, end, regs, launch="face bus L_i"):
    return dict(conn="bus:L_i", from_um=list(FACE), to_um=list(end), regs_um=[list(r) for r in regs], bits=bits,
                launch=launch, capture=f"{core}.p", note="t")


ROWS = [row("u_a", 4, A_END, [(400.0, 200.0), (200.0, 400.0)]),
        row("u_b", 4, B_END, [(600.0, 200.0), (800.0, 400.0)])]
BOUND_IN = """module m (input wire clk, input wire rst_n, input wire [8:0] L_i);
    wire [7:0] L_i_q;
    wire L_i_eq;
    wire [3:0] w_c_ra_Q;
    wire [3:0] w_c_rb_Q;
    reg [3:0] g_c_ra_q;
    reg [3:0] g_c_rb_q;
    assign w_c_ra_Q = g_c_ra_q;
    assign w_c_rb_Q = g_c_rb_q;
    ot_dp_st #(.W(8)) u_bin_L_i (.clk(clk), .rst_n(rst_n), .d(L_i[7:0]), .ea(L_i[8]), .q(L_i_q), .eq(L_i_eq));
    always @(posedge clk) g_c_ra_q <= L_i_q[3:0];
    always @(posedge clk) if (!rst_n) g_c_rb_q <= 4'b0; else g_c_rb_q <= L_i_q[7:4];
    leafA u_u_a (
        .x(w_c_ra_Q[3:0])
    );
    leafA u_u_b (
        .x(w_c_rb_Q)
    );
endmodule
"""


def test_in_owners_and_sites():
    cores = ["u_a", "u_b"]
    own = BG.in_bit_owners(BOUND_IN, "L_i", cores)
    assert {b for b, c in own.items() if c == {"u_a"}} == {0, 1, 2, 3}
    assert {b for b, c in own.items() if c == {"u_b"}} == {4, 5, 6, 7}
    g = BG.plan_groups(ROWS, True, 2, 8, own)
    assert g["unresolved_bits"] == 0
    assert g["stages"][0] == [(0, 3, 400.0, 200.0), (4, 7, 600.0, 200.0)]
    assert g["stages"][1] == [(0, 3, 200.0, 400.0), (4, 7, 800.0, 400.0)]
    assert all(v["hop_um"] <= 405 for v in g["groups"].values())


def test_resample_to_chain_depth_and_merged_violation():
    shallow = [row("u_a", 4, A_END, [(500.0, 300.0)]), ROWS[1]]       # u_a planned 1 stage, chain depth 2
    own = BG.in_bit_owners(BOUND_IN, "L_i", ["u_a", "u_b"])
    g = BG.plan_groups(shallow, True, 2, 8, own)
    a = [r for r in g["stages"][0] if r[0] == 0][0]
    assert a[2] < 500 and a[3] > 0                              # a point on u_a's own route (west), not u_b's
    merged = [(1350.0, 200.0), (1400.0, 500.0)]                  # a pile far east: u_a's core end is > 405 away
    assert BG.merged_violates(ROWS, merged, True)
    assert not BG.merged_violates(ROWS[:1], [(400.0, 200.0), (200.0, 400.0)], True)


def test_out_owners_concat():
    txt = ("module m;\n  wire [3:0] w_u_a_y;\n  wire [3:0] w_u_b_y;\n  wire [3:0] w_c_Q;\n  reg [3:0] g_c_q;\n"
           "  assign w_c_Q = g_c_q;\n  always @(posedge clk) g_c_q <= w_u_b_y;\n"
           "  ot_dp_st #(.W(8)) u_bout_L_o (.clk(clk), .rst_n(rst_n), .d({w_c_Q, w_u_a_y}), .ea(x), .q(q), .eq(e));\nendmodule\n")
    own = BG.out_bit_owners(txt, "L_o", 8, ["u_a", "u_b"])
    assert {b for b, c in own.items() if c == {"u_b"}} == {4, 5, 6, 7}
    assert {b for b, c in own.items() if c == {"u_a"}} == {0, 1, 2, 3}


def test_single_entry_bus_identity():
    t = dict(internal_stations=[ROWS[0]])
    out = KI.bus_entries(t)
    assert len(out) == 1 and out[0] == ROWS[0] and "per_core_rows" not in out[0]


def test_multi_entry_bus_register_set_unchanged():
    t = dict(internal_stations=ROWS)
    (m,) = KI.bus_entries(t)
    assert len(m["regs_um"]) == 2 and m["bits"] == 8 and m["merged_entries"] == 2      # same chain depth / registers
    assert len(m["per_core_rows"]) == 2


def test_tcl_lines_and_proc():
    own = BG.in_bit_owners(BOUND_IN, "L_i", ["u_a", "u_b"])
    g = BG.plan_groups(ROWS, True, 2, 8, own)
    ln = BG.tcl_lines(["u_ist_L_i_0", "u_ist_L_i_1"], g, [(1250.0, 200.0), (1100.0, 500.0)], "L_i")
    assert ln[0] == "is_place_bits {*u_ist_L_i_0[./]*} {1250.0 200.0} ist:L_i {{0 3 400 200} {4 7 600 200}}"
    assert "proc is_place_bits" in BG.BITS_TCL and BG.BITS_TCL.count("{") == BG.BITS_TCL.count("}")


import subprocess  # noqa: E402


def _kit(tmp_path, rows, hard, name):
    kd = tmp_path / name
    kd.mkdir()
    bound = kd / "t_part_bound.sv"
    bound.write_text(BOUND_IN.replace("module m ", "module t_part_bound ").replace(
        "input wire [8:0] L_i", "input wire [8:0] L_i"))
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(bound)])))
    plan = dict(partition_types=dict(t=dict(
        buses=[dict(name="L_i", dir="in", width=8, kind="data")],
        hard_cores=[dict(inst=h) for h in hard],
        internal_stations=rows)))
    pf = tmp_path / f"{name}.json"
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return kd, r.stdout


def test_end_to_end_violating_merged_chain_gets_bit_groups(tmp_path):
    # merged centroid of the two rows is mid-die: u_a (x=100) and u_b (x=900) are both > 405 um from it -> bit groups
    kd, out = _kit(tmp_path, ROWS, ["u_a", "u_b"], "viol")
    tcl = (kd / "istations.tcl").read_text()
    assert "proc is_place_bits" in tcl and "is_place_bits {*u_ist_L_i_0[./]*}" in tcl and "is_place_bits {*u_ist_L_i_1[./]*}" in tcl
    assert "per-bit-group sites for 2 cores" in out
    assert "is_place {*u_ist_L_i_0[./]*}" not in tcl
    # register set / depth unchanged: 2 stations inserted on the one chain
    assert (kd / "t_part_bound.sv").read_text().count("ot_dp_st #(.W(8)) u_ist_L_i_") == 2


def test_end_to_end_ok_merged_chain_is_unchanged(tmp_path):
    near = [row("u_a", 4, (480.0, 500.0), [(500.0, 150.0), (490.0, 350.0)]),
            row("u_b", 4, (520.0, 500.0), [(500.0, 150.0), (510.0, 350.0)])]
    kd, out = _kit(tmp_path, near, ["u_a", "u_b"], "ok")
    tcl = (kd / "istations.tcl").read_text()
    assert "is_place_bits" not in tcl and "is_place {*u_ist_L_i_0[./]*}" in tcl
    kd2, _ = _kit(tmp_path, near, ["u_a", "u_b"], "ok2")      # forced off = byte-identical to auto when not violating
    assert (kd2 / "istations.tcl").read_text() == tcl


def test_landing_pad_delay_is_pass_through():
    txt = BOUND_IN.replace("    always @(posedge clk) g_c_ra_q <= L_i_q[3:0];\n",
                           "    wire [0:0] pd_0;\n    ot_dp_dly #(.W(1), .D(2)) u_pd_0 (.clk(clk), .d(L_i_q[0]), .q(pd_0));  // landing pad\n"
                           "    always @(posedge clk) g_c_ra_q <= {L_i_q[3:1], pd_0[0]};\n")
    own = BG.in_bit_owners(txt, "L_i", ["u_a", "u_b"])
    assert 0 in own and own[0] == {"u_a"}
