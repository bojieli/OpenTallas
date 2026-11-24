"""KV-PV-CAP 11-23: kit_dly_ap.py (alternating-polarity ot_dp_dly lines, kit RTL post-pass, opt-in plan dly_alt_pol)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_dly_ap as ka  # noqa: E402

DLY = """
module ot_dp_dly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    assign q = r[D-1];
endmodule
module ot_dp_dly_keep #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    (* keep *) reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    assign q = r[D-1];
endmodule
"""


def bound(depths=(1, 2, 3, 4, 5, 8)):
    lines = ["module t_bound (input wire clk, input wire [2:0] d, output wire [2:0] q_k"]
    lines += [f", output wire [2:0] q{n}" for n in depths] + [");"]
    for n in depths:
        lines.append(f"    ot_dp_dly #(.W(3), .D({n})) u_l{n} (.clk(clk), .d(d), .q(q{n}));  // landing pad trunk")
    lines.append("    ot_dp_dly_keep #(.W(3), .D(4)) u_k (.clk(clk), .d(d), .q(q_k));")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def test_cfg_of():
    assert ka.cfg_of({}) is None and ka.cfg_of({"dly_alt_pol": False}) is None
    assert ka.cfg_of({"dly_alt_pol": True}) == {"min_d": 2}
    assert ka.cfg_of({"dly_alt_pol": {"min_d": 4}}) == {"min_d": 4}


def test_apply_selects_d2_plain_only():
    out, st = ka.apply(bound())
    assert st["selected"] == 5 and st["kept_d1"] == 1 and st["keep_cells"] == 1
    assert re.search(r"^\s*ot_dp_dly #\(\.W\(3\), \.D\(1\)\) u_l1\b", out, re.M)
    assert re.search(r"^\s*ot_dp_dly_keep #\(\.W\(3\), \.D\(4\)\) u_k\b", out, re.M)
    for n in (2, 3, 4, 5, 8):
        assert re.search(rf"^\s*ot_dp_dly_ap #\(\.W\(3\), \.D\({n}\)\) u_l{n} \(", out, re.M)
    assert out.count("module ot_dp_dly_ap") == 1
    assert st["inv_removed_est"] == 3 * (2 + 2 + 4 + 4 + 8)
    with pytest.raises(ValueError):
        ka.apply(out)
    _, st4 = ka.apply(bound(), min_d=4)
    assert st4["selected"] == 3


def test_apply_kit_in_place(tmp_path):
    f = tmp_path / "t_bound.sv"
    f.write_text(bound())
    (tmp_path / "other.sv").write_text("module other; endmodule\n")
    rec = ka.apply_kit(tmp_path, {"min_d": 2})
    assert list(rec) == ["t_bound.sv"] and rec["t_bound.sv"]["selected"] == 5
    assert "ot_dp_dly_ap" in f.read_text() and not list(tmp_path.glob("*.dap_tmp"))


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_cycle_exact_iverilog(tmp_path):
    """ap file vs the bound file: every output equal on every cycle for random d (after the D-cycle fill)"""
    ref = bound().replace("module t_bound", "module ref_bound")
    dut, _ = ka.apply(bound())
    tb = """
module tb; reg clk = 0; reg [2:0] d = 0; integer k, err = 0;
  wire [2:0] a1,a2,a3,a4,a5,a8,ak, b1,b2,b3,b4,b5,b8,bk;
  ref_bound r (.clk(clk), .d(d), .q_k(ak), .q1(a1), .q2(a2), .q3(a3), .q4(a4), .q5(a5), .q8(a8));
  t_bound   u (.clk(clk), .d(d), .q_k(bk), .q1(b1), .q2(b2), .q3(b3), .q4(b4), .q5(b5), .q8(b8));
  initial begin
    for (k = 0; k < 400; k = k + 1) begin
      d = $random; #1 clk = 1; #1 clk = 0;
      if (k > 10 && {a1,a2,a3,a4,a5,a8,ak} !== {b1,b2,b3,b4,b5,b8,bk}) err = err + 1;
    end
    if (err) $display("FAIL %0d", err); else $display("PASS");
    $finish;
  end
endmodule
"""
    (tmp_path / "a.sv").write_text(DLY + ref + dut + tb)
    exe = tmp_path / "a.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(tmp_path / "a.sv")], check=True)
    out = subprocess.run(["vvp", str(exe)], capture_output=True, text=True, check=True).stdout
    assert "PASS" in out, out
