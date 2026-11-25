"""RAW-TAP-HOLD (C1o): opt-in hold pads on raw START taps; absent = nothing; the Tcl inserts exactly N pads per internal tap."""
import subprocess
import shutil
from types import SimpleNamespace
import pytest
import reset_tree as R


def _plan(cfg, types=("a", "b")):
    return SimpleNamespace(reset={} if cfg is None else {"raw_tap_hold": cfg}, types={t: {} for t in types})


def test_absent_and_types():
    assert R.raw_tap_hold(_plan(None), "a") == 0
    assert R.raw_tap_hold_tcl(0) == ""
    assert R.raw_tap_hold(_plan({"n": 1}), "a") == 1
    assert R.raw_tap_hold(_plan({"n": 2, "types": ["b"]}), "a") == 0
    assert R.raw_tap_hold(_plan({"n": 2, "types": ["b"]}), "b") == 2
    with pytest.raises(R.ResetError):
        R.raw_tap_hold(_plan({"n": 1, "types": ["zz"]}), "a")
    with pytest.raises(R.ResetError):
        R.raw_tap_hold(_plan({"n": 0}), "a")


MOCK = r'''
set ::nid 0
proc mkobj {kind args} { set o "$kind[incr ::nid]"; set ::P($o) $args; interp alias {} $o {} objcall $o; return $o }
proc objcall {o m args} {
  switch -- $m {
    getBTerms { return [expr {[dict exists $::P($o) bterms] ? [dict get $::P($o) bterms] : {}}] }
    getITerms { set r {}; foreach it $::ITS { if {[dict get $::P($it) net] eq $o} { lappend r $it } }; return $r }
    getName { return $o }
    getMTerm { return [dict get $::P($o) mterm] }
    getIoType { return [dict get $::P($o) io] }
    disconnect { dict set ::P($o) net NULL }
    connect { dict set ::P($o) net [lindex $args 0] }
    setDoNotTouch - setLocation - setPlacementStatus { }
    findNet { return [expr {[info exists ::NETS([lindex $args 0])] ? $::NETS([lindex $args 0]) : "NULL"}] }
    findMaster { return HB4 }
    findITerm { return [dict get $::P($o) [lindex $args 0]] }
  }
}
namespace eval odb {}
proc odb::dbNet_create {blk name} { set n [mkobj net]; set ::NETS($name) $n; return $n }
proc odb::dbInst_create {blk m name} {
  set i [mkobj inst]; incr ::NPAD
  set a [mkobj it mterm [mkobj mt io INPUT] net NULL]; set y [mkobj it mterm [mkobj mt io OUTPUT] net NULL]
  lappend ::ITS $a $y; dict set ::P($i) A $a; dict set ::P($i) Y $y; return $i }
namespace eval ord {}
proc ord::get_db {} { return [mkobj db] }
set ::NPAD 0; set ::ITS {}
set ff_blk [mkobj blk]
set out [mkobj mt io OUTPUT]; set in [mkobj mt io INPUT]
set n6 [mkobj net]; set n9 [mkobj net bterms {p}]; set nrl [mkobj net]
set d6 [mkobj it mterm $out net $n6]; set l6 [mkobj it mterm $in net $n6]
set d9 [mkobj it mterm $out net $n9]; set drl [mkobj it mterm $out net $nrl]
lappend ::ITS $d6 $l6 $d9 $drl
set rtr_qnets [dict create rr_t6 $n6 rr_t9 $n9 rst_rl_3 $nrl]
set rtr_at [dict create rr_t6 {10 20} rr_t9 {0 0} rst_rl_3 {0 0}]
'''


@pytest.mark.skipif(not shutil.which("tclsh"), reason="tclsh")
def test_tcl_inserts_pads_internal_taps_only():
    chk = ('\nputs "RES $::NPAD [dict get $::P($d6) net] [dict get $::P($d9) net] [dict get $::P($drl) net] '
           '[llength [objcall $n6 getITerms]]"\n')
    out = subprocess.run(["tclsh"], input=MOCK + R.raw_tap_hold_tcl(2) + chk, text=True, capture_output=True)
    assert out.returncode == 0, out.stderr
    assert "OT_RAW_TAP_HOLD 1 raw taps x 2 HB4xp67 (port taps kept direct: 1 rr_t9)" in out.stdout
    res = out.stdout.split("RES ")[1].split()
    assert res[0] == "2"                      # two pads, only on rr_t6
    assert res[1] != "net" and res[1] != res[2]  # tap flop moved onto the pad chain net
    assert res[2].startswith("net") and res[3].startswith("net")   # port tap and internal relay net untouched
    assert res[4] == "2"                      # original rr_t6 net: its load + the last pad Y (pad drives the loads)
