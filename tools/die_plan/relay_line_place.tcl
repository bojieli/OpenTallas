# relay_line_place.tcl (HBM-COLLECT-1/PTW-C 11-09, opt-in gen_core_kit_hbm.py --relay-line PREFIXES:DEPTH; sourced from
# core_pre_resize.tcl at ORFS PRE_RESIZE, i.e. after 3_3 global placement and before the 3_4 repair_design).
# Class: a pure register pipeline across a sparse core (pt_w: fill 0.019, W-face landing -> N/S-face port flop up to
# ~1438 um) gives wirelength-driven GPL no reason to spread the relay registers along the line: any point on the
# Manhattan path has the same HPWL, so r2 put relay -> S port at ~720 um (TT -53 ps) and 197-um repeater gaps.  This
# hook places, for every port flop whose name starts with one of OT_RELAY_LINE_PORTS, its DEPTH upstream register
# stages (walking back through single-input buffers / inverters only) at k/(DEPTH+1) of the landing -> port line,
# and sizes those relay flops up to OT_RELAY_LINE_FF (sized drivers for the long hops).  DPL legalises afterwards.
# Nothing else changes: no constraint, margin or gate.  Fail-closed: no chain found, or > 1 % of port flops without DEPTH
# upstream stages (those few are left where GPL put them and reported).
if {![info exists ::env(OT_RELAY_LINE_PORTS)] || $::env(OT_RELAY_LINE_PORTS) eq ""} { error "relay_line_place.tcl: OT_RELAY_LINE_PORTS unset" }
set rl_depth [expr {[info exists ::env(OT_RELAY_LINE_DEPTH)] ? int($::env(OT_RELAY_LINE_DEPTH)) : 2}]
# walk limit through single-input cells (SF-RELAY 11-10: max-wire repeaters on a ~1.1 mm core->relay line exceed 8, which
# skipped 66 static_front chains and left 1100-um hops); default 64, env OT_RELAY_LINE_WALK.
set ::rl_walk [expr {[info exists ::env(OT_RELAY_LINE_WALK)] ? int($::env(OT_RELAY_LINE_WALK)) : 64}]
set rl_ff [expr {[info exists ::env(OT_RELAY_LINE_FF)] ? $::env(OT_RELAY_LINE_FF) : "DFFHQNx3_ASAP7_75t_R"}]
set rl_db [ord::get_db]
set rl_blk [ord::get_db_block]
set rl_ffm [$rl_db findMaster $rl_ff]
if {$rl_ffm eq "NULL" || $rl_ffm eq ""} { error "relay_line_place.tcl: master $rl_ff not found" }

proc rl_in_iterms {inst} {
  set r {}
  foreach it [$inst getITerms] {
    if {[$it isInputSignal]} { lappend r $it }
  }
  return $r
}
# driver register of a register's D pin, through single-input combinational cells only
proc rl_seq_driver {it} {
  for {set hop 0} {$hop < $::rl_walk} {incr hop} {
    set net [$it getNet]
    if {$net eq "NULL" || $net eq ""} { return "" }
    set drv ""
    foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv [$t getInst]; break } }
    if {$drv eq ""} { return "" }
    if {[[$drv getMaster] isSequential]} { return $drv }
    set ins [rl_in_iterms $drv]
    if {[llength $ins] != 1} { return "" }
    set it [lindex $ins 0]
  }
  return ""
}
proc rl_d_iterm {inst} {
  foreach n {D d} { set it [$inst findITerm $n]; if {$it ne "NULL" && $it ne ""} { return $it } }
  return ""
}
set rl_n 0; set rl_short 0; set rl_sized 0; set rl_maxhop 0.0; set rl_sumhop 0.0; set rl_hops 0
set rl_prefixes [split $::env(OT_RELAY_LINE_PORTS) " ,"]
foreach inst [$rl_blk getInsts] {
  set nm [$inst getName]
  set hit 0
  foreach p $rl_prefixes { if {$p ne "" && [string first $p $nm] == 0} { set hit 1; break } }
  if {!$hit || ![[$inst getMaster] isSequential]} continue
  set chain {}
  set cur $inst
  for {set k 0} {$k <= $rl_depth} {incr k} {
    set d [rl_d_iterm $cur]
    if {$d eq ""} break
    set drv [rl_seq_driver $d]
    if {$drv eq ""} break
    lappend chain $drv
    set cur $drv
  }
  if {[llength $chain] < $rl_depth + 1} { incr rl_short; continue }
  set L [lindex $chain $rl_depth]
  lassign [$L getLocation] lx ly
  lassign [$inst getLocation] px py
  for {set i 0} {$i < $rl_depth} {incr i} {
    set r [lindex $chain $i]
    set f [expr {double($rl_depth - $i) / ($rl_depth + 1)}]
    set x [expr {int($lx + ($px - $lx) * $f)}]
    set y [expr {int($ly + ($py - $ly) * $f)}]
    if {[$r isFixed]} continue
    $r setLocation $x $y
    $r setPlacementStatus PLACED
    if {[regexp {^DFFHQNx[12]_ASAP7_75t_R$} [[$r getMaster] getName]]} { $r swapMaster $rl_ffm; incr rl_sized }
  }
  set hop [expr {(abs($px - $lx) + abs($py - $ly)) / 1000.0 / ($rl_depth + 1)}]
  if {$hop > $rl_maxhop} { set rl_maxhop $hop }
  set rl_sumhop [expr {$rl_sumhop + $hop}]; incr rl_hops
  incr rl_n
}
puts [format "OT_RELAY_LINE placed %d chains (depth %d), %d short chains skipped, %d relay flops sized to %s, register hop max %.1f um mean %.1f um" \
  $rl_n $rl_depth $rl_short $rl_sized $rl_ff $rl_maxhop [expr {$rl_hops ? $rl_sumhop / $rl_hops : 0}]]
if {$rl_n == 0} { error "OT_RELAY_LINE: no port-flop chain found for '$::env(OT_RELAY_LINE_PORTS)'" }
if {$rl_short * 100 > $rl_n} { error "OT_RELAY_LINE: $rl_short of [expr {$rl_n + $rl_short}] port flops have fewer than $rl_depth upstream register stages (> 1 %)" }
