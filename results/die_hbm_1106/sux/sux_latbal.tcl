# HBM-FORM-SPLIT-14-SUX 2026-11-06: POST-CTS SUBTREE LATENCY BALANCE (clock form, not a knob) for the HBM SU lane cores.
# Measured on the routed vC/vD/full_x-vB DBs (TT, SPEF): every R2R setup and every R2R FF hold violation passes at
# zero skew (worst zero-skew slack setup +16 / +27 / -1 ps, hold all >= 0 but one -9.6); the misses are related-pair
# clock skew 195..224 ps.  The skew is CTS-intrinsic: the trees are tight (median 307 / 451 / 525 ps) with a late tail
# in a few branches that detour around the six SRAM macros (xD NE corner via a 100-um wire repeater: 456..466 ps;
# full_x dtap_2/18/26 at 590..640) while most leaves are 150..190 ps earlier.
# Form: classic post-CTS latency balancing of the WHOLE tree to its latest sink.  Tree = clock port net through every
# buffer / inverter; each node's subtree latest-sink arrival M(n) is measured (propagated clock, placement RC); the target
# T = latest sink arrival before balancing (fixed, never chased).  Top-down, delay stages (BUFx4) are inserted in front
# of the HIGHEST node whose whole subtree is early by >= one stage (k = floor((T - M(n) - tol) / stage)), so a branch
# is delayed once at its root instead of at every leaf; nodes below a delayed node wait for the next round, which
# re-measures.  SRAM macro clock pins are sinks like flops (their pin arrival is balanced).  Same ports, clocks, flops,
# cycles and logic; only clock-tree buffering is added (cells delaybuf_otsux_*, nets otsux_net_*).
# Offline replay on the routed kits' 4_cts.odb (placement RC, TT, before -> after): exp_x vD 265..438 (p1..p99 159) -> 376..435
# (p1..p99 30, 1138 BUFx4); exp_x vC 431..547 (84) -> 514..543 (22, 966); full_x vB 381..486 (56) -> 456..482 (22, 748).
# Insertion grows to ~T (insertion band is checked in die STA, OWNER 11-03).  Wrapped in catch: a failure keeps the
# CTS result.  Env: OT_SUX_LB=0 disables; OT_SUX_LB_TOL (ps, default 8); OT_SUX_LB_STAGE (ps, default 20);
# OT_SUX_LB_ROUNDS (default 12); OT_SUX_LB_CELL (default BUFx4_ASAP7_75t_R); OT_SUX_LB_CLOCK_PORT (default clk).
namespace eval sux {}
set ::sux::tol   [expr {[info exists ::env(OT_SUX_LB_TOL)]    ? $::env(OT_SUX_LB_TOL)    : 8.0}]
set ::sux::stage [expr {[info exists ::env(OT_SUX_LB_STAGE)]  ? $::env(OT_SUX_LB_STAGE)  : 20.0}]
set ::sux::rounds [expr {[info exists ::env(OT_SUX_LB_ROUNDS)] ? $::env(OT_SUX_LB_ROUNDS) : 12}]
set ::sux::cell  [expr {[info exists ::env(OT_SUX_LB_CELL)]   ? $::env(OT_SUX_LB_CELL)   : "BUFx4_ASAP7_75t_R"}]
set ::sux::port  [expr {[info exists ::env(OT_SUX_LB_CLOCK_PORT)] ? $::env(OT_SUX_LB_CLOCK_PORT) : "clk"}]
if {![info exists ::sux::n]} { set ::sux::n 0 }

