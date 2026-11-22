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
    """XR-MID-1 (S81-GEOM-OPUS 11-18): VS centre (925,25) to the far bank centre (5,425) = 1320 um, MIN 600 / D 500 ->
    the 4 g_xr flops go to 500 um from VS along that line (target ~(576,177)), the 2 other write-port flops stay at
    the bank; the tap group excludes g_xr"""
    r = _run(tmp_path, XR_FAR, {"OT_S81_VPW_XR_MID": "600:500"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_VPW_XR_MID placed 4 of 4" in r.stdout, r.stdout
    mid = [ln.split("\t") for ln in (tmp_path / "vpw_xr_mid_sites.tsv").read_text().splitlines()[1:]]
    assert len(mid) == 4 and all(abs(float(x[1]) - 576.5) + abs(float(x[2]) - 176.5) <= 10 for x in mid), mid
    bank = [ln.split("\t") for ln in (tmp_path / "vpw_bank_sites.tsv").read_text().splitlines()[1:]]
    assert len(bank) == 2 and all("g_xr" not in x[0] for x in bank) and max(float(x[3]) for x in bank) <= 100.0
    assert "(?!g_xr[._/])" in (tmp_path / "vpw_bank_clock.tcl").read_text()


def test_xr_mid_keeps_bank_form_under_min(tmp_path):
    r = _run(tmp_path, XR_FAR, {"OT_S81_VPW_XR_MID": "1400:500"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_VPW_XR_MID KEEP" in r.stdout and "PLACED 6" in r.stdout
    assert "(?!g_xr" not in (tmp_path / "vpw_bank_clock.tcl").read_text()


def test_vpw_xr_mid_types_exports_only_listed_types():
    import gen_phys
    b = {"vpw_xr_mid_types": {"ot_s81sl_leaf__t3": {"min_um": 600, "d_um": 500}}}
    assert gen_phys._vpw_xr_mid(b, "ot_s81sl_leaf__t3") == ["export OT_S81_VPW_XR_MID = 600:500"]
    assert gen_phys._vpw_xr_mid(b, "ot_s81sl_leaf__t4") == []
    assert gen_phys._vpw_xr_mid({}, "ot_s81sl_leaf__t3") == []


AFF = r"""
mkbox b0box 0 0 10000 10000
mkbox b1box 0 420000 10000 430000
mkinst b0 u_bound.u_u_lf4_u_vp_u_b0 sram b0box FIRM
mkinst b1 u_bound.u_u_lf4_u_vp_u_b1 sram b1box FIRM
lappend ::insts b0 b1
set n 0
foreach name {
  {u_bound.u_u_lf4_u_vp_g_wr1_u_w.g_slr.g_b\[1\].g_r\[0\].sa_q\[0\]$_DFF_P_}
  {u_bound.u_u_lf4_u_vp_g_wr1_u_w.g_xrb.g_b\[0\].sw_d_q\[3\]$_DFF_P_}
  {u_bound.u_u_lf4_u_vp_g_wr1_u_w.g_xrb.g_b\[1\].sw_d_q\[3\]$_DFF_P_}
  {u_bound.u_u_lf4_u_vp_g_wr1_u_w.wa_q\[1\]\[2\]$_DFF_P_}
  {u_bound.u_u_lf4_u_vp_g_wr1_u_w.wdo_q\[0\]\[114\]$_DFF_P_}
  {u_bound.u_u_lf4_u_vp_g_wr1_u_w.wdo_q\[1\]\[114\]$_DFF_P_}
  {u_bound.u_u_lf4_u_vp_g_wr1_u_w.wv_q\[1\]$_DFF_P_}
} {
  mkbox fb$n 0 0 0 0
  mkinst f$n $name dff fb$n PLACED
  lappend ::insts f$n; incr n
}
mkrows 0 480000
"""


def _sites(tmp_path):
    return {ln.split("\t")[0]: ln.split("\t") for ln in (tmp_path / "vpw_bank_sites.tsv").read_text().splitlines()[1:]}


def test_bank_affinity_sites_each_bank_ff_at_its_own_bank(tmp_path):
    """BANK-AFF (OPUS-FIX-S81-LEAF-R10 11-22): bank-1 FFs (g_b[1], wa_q[1], wdo_q[1]) at u_b1 (y >= 420 - 100), bank-0
    FFs at u_b0 (y <= 110); the shared wv_q keeps nearest-either."""
    r = _run(tmp_path, AFF, {"OT_S81_VPW_BANK_AFF": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_VPW_BANK_AFF 6 of 7" in r.stdout and "PLACED 7" in r.stdout, r.stdout
    rows = _sites(tmp_path)
    for name, row in rows.items():
        y = float(row[2])
        if "g_b[1]" in name or "g_b\\[1\\]" in name or "_q\\[1\\]\\[" in name or "_q[1][" in name:
            assert y >= 320, (name, row)
        elif "wv_q" not in name:
            assert y <= 110, (name, row)
        assert float(row[3]) <= 100.0
    assert len({(r_[1], r_[2]) for r_ in rows.values()}) == 7


def test_bank_affinity_off_is_nearest_either(tmp_path):
    r = _run(tmp_path, AFF)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_VPW_BANK_AFF" not in r.stdout and "PLACED 7" in r.stdout


def test_vpw_bank_aff_types_exports_only_listed_types():
    import gen_phys
    b = {"vpw_bank_aff_types": ["ot_s81sl_leaf__t31"]}
    assert gen_phys._vpw_bank_aff(b, "ot_s81sl_leaf__t31") == ["export OT_S81_VPW_BANK_AFF = 1"]
    assert gen_phys._vpw_bank_aff(b, "ot_s81sl_leaf__t3") == []
    assert gen_phys._vpw_bank_aff({}, "ot_s81sl_leaf__t31") == []
