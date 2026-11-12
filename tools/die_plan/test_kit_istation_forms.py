"""HBM-KITIST-1 11-12: kit_istation_forms (pad_landing per-bit station depth, station_trees) -- structure, fail-closed
gates, default-off, and an iverilog cycle check of the per-bit latencies of the generated RTL."""
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_istation_forms as KF  # noqa: E402

CELLS = """module ot_dp_st #(parameter integer W = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d, input wire ea,
    output reg [W-1:0] q, output reg eq);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n) if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
module ot_dp_ste #(parameter integer W = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d, input wire ea,
    output reg [W-1:0] q, output reg eq);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n) if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
module core3 (input wire [2:0] din, output wire [2:0] dout); assign dout = din; endmodule
module core4 (input wire [3:0] din, input wire ev, output wire [3:0] dout, output wire eo); assign dout = din; assign eo = ev; endmodule
"""

OUT_BOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire [5:0] i_a, output wire [6:0] o);
    wire [2:0] w_A_out;
    wire [2:0] w_B_out;
    assign w_A_out = i_a[2:0];
    assign w_B_out = i_a[5:3];
    ot_dp_ste #(.W(6)) u_bout_o (.clk(clk), .rst_n(rst_n), .d({w_B_out[2:0], w_A_out[2:0]}), .ea(rst_n), .q(o[5:0]), .eq(o[6]));
endmodule
"""

IN_BOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire [6:0] i, output wire [3:0] ya, output wire [3:0] yb,
    output wire ea_o, output wire eb_o);
    wire [5:0] i_q;
    wire i_eq;
    ot_dp_st #(.W(6)) u_bin_i (.clk(clk), .rst_n(rst_n), .d(i[5:0]), .ea(i[6]), .q(i_q), .eq(i_eq));
    core4 u_A (
        .din(i_q[3:0]),
        .ev(i_eq),
        .dout(ya),
        .eo(ea_o)
    );
    core4 u_B (
        .din(i_q[5:2]),
        .ev(i_eq),
        .dout(yb),
        .eo(eb_o)
    );
endmodule
"""

PLAIN_IN = """module t_part_bound (input wire clk, input wire rst_n, input wire [6:0] i, output wire [5:0] y, output wire ye);
    wire [5:0] i_q;
    wire i_eq;
    ot_dp_st #(.W(6)) u_bin_i (.clk(clk), .rst_n(rst_n), .d(i[5:0]), .ea(i[6]), .q(i_q), .eq(i_eq));
    assign y = i_q;
    assign ye = i_eq;
endmodule
"""


def kit(tmp_path, bound, name="kit"):
    kd = tmp_path / name
    kd.mkdir()
    (kd / "t_part_bound.sv").write_text(bound)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(kd / "t_part_bound.sv")])))
    return kd


def run_ist(tmp_path, plan, kd, *flags):
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    return subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd), *flags],
                          capture_output=True, text=True)


def row(launch, capture, regs, bits, frm, to):
    return dict(conn="bus:" + ("o" if capture.startswith("face") else "i"), from_um=frm, to_um=to,
                regs_um=[[x, 0] for x in regs], bits=bits, launch=launch, capture=capture)


def out_plan(depth_runs, k=4, extra=None):
    t = dict(buses=[dict(name="o", dir="out", width=6, kind="data", face="W")],
             internal_stations=[
                 dict(row("A.out", "face bus o", range(100, 100 * (k + 1), 100), 3, [0, 0], [500, 0]), conn="bus:o"),
                 dict(row("B.out", "face bus o", range(100, 100 * (k + 1), 100), 3, [0, 900], [500, 900]), conn="bus:o")],
             pad_landing=[dict(bus="o", bit_depth=depth_runs)])
    t.update(extra or {})
    return dict(partition_types=dict(t=t))