proc sux::arr {pinname} {
  set p [get_pins -quiet $pinname]
  if {![llength $p]} { return "" }
  set a [get_property $p arrival_max_rise]
  if {$a eq "" || $a eq "INF" || $a eq "-INF"} { return "" }
  if {abs($a) < 1.0} { set a [expr {$a * 1e12}] }
  return $a
}
proc sux::is_node {inst} {
  set m [[$inst getMaster] getName]
  if {[[$inst getMaster] isBlock]} { return 0 }
  return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "CKINV*" $m] || [string match "HB*" $m]}]
}
proc sux::in_iterm {inst} {
  foreach t [$inst getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { return $t } }
  return ""
}
proc sux::out_net {inst} {
  foreach t [$inst getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { return [$t getNet] } }
  return ""
}
# build: ::sux::kids(node) = child node insts, ::sux::sinks(node) = sink pin names; root node = "PORT"
proc sux::build {} {
  set blk [ord::get_db_block]
  array unset ::sux::kids; array unset ::sux::sinks
  set bt [$blk findBTerm $::sux::port]
  if {$bt eq "NULL"} { error "no clock port $::sux::port" }
  set todo [list [list PORT [$bt getNet]]]; set nn 0; set ns 0
  while {[llength $todo]} {
    lassign [lindex $todo end] node net; set todo [lrange $todo 0 end-1]
    set ::sux::kids($node) {}; set ::sux::sinks($node) {}
    foreach it [$net getITerms] {
      if {![$it isInputSignal]} continue
      set i [$it getInst]
      if {[sux::is_node $i]} {
        set on [sux::out_net $i]
        if {$on eq ""} continue
        lappend ::sux::kids($node) [$i getName]; incr nn
        lappend todo [list [$i getName] $on]
      } else {
        if {[string match "clkload*" [$i getName]]} continue
        lappend ::sux::sinks($node) "[$i getName]/[[$it getMTerm] getName]"; incr ns
      }
    }
  }
  return [list $nn $ns]
}
# subtree latest / earliest sink arrival (post-order)
proc sux::measure {} {
  array unset ::sux::hi; array unset ::sux::lo
  set order {}; set st [list PORT]
  while {[llength $st]} { set n [lindex $st end]; set st [lrange $st 0 end-1]; lappend order $n; foreach k $::sux::kids($n) { lappend st $k } }
  set all {}
  foreach n [lreverse $order] {
    set h -1e9; set l 1e9
    foreach p $::sux::sinks($n) { set a [sux::arr $p]; if {$a eq ""} continue; lappend all $a; if {$a > $h} { set h $a }; if {$a < $l} { set l $a } }
    foreach k $::sux::kids($n) { if {$::sux::hi($k) > $h} { set h $::sux::hi($k) }; if {$::sux::lo($k) < $l} { set l $::sux::lo($k) } }
    set ::sux::hi($n) $h; set ::sux::lo($n) $l
  }
  set all [lsort -real $all]; set c [llength $all]
  if {!$c} { error "no sink arrivals" }
  return [list [lindex $all 0] [lindex $all [expr {$c / 100}]] [lindex $all [expr {$c / 2}]] [lindex $all [expr {$c - 1 - $c / 100}]] [lindex $all end] $c]
}
proc sux::fmt {m} { lassign $m mn p1 md p99 mx c; return [format "sinks %d min %.0f p1 %.0f med %.0f p99 %.0f max %.0f (spread %.0f, p1..p99 %.0f)" $c $mn $p1 $md $p99 $mx [expr {$mx - $mn}] [expr {$p99 - $p1}]] }
# one delay buffer in front of ITerm $sink at (x, y)
proc sux::insert {sink x y} {
  set blk [ord::get_db_block]
  set n0 [$sink getNet]; set inst [$sink getInst]
  set dt_n [$n0 isDoNotTouch]; set dt_i [$inst isDoNotTouch]
  $n0 setDoNotTouch 0; $inst setDoNotTouch 0
  set k [incr ::sux::n]
  set b [odb::dbInst_create $blk [[ord::get_db] findMaster $::sux::cell] delaybuf_otsux_$k]
  $b setLocation $x $y; $b setPlacementStatus PLACED
  set n1 [odb::dbNet_create $blk otsux_net_$k]; $n1 setSigType CLOCK
  $sink disconnect
  [$b findITerm A] connect $n0
  [$b findITerm Y] connect $n1
  $sink connect $n1
  $n0 setDoNotTouch $dt_n; $inst setDoNotTouch $dt_i
  return $b
}
proc sux::balance {} {
  set blk [ord::get_db_block]
  set_propagated_clock [all_clocks]
  lassign [sux::build] nn ns
  estimate_parasitics -placement
  set m [sux::measure]
  set T [lindex $m 4]
  puts "OT_SUX_LB before: $nn tree nodes, [sux::fmt $m]; target T = [format %.1f $T] (latest sink, fixed)"
  set n0 $::sux::n
  for {set r 0} {$r < $::sux::rounds} {incr r} {
    set added 0; set nodes 0
    set st $::sux::kids(PORT)
    while {[llength $st]} {
      set n [lindex $st end]; set st [lrange $st 0 end-1]
      set gap [expr {$T - $::sux::hi($n) - $::sux::tol}]
      # 3/4 of the stage estimate per round (re-measured next round): never overshoot T
      set k [expr {$gap >= $::sux::stage ? max(1, int(floor(0.75 * $gap / $::sux::stage))) : 0}]
      if {$k >= 1} {
        if {$k > 12} { set k 12 }
        set i [$blk findInst $n]; set it [sux::in_iterm $i]
        if {$it eq ""} continue
        lassign [$i getLocation] x y
        for {set j 0} {$j < $k} {incr j} { sux::insert $it $x $y }
        incr added $k; incr nodes
      } else {
        foreach c $::sux::kids($n) { lappend st $c }
      }
    }
    if {!$added} break
    if {[llength [info procs ot_pg_standard_bind]]} { ot_pg_standard_bind sux_latbal } else { global_connect }
    estimate_parasitics -placement
    set m [sux::measure]
    puts "OT_SUX_LB round $r: +$added delay buffers at $nodes nodes, [sux::fmt $m]"
  }
  if {[expr {$::sux::n - $n0}] && ![info exists ::sux::offline]} {
    detailed_placement
    check_placement -verbose
    estimate_parasitics -placement
    set m [sux::measure]
  }
  puts "OT_SUX_LB done: [expr {$::sux::n - $n0}] delay buffers ($::sux::cell), [sux::fmt $m]"
}
if {![info exists ::env(OT_SUX_LB)] || $::env(OT_SUX_LB) ne "0"} {
  if {[catch {sux::balance} e]} { puts "OT_SUX_LB ERROR (CTS result kept as is): $e" }
}
