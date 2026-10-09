# PRE_GLOBAL_PLACE hook (safe-qwen S-A5, 2026-10-08; the rom_cap_at_pins.tcl technique applied to output ports): put
# every output port's launching flop AT its pin.  Why: qfd_sp_tree_lane routed with lq[*] -> y[*] reg->pin wires of
# 560-738 ps over 145-212 um (class F): timing-driven GPL pulls the OSTN output stations into the logic.  For every
# output port, the driving DFF (directly, or through up to three single-fanout INV / BUF stages: ORFS port buffer, yosys QN inverter) is placed FIRM just inside
# the core on the pin's own edge, in up to 4 staggered columns by pin order; GPL places the logic around the fixed
# flops and out_flop_release.tcl (PRE_DETAIL_PLACE) returns them to PLACED for DPL.  Placement only, 0 cycles.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_core [$ot_blk getCoreArea]
set cx0 [expr {double([$ot_core xMin]) / $ot_dbu}]; set cx1 [expr {double([$ot_core xMax]) / $ot_dbu}]
set cy0 [expr {double([$ot_core yMin]) / $ot_dbu}]; set cy1 [expr {double([$ot_core yMax]) / $ot_dbu}]
set ot_gap [expr {[info exists ::env(OT_OFLOP_GAP)] ? $::env(OT_OFLOP_GAP) : 1.0}]
proc ot_of_drv {net} {
  foreach it [$net getITerms] { if {[$it isOutputSignal]} { return $it } }
  return ""
}
proc ot_of_isff {inst} { return [string match "DFF*" [[$inst getMaster] getName]] }
set ot_list {}; set ot_n 0; set ot_skip 0
set cand {}
foreach bt [$ot_blk getBTerms] {
  if {[$bt getIoType] ne "OUTPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  set d [ot_of_drv $net]; if {$d eq ""} { incr ot_skip; continue }
  # walk back through up to 3 single-fanout INV / BUF stages (ORFS port buffer, yosys QN inverter)
  set inst [$d getInst]; set ff ""
  for {set hop 0} {$hop < 4} {incr hop} {
    if {[ot_of_isff $inst]} { set ff $inst; break }
    set m [[$inst getMaster] getName]
    if {!([string match "INV*" $m] || [string match "BUF*" $m])} break
    set nxt ""
    foreach it [$inst getITerms] {
      if {![$it isInputSignal]} continue
      set n2 [$it getNet]; if {$n2 eq "NULL"} continue
      set d2 [ot_of_drv $n2]
      if {$d2 ne "" && [llength [$n2 getITerms]] == 2} { set nxt [$d2 getInst] }
    }
    if {$nxt eq ""} break
    set inst $nxt
  }
  if {$ff eq ""} { incr ot_skip; continue }
  set bb [$bt getBBox]
  set px [expr {double([$bb xMin] + [$bb xMax]) / 2.0 / $ot_dbu}]
  set py [expr {double([$bb yMin] + [$bb yMax]) / 2.0 / $ot_dbu}]
  if {$px <= $cx0} { set side L } elseif {$px >= $cx1} { set side R } elseif {$py <= $cy0} { set side B } else { set side T }
  lappend cand [list $side [expr {($side eq "L" || $side eq "R") ? $py : $px}] $ff $px $py]
}
foreach side {L R B T} { set k($side) 0 }
foreach c [lsort -real -index 1 $cand] {
  lassign $c side pos ff px py
  set col [expr {$k($side) % 4}]; incr k($side)
  set w [expr {double([[$ff getMaster] getWidth]) / $ot_dbu}]
  set h [expr {double([[$ff getMaster] getHeight]) / $ot_dbu}]
  switch $side {
    L { set x [expr {$cx0 + $ot_gap + $col * ($w + 0.2)}]; set y $py }
    R { set x [expr {$cx1 - $ot_gap - ($col + 1) * ($w + 0.2)}]; set y $py }
    B { set x $px; set y [expr {$cy0 + $ot_gap + $col * $h}] }
    T { set x $px; set y [expr {$cy1 - $ot_gap - ($col + 1) * $h}] }
  }
  $ff setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]
  $ff setPlacementStatus FIRM
  lappend ot_list [$ff getName]
  incr ot_n
}
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt w]
foreach n $ot_list { puts $fh $n }
close $fh
puts "OT_OFLOP fixed $ot_n output-port flops at their pins ($ot_skip outputs not flop-driven)"
if {$ot_n == 0} { error "OT_OFLOP: no flop-driven output port found (netlist changed?)" }
