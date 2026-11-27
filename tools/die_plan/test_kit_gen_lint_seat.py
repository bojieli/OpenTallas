"""C-RELAY-SEAT-KEYMISS (KV-INT-R3 11-27): a plan relay seat key that no register of the kit's RTL can hold fails gen_lint."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_gen_lint as GL

RTL = """module t_part (input wire clk);
  qkd_rlyi_258s u_pv_u_T1Q0_45_r0 (.clk(clk));
endmodule
"""


def _kit(tmp_path, keys):
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = top\nexport VERILOG_FILES = /work/top.v\n")
    (tmp_path / "top.v").write_text("module top; endmodule\n")
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "t_bound.sv").write_text(RTL)
    (tmp_path / "istations.tcl").write_text("rs_place_all {" + " ".join("{%s} {1.0 2.0}" % k for k in keys) + "}\n")
    return GL.lint(tmp_path, yosys=False)


def test_seat_miss_fails_the_kit(tmp_path):
    r = _kit(tmp_path, ["u_pv_u_T1Q0_45_r0.b[0]", "u_pv_u_T0Q0_45_r0.b[0]"])
    assert r["verdict"] == "FAIL" and r["checks"]["seat_miss"]["verdict"] == "FAIL"
    assert any(i.startswith("seat_miss: SEAT-MISS 1 of 2") for i in r["issues"])


def test_all_seated_passes(tmp_path):
    r = _kit(tmp_path, ["u_pv_u_T1Q0_45_r0.b[0]"])
    assert r["verdict"] == "PASS" and r["checks"]["seat_miss"]["verdict"] == "PASS"


def test_u_y_relay_key_without_relay_fails(tmp_path):
    # hub_Eo shape: the kit RTL holds u_y_ relays, a u_y_ key naming none of them seats nothing
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = top\nexport VERILOG_FILES = /work/top.v\n")
    (tmp_path / "top.v").write_text("module top; endmodule\n")
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "t_bound.sv").write_text("module t_part (input wire clk);\n  relay u_y_xd_seq_g_fan_2_u_fan_rst_n_0_0 (.clk(clk));\nendmodule\n")
    (tmp_path / "istations.tcl").write_text("rs_place_all {{u_y_xd_seq_g_fan_2_u_fan_rst_n_0_0.q} {1.0 2.0} {u_y_xd_astk_EN_g_phys_fault_u_fault_rst_n_0_0.q} {1.0 2.0}}\n")
    r = GL.lint(tmp_path, yosys=False)
    assert r["verdict"] == "FAIL" and any("SEAT-MISS 1 of 2" in i for i in r["issues"])
