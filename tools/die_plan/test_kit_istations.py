"""KV-G3 10-24: kit_istations.py inserts len(regs_um) stations on an in bus, re-points the leaf reader, and writes
FIRM sites for the stations and sited plan cells."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

BOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire [1:0] i_a, output wire q);
    wire [0:0] i_a_q;
    wire i_a_eq;
    ot_dp_st #(.W(1)) u_bin_i_a (.clk(clk), .rst_n(rst_n), .d(i_a[0:0]), .ea(i_a[1]), .q(i_a_q), .eq(i_a_eq));
    qkd_hp_or2 #(.MUT(0)) u_c0 (
        .a(i_a_q[0]),
        .b(1'b0),
        .ck(clk),
        .q(q)
    );
endmodule
"""


def test_inserts_and_sites(tmp_path):
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "t_part_bound.sv").write_text(BOUND)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(kd / "t_part_bound.sv")])))
    plan = dict(partition_types=dict(t=dict(
        buses=[dict(name="i_a", dir="in", width=1, kind="data")],
        contents=[dict(inst="c0", module="qkd_hp_or2", origin_um=[10.0, 20.0], outline_um=[4.0, 4.0])],
        internal_stations=[dict(conn="bus:i_a", from_um=[0, 0], to_um=[10, 20], regs_um=[[3, 0], [6, 0]])])))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert "u_ist_i_a_0 (.clk(clk), .rst_n(rst_n), .d(i_a_q)" in sv
    assert "u_ist_i_a_1 (.clk(clk), .rst_n(rst_n), .d(i_a_is0_q)" in sv
    assert ".a(i_a_is1_q[0])" in sv and ".a(i_a_q[0])" not in sv
    tcl = (kd / "istations.tcl").read_text()
    assert "is_place {*u_ist_i_a_0[./]*} 3 0 ist:i_a" in tcl
    assert "is_place {*u_c0[./]*} 12 22 cell:c0" in tcl
    # re-application with more planned stations extends the chain after the last one (in bus)
    plan["partition_types"]["t"]["internal_stations"][0]["regs_um"].append([8, 0])
    pf.write_text(json.dumps(plan))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    sv = (kd / "t_part_bound.sv").read_text()
    assert "u_ist_i_a_2 (.clk(clk), .rst_n(rst_n), .d(i_a_is1_q)" in sv
    assert ".a(i_a_is2_q[0])" in sv and sv.count("u_ist_i_a_1 (") == 1 and ".q(i_a_is1_q)" in sv
