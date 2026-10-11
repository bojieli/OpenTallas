# [vm8] 2026-10-11 CLOCK GRID pre-CTS hook (PRECTS=physical/hbm_accel_die_views/vm/vcut8/pre_cts_clock_grid.tcl).
# 1. the common forwarded-clock root-buffer hook (pre_cts_fclk_root_buf.tcl: TritonCTS separateMacroRegSinks crash
#    workaround + vclk at the measured insertion), unchanged;
# 2. clock plan: every sink of the core root ck[0] (registers, SRAM clk pins, the root buffers of forwarded clocks) is
#    re-homed, by its placed location, to the nearest clock-grid root ckg<k> (make_vm_vcut8.py VM_CG: M7 area pins at
#    the centres of a 2 x 7 grid of ~175 x 143 um regions; the die drops every ck* pin from the same balanced clock,
#    exactly like the face taps ck[wens]<i>).  Logic, constraints and the clock are unchanged (all ck* ports are core_clk);
#    CTS then builds one small local tree per region instead of one 9-level tree over 350 x 1,000 um, and
#    tap_fclat.tcl balances the ckg* roots with the face taps to one REF.
# Why (hbm_vm8bfq bf62ad44e sww calibrate, FF): core tree insertion 284..490 ps (median 356, p99 447) over 32,859 sinks;
# the tail sits on the face-chain wire stages; output hold -47 (vclk = range midpoint + 50), chain s0 -> s1 -34 ps
# (107 ps leaf skew), CTS hold repair stalled at -91 ps / 37k buffers (sww), -86 (nww); sew TT setup -588 post-CTS.
source /src/physical/hbm_accel_die_views/common/pre_cts_fclk_root_buf.tcl

proc ot_cg_rehome {} {
  set blk [ord::get_db_block]
  set ckb [$blk findBTerm {ck[0]}]
  if {$ckb eq "NULL"} { set ckb [$blk findBTerm ck] }
  if {$ckb eq "NULL" || [$ckb getNet] eq "NULL"} { puts "OT_CG: no ck root -> skip"; return }
  set cnet [$ckb getNet]
  set roots {}
  foreach bt [$blk getBTerms] {
    if {![regexp {^ckg[0-9]+(\[0\])?$} [$bt getName]]} { continue }
    set n [$bt getNet]
    if {$n eq "NULL"} {
      set n [odb::dbNet_create $blk "ot_cg_[regsub -all {[^0-9A-Za-z]} [$bt getName] _]"]
      $bt connect $n
    }
    $n setSigType CLOCK
    set bb [$bt getBBox]
    lappend roots [list [$bt getName] $n [expr {([$bb xMin] + [$bb xMax]) / 2.0}] [expr {([$bb yMin] + [$bb yMax]) / 2.0}]]
  }
  if {![llength $roots]} { puts "OT_CG: no ckg roots -> skip (VM_CG=0 netlist)"; return }
  set cnt [dict create]
  foreach r $roots { dict set cnt [lindex $r 0] 0 }
  set moved 0
  foreach it [$cnet getITerms] {
    if {[$it isOutputSignal]} { continue }
    set bb [[$it getInst] getBBox]
    set x [expr {([$bb xMin] + [$bb xMax]) / 2.0}]; set y [expr {([$bb yMin] + [$bb yMax]) / 2.0}]
    set best ""; set bd 1e30
    foreach r $roots {
      set d [expr {abs($x - [lindex $r 2]) + abs($y - [lindex $r 3])}]
      if {$d < $bd} { set bd $d; set best $r }
    }
    $it disconnect
    $it connect [lindex $best 1]
    dict incr cnt [lindex $best 0]
    incr moved
  }
  set lo 1e9; set hi 0
  dict for {k v} $cnt { if {$v < $lo} { set lo $v }; if {$v > $hi} { set hi $v } }
  puts "OT_CG: re-homed $moved ck\[0\] sinks onto [llength $roots] clock-grid roots (per root $lo .. $hi)"
}
ot_cg_rehome
