# Original functional forwarding FF serves both pins; no additional state.
# Move that used FF from the first face anchor to the actual pin midpoint.
# Columns/rows spread dense samples; avoid the unchanged 5.4um macro halos.
set mp_block [ord::get_db_block]
set mp_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set mp_map [dict create]
foreach mp_inst [$mp_block getInsts] {
  if {![regexp {^DFF} [[$mp_inst getMaster] getName]]} continue
  regsub -all {\\} [$mp_inst getName] {} mp_name
  if {[regexp {^u_l\.lo\[([0-9]+)\]\$_DFF} $mp_name -> mp_bit]} {
    set mp_key "lo\[$mp_bit\]"
  } elseif {[regexp {^u_l\.co\[([0-9]+)\]\$_DFF} $mp_name -> mp_bit] && $mp_bit >= 212} {
    set mp_key "co\[$mp_bit\]"
  } else { continue }
  if {[dict exists $mp_map $mp_key]} { error "S81_MIDPOINT duplicate used role $mp_key: [[dict get $mp_map $mp_key] getName] / [$mp_inst getName]" }
  dict set mp_map $mp_key $mp_inst
}
if {[dict size $mp_map] != 1464} { error "S81_MIDPOINT expected1464 used forwarding FFs, found[dict size $mp_map]" }
set mp_haloboxes {}
foreach mp_inst [$mp_block getInsts] {
  if {![[$mp_inst getMaster] isBlock]} continue
  set mp_bb [$mp_inst getBBox]
  lappend mp_haloboxes [list [expr {[$mp_bb xMin]/double($mp_dbu)-5.4}] [expr {[$mp_bb yMin]/double($mp_dbu)-5.4}] [expr {[$mp_bb xMax]/double($mp_dbu)+5.4}] [expr {[$mp_bb yMax]/double($mp_dbu)+5.4}]]
}
set mp_report_file [expr {[info exists ::env(S81_MIDPOINT_REPORT)] ? $::env(S81_MIDPOINT_REPORT) : "/work/s81_midpoint_anchor.tsv"}]
set mp_report [open $mp_report_file w]
puts $mp_report "output\tinput\tflop\tx_um\ty_um\tinput_manhattan_center_um\toutput_manhattan_center_um"
set mp_worst 0.0
set mp_hundred 0
foreach mp_key [lsort [dict keys $mp_map]] {
  set mp_inst [dict get $mp_map $mp_key]
  regexp {^(lo|co)\[([0-9]+)\]$} $mp_key -> mp_kind mp_bit
  if {$mp_kind eq "lo"} { set mp_input "li\[[expr {$mp_bit+276}]\]" } else { set mp_input "ci\[[expr {$mp_bit-212}]\]" }
  set mp_in [$mp_block findBTerm $mp_input]; set mp_out [$mp_block findBTerm $mp_key]
  if {$mp_in eq "NULL" || $mp_out eq "NULL"} { error "S81_MIDPOINT missing actual pins $mp_input / $mp_key" }
  set mp_a [$mp_in getBBox];set mp_b [$mp_out getBBox]
  set mp_ax [expr {([$mp_a xMin]+[$mp_a xMax])/2.0/$mp_dbu}];set mp_ay [expr {([$mp_a yMin]+[$mp_a yMax])/2.0/$mp_dbu}]
  set mp_bx [expr {([$mp_b xMin]+[$mp_b xMax])/2.0/$mp_dbu}];set mp_by [expr {([$mp_b yMin]+[$mp_b yMax])/2.0/$mp_dbu}]
  set mp_w [expr {[[$mp_inst getMaster] getWidth]/double($mp_dbu)}];set mp_h [expr {[[$mp_inst getMaster] getHeight]/double($mp_dbu)}]
  set mp_x [expr {($mp_ax+$mp_bx-$mp_w)/2.0}];set mp_y [expr {($mp_ay+$mp_by-$mp_h)/2.0}]
  if {$mp_kind eq "lo"} { set mp_x [expr {$mp_x+($mp_bit%6-2.5)*($mp_w+0.216)}] } else { set mp_y [expr {$mp_y+($mp_bit%6-2.5)*0.576}] }
  foreach mp_box $mp_haloboxes {
    lassign $mp_box mp_x0 mp_y0 mp_x1 mp_y1
    if {$mp_x < $mp_x1 && $mp_x+$mp_w > $mp_x0 && $mp_y < $mp_y1 && $mp_y+$mp_h > $mp_y0} {
      # The midpoint corridor is between the two actual macro stacks.
      if {($mp_x0+$mp_x1)/2.0 > ($mp_ax+$mp_bx)/2.0} { set mp_x [expr {$mp_x0-$mp_w}] } else { set mp_x $mp_x1 }
    }
  }
  $mp_inst setLocation [expr {round($mp_x*$mp_dbu)}] [expr {round($mp_y*$mp_dbu)}]
  $mp_inst setPlacementStatus FIRM
  set mp_cx [expr {$mp_x+$mp_w/2.0}];set mp_cy [expr {$mp_y+$mp_h/2.0}]
  set mp_di [expr {abs($mp_cx-$mp_ax)+abs($mp_cy-$mp_ay)}];set mp_do [expr {abs($mp_cx-$mp_bx)+abs($mp_cy-$mp_by)}]
  set mp_worst [expr {max($mp_worst,$mp_di,$mp_do)}]
  if {max($mp_di,$mp_do)>100.0} { incr mp_hundred }
  puts $mp_report "$mp_key\t$mp_input\t[$mp_inst getName]\t$mp_x\t$mp_y\t$mp_di\t$mp_do"
}
close $mp_report
puts "S81_MIDPOINT anchored [dict size $mp_map] genuine forwarding FFs; max center Manhattan reach $mp_worst um; $mp_hundred pairs exceed conservative100um heuristic. Actual SS pair/hold evidence required."
