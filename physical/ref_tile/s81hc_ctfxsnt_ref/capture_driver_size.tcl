# NORM tree ctfx_nt input-capture wire drivers (S-NORM, Claude 2026-10-14 22:55; replaces the fixed seven-bit list).
# 160 fd_in/fdx bit pairs cross over inside the strip (die pins: fd_in[b] N face and fdx[b] S face up to 83.8 um apart),
# so recipe 2 gives the pin's D net two captures (pin-owned capture + output-pin clone) and the CTS hold chain ends in a
# BUFx2 that drives the crossing wire (8-17 fF): 41-66 ps stages, native capture up to 211 ps > 190 (27 pins, 22:27 gate).
# Rule, applied to EVERY input-port capture cone (not a measured bit list): a BUFx2 whose output net spans > 20 um
# (iterm bbox half-perimeter) is the wire driver of a crossing and becomes BUFx4f.  Same cells, nets, flops, clocks,
# pins and constraints; only drive strength.  Runs in the CTS interpreter after hold repair (post_cts), then legal
# placement; any later replay only reports (later hold repair is judged by the routed native audit).
set ot_ncs_block [ord::get_db_block]
set ot_ncs_cts [expr {[llength [info procs ::ot_ref_cts_boundary_orig]] && [info exists ::cts_args]}]
proc ot_ncs_span {net} {
  set x0 1e18; set y0 1e18; set x1 -1e18; set y1 -1e18; set n 0
  foreach it [$net getITerms] {
    set loc [[$it getInst] getLocation]; incr n
    set x [lindex $loc 0]; set y [lindex $loc 1]
    if {$x < $x0} {set x0 $x}; if {$x > $x1} {set x1 $x}; if {$y < $y0} {set y0 $y}; if {$y > $y1} {set y1 $y}
  }
  if {$n < 2} { return 0.0 }
  return [expr {(($x1 - $x0) + ($y1 - $y0)) / double([[ord::get_db_tech] getDbUnitsPerMicron])}]
}
set ot_ncs_targets {}; set ot_ncs_holds 0
foreach bt [$ot_ncs_block getBTerms] {
  if {[$bt getIoType] ne "INPUT" || ![string match {fd_in*} [$bt getName]]} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  set front [list $net]
  for {set hop 0} {$hop < 12 && [llength $front]} {incr hop} {
    set next {}
    foreach n $front {
      foreach it [$n getITerms] {
        if {![$it isInputSignal]} continue
        set inst [$it getInst]; set m [[$inst getMaster] getName]
        if {![regexp {^(BUF|HB)} $m]} continue
        if {[string match hold* [$inst getName]]} { incr ot_ncs_holds }
        set out ""
        foreach o [$inst getITerms] { if {[$o isOutputSignal]} { set out [$o getNet] } }
        if {$out eq "" || $out eq "NULL"} continue
        if {$m eq "BUFx2_ASAP7_75t_R" && [ot_ncs_span $out] > 20.0} { dict set ot_ncs_targets [$inst getName] $inst }
        lappend next $out
      }
    }
    set front $next
  }
}
set ot_ncs_n [dict size $ot_ncs_targets]
if {$ot_ncs_cts && $ot_ncs_holds == 0} {
  puts "NORM_CAPTURE_SIZE: defer until post-CTS hold repair"
} elseif {!$ot_ncs_cts} {
  puts "NORM_CAPTURE_SIZE: replay outside CTS, $ot_ncs_n BUFx2 crossing drivers present (report only)"
} else {
  set x4 [[ord::get_db] findMaster BUFx4f_ASAP7_75t_R]
  if {$x4 eq "NULL"} { error "NORM_CAPTURE_SIZE: BUFx4f missing" }
  foreach name [lsort [dict keys $ot_ncs_targets]] {
    if {![[dict get $ot_ncs_targets $name] swapMaster $x4]} { error "NORM_CAPTURE_SIZE: swap failed for $name" }
    set_dont_touch [get_cells $name]
  }
  if {$ot_ncs_n} {
    detailed_placement
    check_placement -verbose
    estimate_parasitics -placement
  }
  puts "NORM_CAPTURE_SIZE: $ot_ncs_n crossing drivers BUFx2 -> BUFx4f ($ot_ncs_holds hold cells in the fd_in cones)"
}
