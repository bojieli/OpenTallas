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


def _run(tmp_path, body, env=None):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    src = MOCK + body + f"\nsource {TCL}\nputs \"PLACED [llength $::placed] $::placed\"\n"
    src = "if {[catch {\n" + src + "\n} e]} {puts stderr $e; exit 1}\n"
    r = subprocess.run(["tclsh"], input=src, text=True, capture_output=True, env={"VB_DIR": str(tmp_path), **(env or {})})
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


XR_FAR = r'''
mkbox b0box 0 0 10000 10000
mkbox b1box 0 420000 10000 430000
mkbox vsbox 900000 0 950000 50000
mkinst b0 u_bound.u_u_lf4_u_vp_u_b0 sram b0box FIRM
mkinst b1 u_bound.u_u_lf4_u_vp_u_b1 sram b1box FIRM
mkinst vs u_bound.u_u_lf4_u_vs sram vsbox FIRM
lappend ::insts b0 b1 vs
for {set i 0} {$i < 4} {incr i} {
  mkbox xb$i 0 0 0 0
  mkinst x$i "u_bound.u_u_lf4_u_vp_g_wr1_u_w.g_xr.wa_q\[$i\]\$_DFF_P_" dff xb$i PLACED
  lappend ::insts x$i
}
for {set i 0} {$i < 2} {incr i} {
  mkbox fb$i 0 0 0 0
  mkinst f$i "u_bound.u_u_lf4_u_vp_g_wr1_u_w.wa0\[$i\]\$_DFF_P_" dff fb$i PLACED
  lappend ::insts f$i
}
mkrows 0 480000
'''


def test_xr_mid_places_cohort_on_the_vs_to_bank_line(tmp_path):
    """XR-MID-1 (S81-GEOM-OPUS 11-18): VS 890 um from the near bank, MIN 600 / D 500 -> the 4 g_xr flops go to
    min(500, 890/2) = 445 um from VS (x ~455 um), the 2 other write-port flops stay at the bank; the tap group
    excludes g_xr"""
    r = _run(tmp_path, XR_FAR, {"OT_S81_VPW_XR_MID": "600:500"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_VPW_XR_MID placed 4 of 4" in r.stdout, r.stdout
    mid = [ln.split("\t") for ln in (tmp_path / "vpw_xr_mid_sites.tsv").read_text().splitlines()[1:]]
    assert len(mid) == 4 and all(400 <= float(x[1]) <= 510 for x in mid), mid
    bank = [ln.split("\t") for ln in (tmp_path / "vpw_bank_sites.tsv").read_text().splitlines()[1:]]
    assert len(bank) == 2 and all("g_xr" not in x[0] for x in bank) and max(float(x[3]) for x in bank) <= 100.0
    assert "(?!g_xr[._/])" in (tmp_path / "vpw_bank_clock.tcl").read_text()


def test_xr_mid_keeps_bank_form_under_min(tmp_path):
    r = _run(tmp_path, XR_FAR, {"OT_S81_VPW_XR_MID": "1000:500"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_VPW_XR_MID KEEP" in r.stdout and "PLACED 6" in r.stdout
    assert "(?!g_xr" not in (tmp_path / "vpw_bank_clock.tcl").read_text()


def test_vpw_xr_mid_types_exports_only_listed_types():
    import gen_phys
    b = {"vpw_xr_mid_types": {"ot_s81sl_leaf__t3": {"min_um": 600, "d_um": 500}}}
    assert gen_phys._vpw_xr_mid(b, "ot_s81sl_leaf__t3") == ["export OT_S81_VPW_XR_MID = 600:500"]
    assert gen_phys._vpw_xr_mid(b, "ot_s81sl_leaf__t4") == []
    assert gen_phys._vpw_xr_mid({}, "ot_s81sl_leaf__t3") == []
