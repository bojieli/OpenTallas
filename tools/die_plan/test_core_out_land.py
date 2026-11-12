"""core_out_land.tcl (DIE-HEAD-69 11-05, hd_tile flt_q): a flop that is the only leaf load of a hard-core output pin and
whose Q has one leaf load sits FIRM next to that pin; broadcast pins and fan-out flops stay with GPL; off unless
OT_CORE_OUT_LAND=1.  Needs docker + openroad/orfs:asap7lock (skipped otherwise).
python3 -m pytest -q tools/die_plan/test_core_out_land.py"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FF, INV = "DFFHQNx1_ASAP7_75t_R", "INVx1_ASAP7_75t_R"

NETLIST = f"""module t(input wire clk, output wire y0, output wire y1, output wire y2, output wire y3);
  wire [20:0] q; wire l0, h0, b0, b1, f0, ib;
  fakeram7_64x21 u_m (.clk(clk), .rd_out(q));
  {INV} ib0 (.A(q[0]), .Y(ib));
  {FF} land0 (.CLK(clk), .D(ib), .QN(l0));
  {FF} hop0 (.CLK(clk), .D(l0), .QN(y0));
  {FF} bc0 (.CLK(clk), .D(q[1]), .QN(y1));
  {FF} bc1 (.CLK(clk), .D(q[1]), .QN(b1));
  {FF} fo0 (.CLK(clk), .D(q[2]), .QN(f0));
  {FF} fo1 (.CLK(clk), .D(f0), .QN(y2));
  {FF} fo2 (.CLK(clk), .D(f0), .QN(y3));
endmodule
"""

TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $P/asap7_tech_1x_201209.lef
read_lef $P/asap7sc7p5t_28_R_1x_220121a.lef
read_lef $P/fakeram7_64x21.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 1200 1200" -core_area "5 5 1195 1195" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
foreach i [$blk getInsts] {
  if {[[$i getMaster] isBlock]} { $i setLocation [expr {300 * $u}] [expr {300 * $u}]; $i setPlacementStatus FIRM
  } else { $i setLocation [expr {1000 * $u}] [expr {1000 * $u}]; $i setPlacementStatus PLACED }
}
set ::env(RESULTS_DIR) /w
source /w/core_out_land.tcl
set it [[$blk findInst u_m] findITerm {rd_out[0]}]
lassign [$it getAvgXY] ok px py
puts "PIN [expr {$px / double($u)}] [expr {$py / double($u)}]"
foreach i [$blk getInsts] {
  if {[[$i getMaster] isBlock]} continue
  lassign [$i getLocation] x y
  puts "CHK [$i getName] [expr {$x / double($u)}] [expr {$y / double($u)}] [$i getPlacementStatus]"
}
"""


def _run(env_on):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(NETLIST)
        (Path(d) / "t.tcl").write_text(TCL)
        shutil.copy(HERE / "core_out_land.tcl", d)
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        env = ["-e", "OT_CORE_OUT_LAND=1"] if env_on else []
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", *env, "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        return r.stdout


def _pos(out):
    return {n: (float(x), float(y), st) for n, x, y, st in re.findall(r"CHK (\S+) ([0-9.]+) ([0-9.]+) (\w+)", out)}


def test_landing_flop_at_pin():
    if not shutil.which("docker"):
        pytest.skip("no docker")
    out = _run(True)
    assert "OT_CORE_OUT_LAND placed 1 core-output landing flops" in out, out[-3000:]
    px, py = map(float, re.search(r"PIN ([0-9.]+) ([0-9.]+)", out).groups())
    pos = _pos(out)
    x, y, st = pos["land0"]
    assert st == "FIRM" and abs(x - px) + abs(y - py) < 30, (pos["land0"], px, py)
    for n in ("hop0", "bc0", "bc1", "fo0", "fo1", "fo2"):    # broadcast pin / fan-out flop / second hop: GPL's
        assert pos[n] == (1000.0, 1000.0, "PLACED"), (n, pos[n])


def test_off_by_default():
    if not shutil.which("docker"):
        pytest.skip("no docker")
    out = _run(False)
    assert "OT_CORE_OUT_LAND" not in out
    assert all(p == (1000.0, 1000.0, "PLACED") for p in _pos(out).values())


def test_plan_budget_key_schema():
    """CPL-QC-NK-OUT 11-11: budgets.core_out_land_types (the plan opt-in gen_phys reads) is a schema-valid list of names"""
    import sys
    sys.path.insert(0, str(HERE))
    import schema
    assert schema.SCHEMA["properties"]["budgets"]["properties"]["core_out_land_types"]["type"] == "array"
    jsonschema = pytest.importorskip("jsonschema")
    v = jsonschema.Draft202012Validator(schema.SCHEMA["properties"]["budgets"])
    assert not list(v.iter_errors({"core_out_land_types": ["cbn_q11__cl49ae4555", "cbf_q11"]}))
    assert list(v.iter_errors({"core_out_land_types": "cbf_q11"}))
    assert list(v.iter_errors({"core_out_land_types": ["cbf_q11", "cbf_q11"]}))
    assert list(v.iter_errors({"core_out_land_type": ["cbf_q11"]}))


def test_gen_phys_reads_plan_key():
    """gen_phys emits the config.mk opt-in from the same plan key the schema now admits"""
    src = (HERE / "gen_phys.py").read_text()
    assert 'P.budgets.get("core_out_land_types")' in src and "export OT_CORE_OUT_LAND = 1" in src
