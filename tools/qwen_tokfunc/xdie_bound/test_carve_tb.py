"""tests for carve_tb.py: python3 -m pytest tools/qwen_tokfunc/xdie_bound/test_carve_tb.py
Generation is always checked; with Verilator on PATH (or $OT_VERILATOR) a 2-partition toy carve is simulated."""
import json, os, shutil, subprocess, sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import carve_tb  # noqa: E402

CARVE = {"name": "toy_carve", "top_sha256": "0",
         "inputs": {"clk_core": {"width": 1, "lane": None}, "rstw_a_rst_o_0": {"width": 1, "lane": None},
                    "x_in": {"width": 72, "lane": "l_in"}, "x_idle": {"width": 3, "lane": "l_idle"}},
         "outputs": {"y_out": {"width": 72, "lane": "l_out"}}}
RESET = {"parts": {"a": {"release": 3}}}
TOY = """module toy_carve(input wire clk_core, input wire rstw_a_rst_o_0, input wire [71:0] x_in, input wire [2:0] x_idle,
                     output reg [71:0] y_out);
  always @(posedge clk_core or negedge rstw_a_rst_o_0) if (!rstw_a_rst_o_0) y_out <= 72'd0; else y_out <= x_in + {69'd0, x_idle};
endmodule
"""


def test_generate_classifies_ports():
    t = carve_tb.emit(CARVE, RESET)
    assert "wire rstw_a_rst_o_0 = (cyc >= rst_cyc + 3);" in t
    assert "reg [71:0] x_in = 72'd0;" in t and "CARVE_TB_IDLE x_idle" in t
    assert ".y_out(y_out)" in t and "toy_carve dut" in t


def test_missing_release_fails():
    with pytest.raises(SystemExit):
        carve_tb.emit(CARVE, {"parts": {}})


VL = os.environ.get("OT_VERILATOR") or shutil.which("verilator")


@pytest.mark.skipif(not VL, reason="no verilator")
def test_toy_sim(tmp_path):
    (tmp_path / "toy.sv").write_text(TOY)
    (tmp_path / "tb.sv").write_text(carve_tb.emit(CARVE, RESET))
    (tmp_path / "stim").mkdir(); (tmp_path / "exp").mkdir()
    (tmp_path / "stim" / "x_in.ev").write_text("10 ffffffffffffffffff\n20 5\n")
    # reset releases at 4+3=7; x_in applied before edge 10 -> y_out = x_in after edge 10, seen at edge 11
    (tmp_path / "exp" / "y_out.ev").write_text("11 ffffffffffffffffff\n21 5\n25 6\n")
    subprocess.run([VL, "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "--top-module", "tb_toy_carve", "-Mdir", "obj",
                    "tb.sv", "toy.sv"], cwd=tmp_path, check=True, capture_output=True)
    r = subprocess.run(["obj/Vtb_toy_carve", "+cycles=30"], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert "CARVE_TB_IDLE x_idle" in r.stdout
    assert "checks=3 mismatches=1" in r.stdout, r.stdout     # cycle 25 expects 6, got 5 -> caught
    tr = (tmp_path / "carve_trace.txt").read_text().split("\n")
    assert tr[0].startswith("11 y_out ffffffffffffffffff") and tr[1].startswith("21 y_out "), tr
