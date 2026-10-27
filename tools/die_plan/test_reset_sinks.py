"""reset_sinks.tcl (PROTO-KITS 10-25 leaf hop bound) on a small OpenDB mock: every reset-tree sink moves to the
nearest tap relay of the same polarity; relays / block pins stay; the leaf max is checked against the reach."""
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).with_name("reset_sinks.tcl")

MOCK = r"""
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1}
set NETS {}; set INSTS {}
proc mk_net {n} { global NETS; dict set NETS $n {}; proc $n {m args} "net_do $n \$m \$args" }
proc net_do {n m a} {
  global NETS
  switch $m { getName {return $n} getITerms {return [dict get $NETS $n]} }
}
proc mk_mterm {name dir} { proc mt_$name$dir {m} "switch \$m {getIoType {return $dir} getName {return $name}}"; return mt_$name$dir }
proc mk_master {name blk} { proc ma_$name {m} "switch \$m {getName {return $name} isBlock {return $blk}}"; return ma_$name }
proc mk_bbox {x y} { set b bb_$x\_$y; proc $b {m} "switch \$m {xMin {return $x} xMax {return $x} yMin {return $y} yMax {return $y}}"; return $b }
set IT 0
proc mk_iterm {inst pin dir net} {
  global IT NETS ITNET
  incr IT; set t it$IT
  set ITNET($t) $net
  proc $t {m args} "it_do $t $inst [mk_mterm $pin $dir] \$m \$args"
  if {$net ne "NULL"} { dict lappend NETS $net $t }
  return $t
}
proc it_do {t inst mt m a} {
  global ITNET NETS
  switch $m {
    getMTerm {return $mt} getInst {return $inst} getNet {return $ITNET($t)}
    disconnect { set n $ITNET($t); dict set NETS $n [lsearch -all -inline -not [dict get $NETS $n] $t]; set ITNET($t) NULL }
    connect { set n [lindex $a 0]; set ITNET($t) $n; dict lappend NETS $n $t }
  }
}
# inst name master isBlock x y {pin dir net ...}
proc mk_inst {name master blk x y pins} {
  global INSTS
  set its {}
  foreach {p d n} $pins { lappend its [mk_iterm $name $p $d $n] }
  set ma [mk_master $master $blk]; set bb [mk_bbox $x $y]
  proc $name {m args} "switch \$m {getName {return $name} getMaster {return $ma} getBBox {return $bb} getITerms {return {$its}}}"
  lappend INSTS $name
}
proc blk {m args} { global INSTS; switch $m { getInsts {return $INSTS} } }
foreach n {nt0 nt1 nt1b nroot} { mk_net $n }
# tap relays (t0 at 0,0; t1 at 1000,0), t1 drives an inverter (parity-1 net nt1b)
mk_inst u_rrl_1_reg DFFHQNx1 0 0 0 {D INPUT nroot QN OUTPUT nt0}
mk_inst u_rrl_2_reg DFFHQNx1 0 1000 0 {D INPUT nroot QN OUTPUT nt1}
mk_inst inv1 INVx1 0 1000 0 {A INPUT nt1 Y OUTPUT nt1b}
# sinks: s_near_t1 on t0 (moves to t1), s_far on t0 at 1500,0 (moves to t1, 500 > 405), core block on t0 stays
mk_inst s_near_t1 DFFASRHQNx1 0 900 0 {RESETN INPUT nt0}
mk_inst s_t0 DFFASRHQNx1 0 100 0 {RESETN INPUT nt0}
mk_inst s_far DFFASRHQNx1 0 %FAR% 0 {RESETN INPUT nt0}
mk_inst s_inv_pol DFFASRHQNx1 0 1050 0 {RESETN INPUT nt1b}
mk_inst u_core CORE 1 950 0 {rst_n INPUT nt0}
"""


def run(tmp_path, far):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    tree = tmp_path / "reset_tree.tcl"
    tree.write_text("rtr_place rst_n_t0 {*u_rrl_1[./_]*} 0 0 rrl:tap1\nrtr_place rst_n_t1 {*u_rrl_2[./_]*} 1000 0 rrl:pad1\n")
    script = (MOCK.replace("%FAR%", str(far)) + f"\nset ::env(RESULTS_DIR) {{{tmp_path}}}\n"
              f"set ::env(OT_RESET_TREE_TCL) {{{tree}}}\nset ::env(OT_RESET_REACH_UM) 405\nsource {{{HOOK}}}\n"
              "foreach i {s_near_t1 s_t0 s_far s_inv_pol u_core} { puts \"NET $i [[lindex [$i getITerms] 0] getNet]\" }\n")
    p = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert not p.stderr, p.stderr
    return p.stdout


def test_sinks_move_to_nearest_tap_and_pass(tmp_path):
    out = run(tmp_path, 1300)
    assert "NET s_near_t1 nt1" in out and "NET s_t0 nt0" in out and "NET s_far nt1" in out
    assert "NET s_inv_pol nt1b" in out          # parity-1 sink keeps the only parity-1 net
    assert "NET u_core nt0" in out              # block pins are never re-pointed
    line = next(l for l in out.splitlines() if l.startswith("OT_RESET_SINKS"))
    assert "2 tap relays" in line and "2 re-pointed" in line and ": PASS" in line and "leaf max 300.0 um" in line
    assert (tmp_path / "ot_reset_sinks.txt").is_file()


def test_leaf_beyond_reach_fails(tmp_path):
    out = run(tmp_path, 1500)
    line = next(l for l in out.splitlines() if l.startswith("OT_RESET_SINKS"))
    assert "1 > 405.0 um: FAIL" in line and "s_far/RESETN@t1:500.0" in line
