"""boundary-hold contract stand-ins (CLOCK-RESET/hold 2026-10-25): die_sta liberty + die_trial stand-in conversion."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta as D  # noqa: E402
import die_trial as T  # noqa: E402

BARE = """module p (clk, clk_t1, arst_n, a, y);
  input clk;
  input clk_t1;
  input arst_n;
  input [1:0] a;
  output [0:0] y;
  wire q0;
  wire q1;
  DFFHQNx1_ASAP7_75t_R f0 (.CLK(clk), .D(a[0]), .QN(q0));
  DFFHQNx1_ASAP7_75t_R f1 (.CLK(clk_t1), .D(a[1]), .QN(q1));
  DFFHQNx1_ASAP7_75t_R f2 (.CLK(clk), .D(1'b0), .QN(y[0]));
endmodule
"""


def test_cell_name_roundtrip():
    assert D.bhold_cell(40) == "OT_BHOLD_40p0"
    assert D.bhold_cell(12.5) == "OT_BHOLD_12p5"
    assert D.BHOLD_RE.fullmatch(D.bhold_cell(40))


def test_lib_has_constant_arc():
    t = D.bhold_lib(["OT_BHOLD_40p0"])
    assert "cell (OT_BHOLD_40p0)" in t and 'cell_rise (scalar) { values ("40.0"); }' in t
    assert 'function : "A"' in t and t.count("{") == t.count("}")
    with pytest.raises(ValueError):
        D.bhold_lib(["BUFx2_ASAP7_75t_R"])


def test_convert_bare_standin(tmp_path):
    t, n = T.standin_add_contract(BARE, 40)
    assert n == 2
    assert "OT_BHOLD_40p0 h0 (.A(a[0]), .Y(d0));" in t and ".D(d0)" in t and ".D(d1)" in t
    assert ".D(1'b0)" in t                       # output face flops untouched
    assert "wire d0;" in t and "wire d1;" in t
    p = tmp_path / "x" / "6_final.v"
    p.parent.mkdir()
    p.write_text(t)
    assert D.bhold_cells_used([p]) == {"OT_BHOLD_40p0"}
    nl = D.read_verilog(p)["p"]
    assert sum(1 for c, _, _ in nl.insts if c == "OT_BHOLD_40p0") == 2
    with pytest.raises(ValueError):
        T.standin_add_contract(t, 40)            # already converted


def test_convert_refuses_real_netlist():
    with pytest.raises(ValueError):
        T.standin_add_contract(BARE.replace("endmodule", "  BUFx2_ASAP7_75t_R b0 (.A(a[0]), .Y(y[0]));\nendmodule"), 40)


def test_convert_flopless_standin():
    t, n = T.standin_add_contract("module e (clk, arst_n);\n  input clk;\n  input arst_n;\nendmodule\n", 40)
    assert n == 0 and "endmodule" in t
