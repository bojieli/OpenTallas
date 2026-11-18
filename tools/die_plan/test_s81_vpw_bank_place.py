"""FIX-S81-VPW 11-17: s81_vpw_bank.tcl on a mock ODB in tclsh (no OpenROAD).
(1) a block with no VP SRAMs and no VPW FFs (col types) is skipped with a no-op clock record;
(2) banks ~420 um apart (S81 leaf t10/t74): FFs go FIRM next to the nearest bank, not >100 um away at the centroid."""
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = Path(__file__).with_name("s81_vpw_bank.tcl")

MOCK = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1000}
proc obj {name body} {proc $name {m args} "switch -- \$m {$body default {error \"\$m\"}}"}
set ::placed {}
obj core {xMin {return 0} yMin {return 0} xMax {return 1000000} yMax {return 1000000}}
obj site {getWidth {return 54} getHeight {return 2700}}
obj sram {isBlock {return 1} getName {return SRAM} getWidth {return 10000} getHeight {return 10000}}
obj dff {isBlock {return 0} getName {return DFFHQNx1} getWidth {return 1000} getHeight {return 2700}}
proc mkbox {n x0 y0 x1 y1} {obj $n "xMin {return $x0} yMin {return $y0} xMax {return $x1} yMax {return $y1}"}
proc mkinst {n name master bx st} {
  obj $n "getMaster {return $master} getName {return {$name}} getBBox {return $bx} getPlacementStatus {return $st}
          setPlacementStatus {} setOrient {} setLocation {lappend ::placed \[list {$name} {*}\$args\]}"
}
set ::insts {}; set ::rows {}
proc mkrows {y0 y1} {
  for {set y $y0; set k 0} {$y < $y1} {incr y 2700; incr k} {
    mkbox rb$k 0 $y 1000000 [expr {$y+2700}]
    obj row$k "getOrigin {return {0 $y}} getSite {return site} getBBox {return rb$k} getOrient {return R0}"
    lappend ::rows row$k
  }
}
mkbox tb 500000 500000 500100 500100
obj bt0 {getName {return clk_t1} getBBox {return tb}}
proc blk {m} {
  switch -- $m {getCoreArea {return core} getInsts {return $::insts} getBlockages {return {}}
                getRows {return $::rows} getBTerms {return bt0}}
}
rename open _open
proc open {p args} {_open [string map [list /work $::env(VB_DIR)] $p] {*}$args}
'''

FAR = r'''
mkbox b0box 0 0 10000 10000
mkbox b1box 0 420000 10000 430000
mkinst b0 u_bound.u_u_lf4_u_vp_u_b0 sram b0box FIRM
mkinst b1 u_bound.u_u_lf4_u_vp_u_b1 sram b1box FIRM
lappend ::insts b0 b1
for {set i 0} {$i < 6} {incr i} {
  mkbox fb$i 0 0 0 0
  mkinst f$i "u_bound.u_u_lf4_u_vp_g_wr1_u_w.wa0\[$i\]\$_DFF_P_" dff fb$i PLACED
  lappend ::insts f$i
}
mkrows 0 480000
'''


def _run(tmp_path, body):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    src = MOCK + body + f"\nsource {TCL}\nputs \"PLACED [llength $::placed] $::placed\"\n"
    src = "if {[catch {\n" + src + "\n} e]} {puts stderr $e; exit 1}\n"
    r = subprocess.run(["tclsh"], input=src, text=True, capture_output=True, env={"VB_DIR": str(tmp_path)})
    return r


def test_block_without_vp_macros_is_skipped(tmp_path):
    r = _run(tmp_path, "mkrows 0 27000\n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_VPW_BANK SKIP" in r.stdout and "PLACED 0" in r.stdout
    clk = (tmp_path / "vpw_bank_clock.tcl").read_text()
    assert "OT_TAP_GROUP" not in clk


def test_far_banks_place_at_nearest_bank(tmp_path):
    r = _run(tmp_path, FAR)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PLACED 6" in r.stdout and "WARN" not in r.stdout, r.stdout
    rows = [ln.split("\t") for ln in (tmp_path / "vpw_bank_sites.tsv").read_text().splitlines()[1:]]
    assert len(rows) == 6 and max(float(x[3]) for x in rows) <= 100.0
    assert "OT_TAP_GROUP_FIXED" in (tmp_path / "vpw_bank_clock.tcl").read_text()


def test_vp_block_with_banks_but_no_ffs_still_fails(tmp_path):
    body = FAR.replace("for {set i 0} {$i < 6}", "for {set i 0} {$i < 0}")
    r = _run(tmp_path, body)
    assert r.returncode != 0 and "no VPW FFs" in r.stderr + r.stdout
