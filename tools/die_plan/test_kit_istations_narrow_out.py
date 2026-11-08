"""DIE-HBM-90-TSTRAP 11-07: HBM NE_io/NW_io L52_o plan 612 vs bound face 610.

The bind's kit-rtl wrapper ties the 2 plan bits with no bound driver to 0 (kit_rtl.json spare_out_bits + narrow_buses);
kit_istations accepted that only for inputs and stopped both io types.  An output is accepted only with the exact
narrow mapping and a spare_out_bits row of plan-bound bits; stations are sized to the real face register.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

BOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire a, output wire [1:0] o_a);
    ot_dp_st #(.W(1)) u_bout_o_a (.clk(clk), .rst_n(rst_n), .d(a), .ea(rst_n), .q(o_a[0:0]), .eq(o_a[1]));
endmodule
"""


@pytest.mark.parametrize("case", ["tied", "no_spare", "wrong_bits", "no_narrow", "input_rule_kept"])
def test_narrow_output_needs_exact_spare_tie(tmp_path, case):
    plan = dict(partition_types=dict(t=dict(
        buses=[dict(name="o_a", dir="out", width=3, kind="data")],
        internal_stations=[dict(conn="bus:o_a", regs_um=[[3, 0]])])))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan))
    kd = tmp_path / "kit"
    kd.mkdir()
    bound = kd / "t_part_bound.sv"
    bound.write_text(BOUND)
    man = dict(bound_module="t_part_bound", files=[str(bound)],
               narrow_buses=[dict(port="o_a", plan=3, bound=1)], spare_out_bits=[dict(port="o_a", bits=2)])
    if case == "no_spare":
        man["spare_out_bits"] = []
    if case == "wrong_bits":
        man["spare_out_bits"] = [dict(port="o_a", bits=1)]
    if case == "no_narrow":
        man["narrow_buses"] = []
    if case == "input_rule_kept":
        # an input bus still needs the dead-input proof; spare_out_bits does not authorise it
        plan["partition_types"]["t"]["buses"][0]["dir"] = "in"
        pf.write_text(json.dumps(plan))
    (kd / "kit_rtl.json").write_text(json.dumps(man))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                       capture_output=True, text=True)
    if case == "tied":
        assert r.returncode == 0, r.stderr
        report = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"][0]
        assert (report["plan_width"], report["bound_width"]) == (3, 1)
        assert "ot_dp_st #(.W(3))" not in bound.read_text()
        assert json.loads(pf.read_text()) == plan
    else:
        assert r.returncode != 0
        assert "plan width 3 != face width 1" in r.stderr
        assert bound.read_text() == BOUND