def in_plan(k, extra):
    rows = [dict(conn="bus:i", from_um=[0, 0], to_um=[900, 0], regs_um=[[100 * (j + 1), 0] for j in range(k)], bits=4,
                 launch="face bus i", capture="A.din")]
    t = dict(buses=[dict(name="i", dir="in", width=6, kind="data", face="E")], internal_stations=rows)
    t.update(extra)
    return dict(partition_types=dict(t=t))


def sim(tmp_path, files, tb, top="tb"):
    if not shutil.which("iverilog"):
        pytest.skip("iverilog missing")
    (tmp_path / "cells.v").write_text(CELLS)
    (tmp_path / "tb.v").write_text(tb)
    r = subprocess.run(["iverilog", "-g2012", "-o", str(tmp_path / "a.out"), str(tmp_path / "cells.v"), *map(str, files),
                        str(tmp_path / "tb.v")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run(["vvp", str(tmp_path / "a.out")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return [ln for ln in r.stdout.splitlines() if ln.startswith("S ")]


def latencies(lines, nbits, drive_col=0):
    """lines 'S t in out' (binary strings) -> per bit latency (set), by comparing every bit against the driven history"""
    hist, outs = [], []
    for ln in lines:
        _, t_, i_, o_ = ln.split()
        hist.append(i_)
        outs.append(o_)
    lat = []
    for b in range(nbits):
        ok = None
        for L in range(0, 12):
            if all(outs[t][::-1][b] == hist[t - L][::-1][b] for t in range(15, len(hist))):
                ok = L
                break
        lat.append(ok)
    return lat


OUT_TB = """module tb; reg clk=0, rst_n=0; reg [5:0] i_a=0; wire [6:0] o; integer t=0; reg [31:0] r;
  t_part_bound u(.clk(clk), .rst_n(rst_n), .i_a(i_a), .o(o));
  always #5 clk = ~clk;
  initial begin #22 rst_n = 1; end
  always @(negedge clk) begin r = $random; i_a <= r[5:0]; end
  always @(posedge clk) begin t = t + 1; #1 $display("S %0d %b %b", t, i_a, o[5:0]); end
  initial begin #3000 $finish; end
endmodule
"""


def test_pure_helpers():
    assert KF.expand_runs([[0, 2, 1], [3, 5, 3]], 6) == [1, 1, 1, 3, 3, 3]
    with pytest.raises(ValueError):
        KF.expand_runs([[0, 2, 1]], 6)
    with pytest.raises(ValueError):
        KF.expand_runs([[0, 3, 1], [3, 5, 3]], 6)
    assert KF.compress_runs([1, 1, 2, 2, 2, 1]) == [[0, 1, 1], [2, 4, 2], [5, 5, 1]]
    assert KF.check_pair(6, [2, 4], 6, [10, 9]) == [1]            # bit 1: 4 + 9 != 12
    assert KF.check_pair(6, [2, 4], 6, KF.peer_depth(6, [2, 4], 6)) == []
    assert KF.reach_need([0, 0], [720, 0]) == 1 and KF.reach_need([0, 0], [721, 0]) == 2 and KF.reach_need([0, 0], [0, 0]) == 0
    assert KF.cat([("a", 5), ("a", 4), ("b", 1), ("1'b0", None), ("a", 0)]) == "{a[5:4], b[1], 1'b0, a[0]}"
    assert KF.cat([("a", 3)]) == "a[3]"


def test_bit_depth_from_rows_is_the_reach_floor():
    rows = [dict(launch="A.out", capture="face bus o", from_um=[0, 0], to_um=[500, 0], regs_um=[[1, 1]] * 4),
            dict(launch="B.out", capture="face bus o", from_um=[0, 0], to_um=[1500, 0], regs_um=[[1, 1]] * 4)]
    d = KF.bit_depth_from_rows(rows, {0: {"A"}, 1: {"A"}, 2: {"B"}, 3: {"A", "B"}}, 5, 4)
    assert d == [1, 1, 4, 4, 4]                                    # A needs 1, B needs ceil(1500/360)-1 = 4; unresolved bit keeps K


def test_out_pad_landing_structure_and_cycles(tmp_path):
    kd = kit(tmp_path, OUT_BOUND)
    plan = out_plan([[0, 2, 2], [3, 5, 4]])
    r = run_ist(tmp_path, plan, kd)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    # stage widths: B bits (d=4) enter at stage 0, A bits (d=2) at stage 2
    for j, w in enumerate([3, 3, 6, 6]):
        assert f"ot_dp_st #(.W({w})) u_ist_o_{j} " in sv
    assert "ot_dp_ste" not in sv
    assert ".d(o_is3_q[5:0])" in sv and ".eq(o[6])" in sv and ".ea(o_is3_eq)" in sv
    rep = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"][0]
    assert rep["pad_landing"]["data_flops"] == 3 * 4 + 3 * 2 < rep["pad_landing"]["data_flops_single_chain"] == 24
    tcl = (kd / "istations.tcl").read_text()
    assert "is_place_bits {*u_ist_o_0[./]*}" in tcl and "is_place_bits {*u_ist_o_3[./]*}" in tcl
    # cycle check: bit b has d_b stations + the bout flop; latencies() counts flops - 1
    lines = sim(tmp_path, [kd / "t_part_bound.sv"], OUT_TB)
    assert latencies(lines, 6) == [2, 2, 2, 4, 4, 4]


def test_out_pad_landing_epoch_only_stage_and_extension(tmp_path):
    # all bits shallower than K: stage 0 carries no data bit but keeps the K-deep epoch chain (one dead data flop)
    kd = kit(tmp_path, OUT_BOUND)
    r = run_ist(tmp_path, out_plan([[0, 5, 2]]), kd)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert "ot_dp_st #(.W(1)) u_ist_o_0 " in sv and "ot_dp_st #(.W(1)) u_ist_o_1 " in sv
    assert "ot_dp_st #(.W(6)) u_ist_o_2 " in sv and "ot_dp_st #(.W(6)) u_ist_o_3 " in sv
    # extension (peer side of a landing): d_b = 6 > K = 4 -> S = 6, epoch enters at stage 2
    kd2 = kit(tmp_path, OUT_BOUND, "kit2")
    r = run_ist(tmp_path, out_plan([[0, 2, 4], [3, 5, 6]]), kd2)
    assert r.returncode == 0, r.stderr
    sv = (kd2 / "t_part_bound.sv").read_text()
    assert "u_ist_o_5 " in sv and "u_ist_o_6 " not in sv
    assert ".ea(1'b0)" in sv and sv.count(".ea(1'b0)") == 2        # stages 0,1 carry the dead epoch input
    (tmp_path / "x").mkdir()
    lines = sim(tmp_path / "x", [kd2 / "t_part_bound.sv"], OUT_TB)
    assert latencies(lines, 6) == [4, 4, 4, 6, 6, 6]


def test_in_pad_landing_cycles_and_reader_epoch(tmp_path):
    kd = kit(tmp_path, PLAIN_IN)
    plan = in_plan(4, dict(pad_landing=[dict(bus="i", bit_depth=[[0, 1, 1], [2, 3, 3], [4, 5, 4]])]))
    r = run_ist(tmp_path, plan, kd)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    for j, w in enumerate([6, 4, 4, 2]):
        assert f"ot_dp_st #(.W({w})) u_ist_i_{j} " in sv
    assert "assign ye = i_is3_eq;" in sv                             # epoch of stage K-1
    tb = """module tb; reg clk=0, rst_n=0; reg [6:0] i=0; wire [5:0] y; wire ye; integer t=0; reg [31:0] r;
      t_part_bound u(.clk(clk), .rst_n(rst_n), .i(i), .y(y), .ye(ye));
      always #5 clk = ~clk;  initial begin #22 rst_n = 1; end
      always @(negedge clk) begin r = $random; i <= r[6:0]; end
      always @(posedge clk) begin t = t + 1; #1 $display("S %0d %b %b", t, i[5:0], y); end
      initial begin #3000 $finish; end
    endmodule
    """
    lines = sim(tmp_path, [kd / "t_part_bound.sv"], tb)
    assert latencies(lines, 6) == [1, 1, 3, 3, 4, 4]                 # d_b stations + face register


def test_in_pad_landing_with_bind_pads(tmp_path):
    bound = PLAIN_IN.replace("    assign y = i_q;", "    wire [5:0] i_p0_q;\n    wire i_p0_eq;\n"
                             "    ot_dp_st #(.W(6)) u_bin_i_pad0 (.clk(clk), .rst_n(rst_n), .d(i_q), .ea(i_eq), .q(i_p0_q), .eq(i_p0_eq));\n"
                             "    assign y = i_p0_q;").replace("assign ye = i_eq;", "assign ye = i_p0_eq;")
    kd = kit(tmp_path, bound)
    plan = in_plan(3, dict(pad_landing=[dict(bus="i", bit_depth=[[0, 1, 1], [2, 5, 3]])]))
    r = run_ist(tmp_path, plan, kd)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert "u_ist_i_0 " not in sv and "ot_dp_st #(.W(4)) u_ist_i_1 " in sv and "ot_dp_st #(.W(4)) u_ist_i_2 " in sv
    assert "assign ye = i_is2_eq;" in sv


def test_pad_landing_fails_closed(tmp_path):
    kd = kit(tmp_path, OUT_BOUND)
    r = run_ist(tmp_path, out_plan([[0, 2, 2]]), kd)
    assert r.returncode != 0 and "not covered" in r.stderr
    assert (kd / "t_part_bound.sv").read_text() == OUT_BOUND
    r = run_ist(tmp_path, out_plan([[0, 2, 2], [2, 5, 1]]), kd)
    assert r.returncode != 0 and "two runs" in r.stderr
    plan = out_plan([[0, 5, 2]], extra=dict(pad_landing=[dict(bus="o", bit_depth=[[0, 5, 2]]),
                                                         dict(bus="o", bit_depth=[[0, 5, 2]])]))
    r = run_ist(tmp_path, plan, kd)
    assert r.returncode != 0 and "claimed twice" in r.stderr


def test_default_off(tmp_path):
    """no plan key: byte-identical to the plain chain; --no-station-forms: the keys are ignored"""
    a = kit(tmp_path, OUT_BOUND, "a")
    plan = out_plan([[0, 2, 2], [3, 5, 4]])
    plain = json.loads(json.dumps(plan))
    del plain["partition_types"]["t"]["pad_landing"]
    assert run_ist(tmp_path, plain, a).returncode == 0
    b = kit(tmp_path, OUT_BOUND, "b")
    assert run_ist(tmp_path, plan, b, "--no-station-forms").returncode == 0
    assert (a / "t_part_bound.sv").read_text() == (b / "t_part_bound.sv").read_text()
    assert (a / "istations.tcl").read_text() == (b / "istations.tcl").read_text()
    assert "ot_dp_st #(.W(6)) u_ist_o_3 " in (a / "t_part_bound.sv").read_text()


def tree_plan(nodes, readers, k=3, key="readers"):
    return in_plan(k, dict(station_trees=[dict(bus="i", nodes=nodes, **{key: readers})]))


NODES = [dict(id="t0", parent=None, site_um=[100, 0]), dict(id="t1", parent="t0", site_um=[300, 0]),
         dict(id="t2", parent="t1", site_um=[500, 50]), dict(id="t3", parent="t1", site_um=[500, -50])]


def test_in_tree_structure_and_cycles(tmp_path):
    kd = kit(tmp_path, IN_BOUND)
    plan = tree_plan(NODES, [dict(node="t2", core="A"), dict(node="t3", core="B")])
    r = run_ist(tmp_path, plan, kd)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    # owner bits come from the RTL: A reads bits 0-3, B bits 2-5; trunk = union
    assert "ot_dp_st #(.W(6)) u_ist_i_tt0 " in sv and "ot_dp_st #(.W(6)) u_ist_i_tt1 " in sv
    assert "ot_dp_st #(.W(4)) u_ist_i_tt2 " in sv and "ot_dp_st #(.W(4)) u_ist_i_tt3 " in sv
    assert ".din(i_tt2_q[3:0])" in sv and ".din(i_tt3_q[3:0])" in sv and ".ev(i_tt2_eq)" in sv and ".ev(i_tt3_eq)" in sv
    tcl = (kd / "istations.tcl").read_text()
    assert "is_place {*u_ist_i_tt2[./]*} 500 50 ist:i" in tcl
    rep = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"][0]["station_tree"]
    assert rep["data_flops"] == 6 + 6 + 4 + 4 and rep["data_flops_single_chain"] == 18
    tb = """module tb; reg clk=0, rst_n=0; reg [6:0] i=0; wire [3:0] ya, yb; wire ea_o, eb_o; integer t=0; reg [31:0] r;
      t_part_bound u(.clk(clk), .rst_n(rst_n), .i(i), .ya(ya), .yb(yb), .ea_o(ea_o), .eb_o(eb_o));
      always #5 clk = ~clk;  initial begin #22 rst_n = 1; end
      always @(negedge clk) begin r = $random; i <= r[6:0]; end
      always @(posedge clk) begin t = t + 1; #1 $display("S %0d %b %b", t, i[3:0], ya); $display("S %0d %b %b", t, i[5:2], yb); end
      initial begin #3000 $finish; end
    endmodule
    """
    lines = sim(tmp_path, [kd / "t_part_bound.sv"], tb)
    a = [ln for ln in lines][0::2]
    b = [ln for ln in lines][1::2]
    assert latencies(a, 4) == [3] * 4 and latencies(b, 4) == [3] * 4      # face reg + K = 3 stations


def test_in_tree_fail_closed(tmp_path):
    kd = kit(tmp_path, IN_BOUND)
    bad = [dict(NODES[0]), dict(NODES[1]), dict(id="t2", parent="t0", site_um=[500, 50]), dict(NODES[3])]
    r = run_ist(tmp_path, tree_plan(bad, [dict(node="t2", core="A"), dict(node="t3", core="B")]), kd)
    assert r.returncode != 0 and "one bus = one latency" in r.stderr
    assert (kd / "t_part_bound.sv").read_text() == IN_BOUND
    r = run_ist(tmp_path, tree_plan(NODES, [dict(node="t2", core="A", bits=[[0, 2]]), dict(node="t3", core="B")]), kd)
    assert r.returncode != 0 and "outside its declared bits" in r.stderr
    r = run_ist(tmp_path, tree_plan(NODES[:3], [dict(node="t2", core="A")]), kd)      # B's read has no reader
    assert r.returncode != 0 and "not owned by exactly one tree reader" in r.stderr
    r = run_ist(tmp_path, tree_plan(NODES[:3] + [dict(id="t9", parent="zz")],
                                    [dict(node="t2", core="A")]), kd)
    assert r.returncode != 0 and "unknown parent" in r.stderr


OUT_TREE_BOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire [5:0] i_a, output wire [6:0] o);
    wire [2:0] w_A_out;
    wire [2:0] w_B_out;
    assign w_A_out = i_a[2:0];
    assign w_B_out = i_a[5:3];
    ot_dp_ste #(.W(6)) u_bout_o (.clk(clk), .rst_n(rst_n), .d({w_B_out[2:0], w_A_out[2:0]}), .ea(rst_n), .q(o[5:0]), .eq(o[6]));
endmodule
"""


def test_out_tree_merge(tmp_path):
    kd = kit(tmp_path, OUT_TREE_BOUND)
    nodes = [dict(id="r", parent=None, site_um=[10, 0]), dict(id="m", parent="r", site_um=[200, 0]),
             dict(id="la", parent="m", site_um=[400, 0]), dict(id="lb", parent="m", site_um=[400, 400])]
    plan = out_plan([[0, 5, 4]])
    t = plan["partition_types"]["t"]
    del t["pad_landing"]
    t["internal_stations"] = [dict(e, regs_um=e["regs_um"][:3]) for e in t["internal_stations"]]
    t["station_trees"] = [dict(bus="o", nodes=nodes, sources=[dict(node="la", core="A"), dict(node="lb", core="B")])]
    r = run_ist(tmp_path, plan, kd)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert "ot_dp_st #(.W(3)) u_ist_o_tla " in sv and "ot_dp_st #(.W(6)) u_ist_o_tm " in sv and "ot_dp_st #(.W(6)) u_ist_o_tr " in sv
    assert ".d({w_B_out[2:0], w_A_out[2:0]})" not in sv
    lines = sim(tmp_path, [kd / "t_part_bound.sv"], OUT_TB)
    assert latencies(lines, 6) == [3] * 6                                 # 3 stations + bout flop
    # a source not K stations from the face fails closed
    nodes2 = nodes[:3] + [dict(id="lb", parent="r", site_um=[400, 400])]
    t["station_trees"][0]["nodes"] = nodes2
    kd3 = kit(tmp_path, OUT_TREE_BOUND, "kit3")
    r = run_ist(tmp_path, plan, kd3)
    assert r.returncode != 0 and "one bus = one latency" in r.stderr


def test_planner_to_kit_end_to_end(tmp_path):
    """station_tree_plan.plan_tree -> station_trees entry -> kit RTL: every reader K stations from the face"""
    import station_tree_plan as STP
    rows = [dict(conn="bus:i", from_um=[0, 0], to_um=[1000, 0], regs_um=[[250, 0], [500, 0], [750, 0]], bits=4,
                 launch="face bus i", capture="A.din"),
            dict(conn="bus:i", from_um=[0, 0], to_um=[300, 100], regs_um=[[150, 50]], bits=4,
                 launch="face bus i", capture="B.din")]
    res = STP.plan_tree(rows, True, 6)
    st = res["stats"]
    assert st["k"] == 3 and st["trunk_core"] == "A" and st["branch_nodes"] == 1 and not st["violations"]
    ids = {nn["id"]: nn for nn in res["entry"]["nodes"]}
    assert set(ids) == {"t0", "t1", "t2", "B_b0"} and ids["B_b0"]["parent"] == "t1"
    assert {a["core"]: a["node"] for a in res["entry"]["readers"]} == {"A": "t2", "B": "B_b0"}
    # the rewritten rows keep every capture group; B's runs tap -> branch reg -> core
    new = STP.tree_rows(rows, res, True)
    assert new[0] == rows[0] and new[1]["from_um"] == [500, 0] and len(new[1]["regs_um"]) == 1 and new[1]["to_um"] == [300, 100]
    kd = kit(tmp_path, IN_BOUND)
    plan = in_plan(3, dict(station_trees=[dict(bus="i", **res["entry"])]))
    plan["partition_types"]["t"]["internal_stations"] = rows
    r = run_ist(tmp_path, plan, kd)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert ".din(i_tB_b0_q[3:0])" in sv or ".din(i_tB_b0_q" in sv
    rep = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"][0]["station_tree"]
    assert rep["data_flops"] == 6 + 6 + 4 + 4 and rep["data_flops_single_chain"] == 18


def test_planner_flags_unreachable_core():
    import station_tree_plan as STP
    rows = [dict(conn="bus:i", from_um=[0, 0], to_um=[1000, 0], regs_um=[[250, 0], [500, 0], [750, 0]], bits=4,
                 launch="face bus i", capture="A.din"),
            dict(conn="bus:i", from_um=[0, 0], to_um=[0, 2000], regs_um=[[0, 100]], bits=4, launch="face bus i", capture="B.din")]
    res = STP.plan_tree(rows, True, 6)
    assert res["stats"]["violations"] and res["stats"]["violations"][0]["core"] == "B"


def test_schema_accepts_the_new_keys():
    jsonschema = pytest.importorskip("jsonschema")
    import schema
    pt = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    ok = dict(pad_landing=[dict(bus="o", bit_depth=[[0, 5, 2]], stage_sites_um=[[1, 2]])],
              station_trees=[dict(bus="i", nodes=NODES, readers=[dict(node="t2", core="A", bits=[[0, 3], 5])])])
    for key, val in ok.items():
        jsonschema.Draft202012Validator(pt[key]).validate(val)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(pt["pad_landing"]).validate([dict(bus="o", bit_depth=[[0, 5, -1]])])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(pt["station_trees"]).validate([dict(bus="i", nodes=[dict(id="a")])])


def test_derive_cli(tmp_path):
    kd = kit(tmp_path, OUT_BOUND)
    plan = out_plan([[0, 5, 4]])
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istation_forms.py"), "derive", str(pf), "t", "o", str(kd)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    # rows are 500 um long: reach_need = ceil(500/360) - 1 = 1 for both owner cores
    assert out["bit_depth"] == [[0, 5, 1]] and out["owners_resolved"] == 6 and out["data_flops"] == 6


def _census(plan, kd):
    import kit_topology
    return kit_topology.source_census(plan, "t", kd)


def test_kit_topology_accepts_pad_landing_and_tree(tmp_path):
    # out bus pad landing with an extension stage (S = 6 > K = 4)
    kd = kit(tmp_path, OUT_BOUND)
    plan = out_plan([[0, 2, 4], [3, 5, 6]])
    assert run_ist(tmp_path, plan, kd).returncode == 0
    c = _census(plan, kd)
    assert c["problems"] == [] and len(c["emitted_bus_stages"]["bus:o"]) == 6 and c["planned_bus_stages"]["bus:o"] == 4
    # a missing station is still caught
    sv = (kd / "t_part_bound.sv").read_text()
    (kd / "t_part_bound.sv").write_text(sv.replace("u_ist_o_5 ", "u_xx_o_5 "))
    assert _census(plan, kd)["problems"]
    # in bus pad landing with a bind pad
    bound = PLAIN_IN.replace("    assign y = i_q;", "    wire [5:0] i_p0_q;\n    wire i_p0_eq;\n"
                             "    ot_dp_st #(.W(6)) u_bin_i_pad0 (.clk(clk), .rst_n(rst_n), .d(i_q), .ea(i_eq), .q(i_p0_q), .eq(i_p0_eq));\n"
                             "    assign y = i_p0_q;").replace("assign ye = i_eq;", "assign ye = i_p0_eq;")
    kd2 = kit(tmp_path, bound, "kit2")
    plan2 = in_plan(3, dict(pad_landing=[dict(bus="i", bit_depth=[[0, 1, 1], [2, 5, 3]])]))
    assert run_ist(tmp_path, plan2, kd2).returncode == 0
    c = _census(plan2, kd2)
    assert c["problems"] == [] and len(c["emitted_bus_stages"]["bus:i"]) == 3
    # tree
    kd3 = kit(tmp_path, IN_BOUND, "kit3")
    plan3 = tree_plan(NODES, [dict(node="t2", core="A"), dict(node="t3", core="B")])
    assert run_ist(tmp_path, plan3, kd3).returncode == 0
    c = _census(plan3, kd3)
    assert c["problems"] == [] and len(c["emitted_bus_stages"]["bus:i"]) == 4
    # a reader at the wrong depth in the receipt is reported
    man = json.loads((kd3 / "kit_rtl.json").read_text())
    man["kit_istations"][0]["station_tree"]["reader_stations"] = [3, 2]
    (kd3 / "kit_rtl.json").write_text(json.dumps(man))
    assert any("bus latency is 3" in p for p in _census(plan3, kd3)["problems"])
