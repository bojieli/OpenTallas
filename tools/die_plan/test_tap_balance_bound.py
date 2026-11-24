"""TAPBAL-BOUND 11-24 (QC-CBX-CLOCK, COORD): tap_balance.tcl never leaves a tap padded above the post-CTS tree bound.  The pad is
priced at ~18 ps a stage but the last stage drives the whole tree root (QC slw_hc1 cl3449ea95 clk_t101: ONE stage +41 ps, 263 ->
304 max; 54 of 132 taps over 285 with every raw tree under it).  After each pass a tap over the bound loses the chain just added
and may be re-padded with one stage fewer.  The real guard procs run under tclsh on a mock OpenDB."""
import shutil
import subprocess
from pathlib import Path

import pytest

D = Path(__file__).resolve().parent
TB = (D / "tap_balance.tcl").read_text()

MOCK = r'''
namespace eval odb {}
array set NET {}
array set INST {}
proc mk_net {n} { global NET; set NET($n) 1; proc $n {op args} "netcall $n \$op {*}\$args" }
proc netcall {n op args} {
  global CONN
  switch $op {
    getName { return $n }
    getITerms { set r {}; foreach k [lsort [array names CONN]] { if {$CONN($k) eq $n} { lappend r $k } }; return $r }
  }
}
proc mk_it {t inst net} { global CONN OWN; set CONN($t) $net; set OWN($t) $inst; proc $t {op args} "itcall $t \$op {*}\$args" }
proc itcall {t op args} {
  global CONN OWN
  switch $op { disconnect { set CONN($t) NULL } connect { set CONN($t) [lindex $args 0] } getInst { return $OWN($t) } }
}
proc mk_inst {i} { global INST; set INST($i) 1 }
proc blk {op name} {
  global NET INST
  switch $op {
    findInst { return [expr {[info exists INST($name)] ? $name : "NULL"}] }
    findNet { return [expr {[info exists NET($name)] ? $name : "NULL"}] }
  }
}
proc odb::dbInst_destroy {i} { global INST CONN OWN; unset INST($i); foreach k [array names OWN] { if {$OWN($k) eq $i} { unset CONN($k) } } }
proc odb::dbNet_destroy {n} { global NET; unset NET($n) }
proc tb_begin {} {}
proc tb_end {p} {}
set tb_blk blk; set tb_added 2; set tb_win 20.0; set ::tb_bnd 265.0
# port net root -> d0 -> n0 -> d1 -> tree -> 3 sink pins
mk_net root; mk_net t_tb0_n0; mk_net t_tb0_tree
mk_inst t_tb0_d0; mk_inst t_tb0_d1
mk_it d0.A t_tb0_d0 root; mk_it d0.Y t_tb0_d0 t_tb0_n0; mk_it d1.A t_tb0_d1 t_tb0_n0; mk_it d1.Y t_tb0_d1 t_tb0_tree
foreach s {s1 s2 s3} { mk_it $s.CK $s t_tb0_tree }
'''


def _guard_src():
    a = TB.index("set tb_guard [expr")
    b = TB.index("proc tb_tap_pass {it} {")
    return TB[a:b]


def _run(maxps):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    body = (MOCK + _guard_src()
            + "set tb_last [dict create clk_t9 [list root t_tb0_tree {t_tb0_d0 t_tb0_d1} {t_tb0_n0}]]\n"
            + f"puts \"RET [tb_bound_guard [dict create clk_t9 [list 290 236 {maxps} 7319 bt]]]\"\n"
            + 'puts "ROOT [lsort [root getITerms]]"\nputs "ADDED $tb_added UNDONE $tb_undone NCAP $tb_ncap LAST [dict size $tb_last]"\n'
            + 'puts "INSTS [lsort [array names INST]] NETS [lsort [array names NET]]"\n')
    r = subprocess.run(["tclsh"], input=body, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    return {ln.split()[0]: ln.split(None, 1)[1] if " " in ln else "" for ln in r.stdout.splitlines()}


def test_chain_over_bound_is_removed_and_capped():
    o = _run(304.0)                                   # clk_t101-like: max 304 > 265 + 20
    assert o["RET"] == "1"
    assert o["ROOT"] == "s1.CK s2.CK s3.CK"           # sinks back on the port net
    assert o["ADDED"].split()[0] == "0" and "UNDONE 1" in o["ADDED"] and "NCAP clk_t9 1" in o["ADDED"] and o["ADDED"].endswith("LAST 0")
    assert o["INSTS"].startswith("NETS") and o["INSTS"].split("NETS")[1].split() == ["root"]


def test_chain_under_bound_is_kept():
    o = _run(284.0)
    assert o["RET"] == "0" and o["ROOT"] == "d0.A"
    assert "UNDONE 0" in o["ADDED"] and o["ADDED"].endswith("LAST 0")
    assert "t_tb0_d0 t_tb0_d1" in o["INSTS"]


def test_guard_wired_into_the_pass_and_after_the_loop():
    p = TB[TB.index("proc tb_tap_pass {it} {"):]
    assert "if {[llength [info procs tb_bound_guard]] && [tb_bound_guard $m]} { set m [tb_measure] }" in p
    assert "set nb [expr {min($nb, [dict get $tb_ncap $n])}]" in p and "if {[dict get $tb_ncap $n] < 1} continue" in p and "[info exists tb_ncap] && [dict exists $tb_ncap $n]" in p
    assert "dict set tb_last $n [list $root $tree $tb_ci $tb_cn]" in p
    loop = "for {set it 0} {$it < $tb_iters} {incr it} {\n  if {![tb_tap_pass $it]} break\n}\ntb_bound_guard [tb_measure]\n"
    assert loop in TB
    assert 'set tb_guard [expr {![info exists ::env(OT_TAP_BOUND_GUARD)] || $::env(OT_TAP_BOUND_GUARD) ne "0"}]' in TB
