"""FACE-FLOPS-0130 (2026-11-21): is_place walked every instance of the block for each of ~900 calls (1221 s pre-GPL on
dsdv_slice_c1x_C__t9).  The indexed is_place must place exactly the cells the full scan placed, in the same order, with the
same is_miss entries, including after a DFF is created (is_dff_reset)."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_istations as K  # noqa: E402

TCLSH = shutil.which("tclsh")

MOCK = r'''
set ::placed {}
set ::nid 0; set ::insts {}
proc mk_inst {name master} {
  proc ::inst_$::nid {cmd args} [format {
    switch $cmd { getName { return {%s} } getMaster { return ::mast_%s } default { error "inst $cmd" } }
  } $name $::nid]
  proc ::mast_$::nid {cmd args} [format { if {$cmd eq "getName"} { return {%s} }; error "master $cmd" } $master]
  lappend ::insts ::inst_$::nid; incr ::nid
}
proc ff_blk_obj {cmd args} { if {$cmd eq "getInsts"} { return $::insts }; error "blk $cmd" }
set ff_blk ff_blk_obj; set ff_dbu 1000
proc ff_put_near {i x y} { lappend ::placed [list [$i getName] $x $y]; return [list $x $y] }
set ::env(RESULTS_DIR) $::tmpdir
'''

REF = r'''
proc ref_place {pat x y tag} {
  global ff_blk ff_dbu ref_miss ref_placed
  set hit 0
  foreach i [$ff_blk getInsts] {
    set nm [$i getName]
    if {![string match $pat [string map {\\ {}} $nm]]} continue
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    lappend ref_placed [list $nm $x $y]
    incr hit
  }
  if {!$hit} { lappend ref_miss $pat }
}
set ref_miss {}; set ref_placed {}
'''

NAMES = [("u_ist_a_0/q\\[1\\]$_DFF_P_", "DFFHQNx1"), ("u_ist_a_0/q[2]", "DFFHQNx1"), ("u_ist_a_0.eq$_DFF_", "DFFHQNx1"),
         ("u_ist_a_0/inv", "INVx1"), ("top.u_ist_b_1/q[1]", "DFFHQNx2"), ("xu_ist_a_0/q[1]", "DFFHQNx1"),
         ("u_ist_c_2/q[5]", "DFFHQNx1")]
CALLS = ["*u_ist_a_0[./]q\\[1\\]*", "*u_ist_a_0[./]*", "*u_ist_a_0[./]eq*", "*u_ist_b_1[./]q\\[[0-9]\\]*", "*nothing*",
         "u_ist_c_2[./]*", "[tx]*u_ist_a_0*", "*u_ist_a_0[./]inv*", "?u_ist_a_0*"]


@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
def test_indexed_is_place_equals_full_scan(tmp_path):
    body = [f"set ::tmpdir {{{tmp_path}}}", MOCK, REF]
    for n, m in NAMES:
        body.append(f"mk_inst {{{n}}} {m}")
    body.append(K.TCL_HEAD)
    for c in CALLS:
        body.append(f"ref_place {{{c}}} 1 2 t")
        body.append(f"is_place {{{c}}} 1 2 t")
    # a DFF created after the first call is seen once is_dff_reset ran
    body.append("mk_inst {u_ist_a_0/q[9]} DFFHQNx1; is_dff_reset")
    body.append("ref_place {*u_ist_a_0[./]q\\[9\\]*} 1 2 t; is_place {*u_ist_a_0[./]q\\[9\\]*} 1 2 t")
    body.append("close $is_fh")
    body.append('puts "REFPLACED [llength $ref_placed] [join [lmap e $ref_placed {lindex $e 0}] |]"')
    body.append('puts "NEWPLACED [llength $::placed] [join [lmap e $::placed {lindex $e 0}] |]"')
    body.append('puts "REFMISS [join $ref_miss |]"')
    body.append('puts "NEWMISS [join $is_miss |]"')
    script = tmp_path / "t.tcl"
    script.write_text("\n".join(body))
    out = subprocess.run([TCLSH, str(script)], capture_output=True, text=True, check=True).stdout
    d = {ln.split(" ", 1)[0]: ln.split(" ", 1)[1] for ln in out.splitlines() if ln[:3] in ("REF", "NEW")}
    assert d["REFPLACED"] == d["NEWPLACED"] and int(d["NEWPLACED"].split()[0]) > 6
    assert d["REFMISS"] == d["NEWMISS"] and d["NEWMISS"]
