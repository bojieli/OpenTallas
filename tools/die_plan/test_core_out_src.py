"""core_out_src.tcl (KIT-NK-SRCPIN 11-11, QC cbn_q11 NK output chains): after core_out_land.tcl lands r[0] at a hard-core
output pin, the later stages of a single-load register chain into a hard-core INPUT stay FIRM beside r[0] when the
source -> destination L route crosses exactly one core and is within reach; 0-crossing, >= 2-crossing, out-of-reach and
fan-out chains stay with GPL.  Opt-in through plan budgets.core_out_src_types (gen_phys) only.
The OpenROAD cases need docker + openroad/orfs:asap7lock (skipped otherwise).
python3 -m pytest -q tools/die_plan/test_core_out_src.py"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as GP  # noqa: E402
import schema as S  # noqa: E402

FF, RAM = "DFFHQNx1_ASAP7_75t_R", "fakeram7_64x21"

# A (300,300) drives five chains from W-face rd_out pins (y 300.6 .. 301.4); every wd_in[0] / wd_in[1] is a W-face pin
#   c0 -> B (100,300): route A -> B passes through B only                 = 1 crossing  -> stages s01 s02 at the source
#   c1 -> C (700,600): VH route reaches C's W face from the west           = 0 crossings -> GPL
#   c2 -> D (40,300):  passes through B and D                              = 2 crossings -> GPL (S2 floorplan item)
#   c3 -> E (1400,300): through A only, but 1100 um                        = beyond reach -> GPL
#   c4 -> s41 -> {B.wd_in[1], flop}: the chain fans out                    = not a chain -> GPL
NETLIST = f"""module t(input wire clk, output wire y0);
  wire [20:0] q; wire l0, s01q, s02q, l1, s11q, l2, s21q, l3, s31q, l4, s41q;
  {RAM} u_a (.clk(clk), .rd_out(q));
  {FF} l0_r (.CLK(clk), .D(q[3]), .QN(l0));
  {FF} s01 (.CLK(clk), .D(l0), .QN(s01q));
  {FF} s02 (.CLK(clk), .D(s01q), .QN(s02q));
  {RAM} u_b (.clk(clk), .wd_in({{19'b0, s41q, s02q}}));
  {FF} l1_r (.CLK(clk), .D(q[4]), .QN(l1));
  {FF} s11 (.CLK(clk), .D(l1), .QN(s11q));
  {RAM} u_c (.clk(clk), .wd_in({{20'b0, s11q}}));
  {FF} l2_r (.CLK(clk), .D(q[5]), .QN(l2));
  {FF} s21 (.CLK(clk), .D(l2), .QN(s21q));
  {RAM} u_d (.clk(clk), .wd_in({{20'b0, s21q}}));
  {FF} l3_r (.CLK(clk), .D(q[6]), .QN(l3));
  {FF} s31 (.CLK(clk), .D(l3), .QN(s31q));
  {RAM} u_e (.clk(clk), .wd_in({{20'b0, s31q}}));
  {FF} l4_r (.CLK(clk), .D(q[7]), .QN(l4));
  {FF} s41 (.CLK(clk), .D(l4), .QN(s41q));
  {FF} f41 (.CLK(clk), .D(s41q), .QN(y0));
endmodule
"""

TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $P/asap7_tech_1x_201209.lef
read_lef $P/asap7sc7p5t_28_R_1x_220121a.lef
read_lef $P/fakeram7_64x21.lef
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area "0 0 1600 1200" -core_area "5 5 1595 1195" -site asap7sc7p5t
set blk [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set at {u_a {300 300} u_b {100 300} u_c {700 600} u_d {40 300} u_e {1400 300}}
foreach i [$blk getInsts] {
  if {[[$i getMaster] isBlock]} {
    lassign [dict get $at [$i getName]] x y
    $i setLocation [expr {$x * $u}] [expr {$y * $u}]; $i setPlacementStatus FIRM
  } else { $i setLocation [expr {800 * $u}] [expr {800 * $u}]; $i setPlacementStatus PLACED }
}
set ::env(RESULTS_DIR) /w
source /w/core_out_land.tcl
if {[file exists /w/core_out_src.tcl]} { source /w/core_out_src.tcl }
foreach i [$blk getInsts] {
  if {[[$i getMaster] isBlock]} continue
  lassign [$i getLocation] x y
  puts "CHK [$i getName] [expr {$x / double($u)}] [expr {$y / double($u)}] [$i getPlacementStatus]"
}
"""


def _run(land_on, with_src):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "t.v").write_text(NETLIST)
        (Path(d) / "t.tcl").write_text(TCL)
        shutil.copy(HERE / "core_out_land.tcl", d)
        if with_src:
            shutil.copy(HERE / "core_out_src.tcl", d)
        cmd = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl; chmod -R a+rwX /w"
        env = ["-e", "OT_CORE_OUT_LAND=1"] if land_on else []
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", *env, "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        files = {n: (Path(d) / n).read_text() for n in ("ot_core_out_land.txt", "ot_core_out_src.tsv")
                 if (Path(d) / n).exists()}
        return r.stdout, files


def _pos(out):
    return {n: (float(x), float(y), st) for n, x, y, st in re.findall(r"CHK (\S+) ([0-9.]+) ([0-9.]+) (\w+)", out)}


PARK = (800.0, 800.0, "PLACED")


def test_one_crossing_chain_stages_at_source():
    if not shutil.which("docker"):
        pytest.skip("no docker")
    out, files = _run(True, True)
    assert "OT_CORE_OUT_SRC placed 2 chain stages FIRM at their source pins on 1 one-crossing" in out, out[-3000:]
    assert "1 without a core crossing, 1 with >= 2 crossings" in out and "1 beyond 900.0 um" in out, out[-3000:]
    pos = _pos(out)
    lx, ly, lst = pos["l0_r"]
    assert lst == "FIRM" and abs(lx - 300) < 40 and abs(ly - 300.6) < 40, pos["l0_r"]
    for n in ("s01", "s02"):
        x, y, st = pos[n]
        assert st == "FIRM" and abs(x - lx) + abs(y - ly) < 30, (n, pos[n], pos["l0_r"])
    for n in ("s11", "s21", "s31", "s41", "f41"):
        assert pos[n] == PARK, (n, pos[n])
    land = files["ot_core_out_land.txt"].split()
    assert "s01" in land and "s02" in land and "s11" not in land      # released before DPL with the landing flops
    rows = {r.split("\t")[0]: r.split("\t") for r in files["ot_core_out_src.tsv"].splitlines()[1:]}
    assert rows["l0_r"][4:] == ["1", rows["l0_r"][5], "src"] and rows["l0_r"][2] == "u_b/wd_in[0]"
    assert rows["l1_r"][-1] == "skip_no_crossing" and rows["l2_r"][-1] == "skip_multi_crossing"
    assert rows["l3_r"][-1] == "skip_reach" and rows["l4_r"][-1] == "skip_shape"


def test_landing_only_unchanged_without_src():
    """a kit without core_out_src.tcl (no plan key): core_out_land.tcl alone, chain stages stay with GPL"""
    if not shutil.which("docker"):
        pytest.skip("no docker")
    out, files = _run(True, False)
    assert "OT_CORE_OUT_SRC" not in out and "ot_core_out_src.tsv" not in files
    pos = _pos(out)
    assert pos["l0_r"][2] == "FIRM"
    for n in ("s01", "s02", "s11", "s21", "s31", "s41", "f41"):
        assert pos[n] == PARK, (n, pos[n])


def test_src_without_landing_is_noop():
    if not shutil.which("docker"):
        pytest.skip("no docker")
    out, _ = _run(False, True)
    assert "OT_CORE_OUT_SRC skipped" in out
    assert all(p == PARK for p in _pos(out).values())


def test_plan_key_opt_in(monkeypatch):
    monkeypatch.delenv("OT_CORE_OUT_SRC", raising=False)
    monkeypatch.delenv("OT_CORE_OUT_LAND", raising=False)
    t = "cbn_q11__cl49ae4555"
    assert not GP._core_out_src({}, t) and not GP._core_out_land({}, t)            # absent key: unchanged kits
    assert not GP._core_out_src({"core_out_src_types": ["cbn_q11"]}, t)           # exact names only
    assert GP._core_out_src({"core_out_src_types": [t]}, t)
    assert GP._core_out_land({"core_out_src_types": [t]}, t)                     # src implies landing
    assert GP._core_out_land({"core_out_land_types": [t]}, t) and not GP._core_out_src({"core_out_land_types": [t]}, t)
    monkeypatch.setenv("OT_CORE_OUT_SRC", "1")
    assert GP._core_out_src({}, t) and GP._core_out_land({}, t)


def test_install_appends_hook(tmp_path):
    (tmp_path / "face_flops.tcl").write_text("# base hook\n")
    GP.core_out_src_install(tmp_path)
    assert (tmp_path / "core_out_src.tcl").read_bytes() == (HERE / "core_out_src.tcl").read_bytes()
    body = (tmp_path / "face_flops.tcl").read_text()
    assert body.startswith("# base hook\n") and body.rstrip().endswith(GP.CORE_OUT_SRC_HOOK)


def test_gen_phys_wires_the_key():
    src = (HERE / "gen_phys.py").read_text()
    assert "macros and _core_out_land(P.budgets, tn) else []" in src
    assert re.search(r"if macros and _core_out_src\(P\.budgets, tn\):\n(\s+#.*\n)*\s+core_out_src_install\(kd\)", src)


def test_schema_key():
    props = S.SCHEMA["properties"]["budgets"]["properties"]
    assert props["core_out_src_types"]["type"] == "array" and props["core_out_src_types"]["uniqueItems"]
    jsonschema = pytest.importorskip("jsonschema")
    v = jsonschema.Draft202012Validator(S.SCHEMA["properties"]["budgets"])
    assert not list(v.iter_errors({"core_out_src_types": ["cbn_q11__cl49ae4555"]}))
    assert list(v.iter_errors({"core_out_src_types": "cbn_q11__cl49ae4555"}))
    assert list(v.iter_errors({"core_out_src_types": ["a", "a"]}))
