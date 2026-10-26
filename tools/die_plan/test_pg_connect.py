"""FLOW 10-26 PG: supply binding after every cell-creating step + hard check (pg_connect.tcl).

Real-tool control (OpenROAD, openroad/orfs:latest) on the signed-then-invalidated s8b 6_final.odb
(intel2 autopilot/closed/qwen_compute/qfd_dv_s8x_prog__s8b__6aa7f1fc4d): ot_pg_require_bound FAIL 216/408482
(first ot_ms_m3_leaf dont_touch=1) -> ot_pg_connect_all protected_rebound=108 -> PASS 408482; dont_touch 108 -> 108,
signal ITerm state identical, instance/net counts unchanged; second call rebinds 0; OT_PG_STRICT=1 skips.
Recorded in results/flow_pg_1026/control.txt."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def test_hooks_bind_then_check():
    for hook, where in (("cts_post.tcl", "cts_post"), ("grt_post.tcl", "grt_post")):
        t = (HERE / hook).read_text()
        assert re.search(r"^uplevel #0 \[list source \[file join \$\w+ pg_connect\.tcl\]\]$", t, re.M)
        assert t.index(f"ot_pg_connect_all {where}") < t.index(f"ot_pg_require_bound {where}")
        # the binding is the last cell-changing action of the hook
        tail = t[t.index(f"ot_pg_connect_all {where}"):]
        assert not re.search(r"\b(repair_timing|repair_design|insert_buffer|clock_tree_synthesis)\b", tail)
    hbm = (REPO / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py").read_text()
    assert "ot_pg_connect_all grt_post" in hbm and '"pg_connect.tcl"' in hbm


def test_generators_ship_helper():
    gp = (HERE / "gen_phys.py").read_text()
    assert '"pg_connect.tcl"):' in gp
    assert '"grt_post.tcl", "pg_connect.tcl"' in (HERE / "core_flow.py").read_text()
    import sys
    sys.path.insert(0, str(HERE))
    import signoff
    assert "pg_connect.tcl" in signoff.KIT_TOOL_DEPENDENCIES["cts_post.tcl"]
    assert signoff.KIT_TOOL_DEPENDENCIES["grt_post.tcl"] == ("pg_connect.tcl",)
    assert "pg" in signoff.BLOCKING


TCL_MOCK = r"""
# minimal OpenDB mock: inst u1 (dont_touch, VDD open), u2 (bound), u3 (VSS on a SIGNAL net)
proc mk {name dt nets} { set ::dt($name) $dt; foreach {p n} $nets { set ::net($name/$p) $n } }
mk u1 1 {VDD NULL VSS VSS A n1}
mk u2 0 {VDD VDD VSS VSS A n2}
mk u3 0 {VDD VDD VSS n3 A n3}
set ::role(VDD) POWER; set ::role(VSS) GROUND; set ::role(n1) SIGNAL; set ::role(n2) SIGNAL; set ::role(n3) SIGNAL
proc ord::get_db_block {} { return blk }
proc blk {m args} { switch $m { getInsts { return {i:u1 i:u2 i:u3} } getGlobalConnects { return {r1 r2} } } }
foreach i {u1 u2 u3} {
  proc i:$i {m args} [string map [list @I@ $i] {
    switch $m {
      getName { return @I@ } getMaster { return mst }
      isDoNotTouch { return $::dt(@I@) } setDoNotTouch { set ::dt(@I@) [lindex $args 0]; return }
      findITerm { return t:@I@/[lindex $args 0] }
    } }]
  foreach p {VDD VSS A} { proc t:$i/$p {m args} [string map [list @K@ $i/$p] { if {$::net(@K@) eq "NULL"} {return NULL}; return n:$::net(@K@) }] }
}
foreach n {VDD VSS n1 n2 n3} { proc n:$n {m args} [string map [list @N@ $n] { return $::role(@N@) }] }
proc mst {m args} { switch $m { getMTerms { return {mt:VDD mt:VSS mt:A} } getName { return BUFx2 } } }
proc mt:VDD {m args} { switch $m { getSigType { return POWER } getName { return VDD } } }
proc mt:VSS {m args} { switch $m { getSigType { return GROUND } getName { return VSS } } }
proc mt:A {m args} { switch $m { getSigType { return SIGNAL } getName { return A } } }
proc global_connect {} {
  # native behaviour: dont_touch instances are skipped (ODB-0383); others get rule nets on open VDD/VSS
  foreach i {u1 u2 u3} { if {$::dt($i)} { lappend ::skipped $i; continue }
    if {$::net($i/VDD) eq "NULL"} { set ::net($i/VDD) VDD }; if {$::net($i/VSS) eq "NULL"} { set ::net($i/VSS) VSS } }
}
source @HELPER@
puts "R1 [catch {ot_pg_require_bound t0} m] $m"
set ::net(u3/VSS) VSS
puts "R2 [catch {ot_pg_require_bound t1} m] $m"
puts "C1 [ot_pg_connect_all t2] dt=$::dt(u1) vdd=$::net(u1/VDD) a=$::net(u1/A)"
puts "R3 [catch {ot_pg_require_bound t3} m] $m"
"""


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_tcl_mock_semantics(tmp_path):
    s = tmp_path / "t.tcl"
    s.write_text("namespace eval ord {}\n" + TCL_MOCK.replace("@HELPER@", str(HERE / "pg_connect.tcl")))
    out = subprocess.run(["tclsh", str(s)], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    lines = dict(ln.split(" ", 1) for ln in out.stdout.splitlines() if ln[:2] in ("R1", "R2", "C1", "R3"))
    assert lines["R1"].startswith("1 OT_PG_OPEN t0 open_pg_terms=2 of 6 first=u1(BUFx2 dont_touch=1)")  # wrong-type net counts
    assert lines["R2"].startswith("1 OT_PG_OPEN t1 open_pg_terms=1")
    assert lines["C1"] == "1 dt=1 vdd=VDD a=n1"           # rebound, re-protected, signal pin untouched
    assert lines["R3"].startswith("0 ")
