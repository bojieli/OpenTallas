# PRE_GLOBAL_PLACE hook (drive-0849, 2026-10-09): out_flop_at_pins.tcl extended to INPUT ports.  For every output port its
# launching flop, and for every input port its single capturing flop (the port net -- through up to three single-fanout
# INV / BUF stages -- reaches exactly one DFF D pin), is placed FIRM just inside the core on the pin's own edge, in up to
# 4 staggered columns by pin order.  Why: low-utilisation die-slot outlines (qfd_sp_constants_sequencer_sys 777.6 x 1000
# at ~1 %, qfd_sp_res_ser) let timing-driven GPL pull pin flops into the central logic, so pin -> flop and flop -> pin
# become 200-760 ps wires (ICUT 155370387: vm_rq -> line -514.8, c_data -309; res_ser r2q: i_addr -> c_addr 535 ps wire).
# The pin flop then carries the distance on a reg -> reg path with a full cycle.  out_flop_release.tcl (PRE_DETAIL_PLACE)
# returns them to PLACED for DPL (same list file).  Placement only, 0 cycles.
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
proc ot_of_isbuf {inst} { set m [[$inst getMaster] getName]; return [expr {[string match "INV*" $m] || [string match "BUF*" $m]}] }
# the single input-signal sink of a net (or "" if 0 or > 1 sinks)
proc ot_of_sink {net} {
  set s ""
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    if {$s ne ""} { return "" }
    set s $it
  }
  return $s
}
set ot_list {}; set ot_n 0; set ot_ni 0; set ot_skip 0
set cand {}
set ot_seen [dict create]
foreach bt [$ot_blk getBTerms] {
  set io [$bt getIoType]
  set net [$bt getNet]; if {$net eq "NULL"} continue
  set ff ""
  if {$io eq "OUTPUT"} {
    set d [ot_of_drv $net]; if {$d eq ""} { incr ot_skip; continue }
    set inst [$d getInst]
    for {set hop 0} {$hop < 4} {incr hop} {
      if {[ot_of_isff $inst]} { set ff $inst; break }
      if {![ot_of_isbuf $inst]} break
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
  } elseif {$io eq "INPUT"} {
    if {[$net getSigType] eq "CLOCK"} continue
    set s [ot_of_sink $net]; if {$s eq ""} { incr ot_skip; continue }
    for {set hop 0} {$hop < 4} {incr hop} {
      set inst [$s getInst]
      if {[ot_of_isff $inst]} {
        if {[[$s getMTerm] getName] eq "D"} { set ff $inst }
        break
      }
      if {![ot_of_isbuf $inst]} break
      set on ""
      foreach it [$inst getITerms] { if {[$it isOutputSignal]} { set on [$it getNet] } }
      if {$on eq "" || $on eq "NULL"} break
      set s [ot_of_sink $on]; if {$s eq ""} break
    }
  } else { continue }
  if {$ff eq ""} { incr ot_skip; continue }
  set fn [$ff getName]
  if {[dict exists $ot_seen $fn]} continue
  dict set ot_seen $fn 1
  set bb [$bt getBBox]
  set px [expr {double([$bb xMin] + [$bb xMax]) / 2.0 / $ot_dbu}]
  set py [expr {double([$bb yMin] + [$bb yMax]) / 2.0 / $ot_dbu}]
  if {$px <= $cx0} { set side L } elseif {$px >= $cx1} { set side R } elseif {$py <= $cy0} { set side B } else { set side T }
  lappend cand [list $side [expr {($side eq "L" || $side eq "R") ? $py : $px}] $ff $px $py $io]
}
foreach side {L R B T} { set ot_k($side) 0 }
foreach c [lsort -real -index 1 $cand] {
  lassign $c side pos ff px py io
  set col [expr {$ot_k($side) % 4}]; incr ot_k($side)
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
  if {$io eq "INPUT"} { incr ot_ni } else { incr ot_n }
}
set fh [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt w]
foreach n $ot_list { puts $fh $n }
close $fh
puts "OT_IOFLOP fixed $ot_n output-port and $ot_ni input-port flops at their pins ($ot_skip ports not single-flop)"
if {$ot_n + $ot_ni == 0} { error "OT_IOFLOP: no pin flop found (netlist changed?)" }
