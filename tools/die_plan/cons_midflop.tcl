# TYPE-CONS-2 (POST_GLOBAL_PLACE hook, OT_CONS_KIT kits with OT_MIDFLOP_RE only): register at the midpoint of a one-cycle transport.
# A core output flop with hundreds of ps of D-side slack sat next to its fan-in and left its whole Q wire to the face flop
# (QC hc: D-side min +423 ps, Q-side -140 ps). Move each matching flop to OT_MIDFLOP_FRAC of the way to its single flop sink and
# spread its fanout-1 repeater chain evenly on the new leg. No netlist change, no pin cycle; detail placement legalizes.
proc ot_mf_out {inst} {
  foreach it [$inst getITerms] { if {[$it isOutputSignal]} { set n [$it getNet]; if {$n ne "NULL"} { return $n } } }
  return ""
}
proc ot_mf_center {inst} { set b [$inst getBBox]; return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
proc ot_midflop {} {
  set block [ord::get_db_block]
  set re $::env(OT_MIDFLOP_RE)
  set frac [expr {[info exists ::env(OT_MIDFLOP_FRAC)] ? $::env(OT_MIDFLOP_FRAC) : 0.5}]
  set moved 0; set skip 0; set tot 0.0
  foreach inst [$block getInsts] {
    if {![regexp -- $re [$inst getName]]} continue
    if {[$inst isFixed]} { incr skip; continue }
    set chain {}; set n [ot_mf_out $inst]; set sink ""; set guard 0
    while {$n ne "" && [incr guard] < 200} {
      set loads {}
      foreach it [$n getITerms] { if {[$it isInputSignal]} { lappend loads [$it getInst] } }
      if {[llength $loads] != 1 || [llength [$n getBTerms]]} break
      set l [lindex $loads 0]
      if {[regexp {^(BUF|INV|HB)} [[$l getMaster] getName]]} { lappend chain $l; set n [ot_mf_out $l]; continue }
      set sink $l; break
    }
    if {$sink eq ""} { incr skip; continue }
    lassign [ot_mf_center $inst] x0 y0
    lassign [ot_mf_center $sink] x1 y1
    set mx [expr {int($x0 + $frac*($x1-$x0))}]; set my [expr {int($y0 + $frac*($y1-$y0))}]
    set tot [expr {$tot + abs($x1-$x0) + abs($y1-$y0)}]
    $inst setLocation $mx $my
    set k 0; set m [llength $chain]
    foreach b $chain {
      incr k
      if {[$b isFixed]} continue
      $b setLocation [expr {int($mx + ($x1-$mx)*double($k)/($m+1))}] [expr {int($my + ($y1-$my)*double($k)/($m+1))}]
    }
    incr moved
  }
  set u [expr {double([$block getDbUnitsPerMicron])}]
  puts [format "OT_MIDFLOP moved %d skipped %d mean_leg_before %.1f um frac %.2f re %s" $moved $skip [expr {$moved ? $tot/$moved/$u : 0}] $frac $re]
  if {$moved == 0} { puts "OT_MIDFLOP: WARNING nothing matched" }
}
ot_midflop
