# DIE-HBM-97 11-11 VSN2-HOLD hybrid (COORD 00:5x): reset root on ONE clock tap with its direct relays.
# Opt-in, plan clock.reset_root_tap.types; gen_phys copies this file into the kit and pre_cts.tcl sources it after
# clock_taps.tcl and before reset_taps.tcl / reset_follow_clock.tcl.  Absent = no file, pre_cts.tcl unchanged.
# Why: the reset pin register u_rst_in feeds the depth-1 relays u_rrl_k directly (no hop lockup latch).  The nearest-
# tap split hangs the root and each relay on whatever tap is closest, so the hop crosses tap ports and the kit SDC times
# it with the whole tap window W (source latency -early -W / -late 0 per port, no CRPR across ports): vsN2 bf9c99d599c3
# FF hold u_rst_in -> u_rrl_38/D -30.32, -> u_rrl_27/D -15.08 after route.  Hung on the root's own tap the pair shares
# the tap root (CRPR), W drops out, and the >= 300 um root -> relay wire is ample hold delay; setup is a full cycle.
# Only the clock pins of the root's direct relays move (forward from Q through BUF / INV / HB cells); no cell, data or
# reset connection changes.  OT_RESET_ROOT_RE overrides the root instance regex.
namespace eval ::ot_rrt {
 proc tapnets {blk} {
  set d {}
  foreach bt [$blk getBTerms] {
   set n [$bt getNet]
   if {[regexp {^clk(_t[0-9]+)?$} [$bt getName]] && $n ne "NULL" && $n ne ""} { dict set d [$n getName] [$bt getName] }
  }
  return $d
 }
 proc clk_iterm {inst tn} {
  foreach it [$inst getITerms] {
   set n [$it getNet]
   if {$n ne "NULL" && $n ne "" && [dict exists $tn [$n getName]] && [[$it getMTerm] getIoType] eq "INPUT"} { return $it }
  }
  return ""
 }
 proc run {} {
  set blk [ord::get_db_block]
  set tn [tapnets $blk]
  set re [expr {[info exists ::env(OT_RESET_ROOT_RE)] && $::env(OT_RESET_ROOT_RE) ne "" ? $::env(OT_RESET_ROOT_RE) : {(^|[./])u_rst_in[./]}}]
  set roots {}
  foreach i [$blk getInsts] { if {[regexp -- $re [$i getName]] && [clk_iterm $i $tn] ne ""} { lappend roots $i } }
  if {[llength $roots] != 1} { puts "OT_RESET_ROOT_TAP skip: [llength $roots] clocked root flops match $re"; return }
  set r [lindex $roots 0]
  set rnet [[clk_iterm $r $tn] getNet]
  set front {}; set seen {}; set sinks {}
  foreach it [$r getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT" && [$it getNet] ne "NULL" && [$it getNet] ne ""} { lappend front [$it getNet] } }
  while {[llength $front]} {
   set n [lindex $front 0]; set front [lrange $front 1 end]
   if {[dict exists $seen [$n getName]]} continue
   dict set seen [$n getName] 1
   foreach it [$n getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    set d [$it getInst]
    if {$d eq $r} continue
    if {[regexp {^(BUF|INV|HB)} [[$d getMaster] getName]]} {
     foreach o [$d getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL" && [$o getNet] ne ""} { lappend front [$o getNet] } }
    } elseif {[set ck [clk_iterm $d $tn]] ne ""} {
     dict set sinks [$d getName] $ck
    }
   }
  }
  set moved 0; set already 0
  dict for {nm ck} $sinks {
   if {[[$ck getNet] getName] eq [$rnet getName]} { incr already; continue }
   $ck disconnect; $ck connect $rnet; incr moved
  }
  puts "OT_RESET_ROOT_TAP root [$r getName] on [dict get $tn [$rnet getName]]: [dict size $sinks] direct clocked sinks, $moved re-hung onto the root tap, $already already there"
 }
}
::ot_rrt::run
