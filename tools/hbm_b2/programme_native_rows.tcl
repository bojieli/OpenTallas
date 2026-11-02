# Disabled programme native row proposal. Normal PRE_GLOBAL_PLACE hook only.
# Normal face endpoint discovery runs first; its physical positions are then
# replaced by the explicitly reviewed INTERNAL_CORE same-stage row plan.
source /work/face_flops.tcl
set pr_block [ord::get_db_block]
set pr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set pr_plan {}
set pr_fh [open /work/runtime/actual_FF_rows.csv r]
gets $pr_fh pr_header
if {$pr_header ne "cell,master,ownership,x_um,y_um,planned_output_pin_x_um,planned_output_pin_y_um\r" &&
    $pr_header ne "cell,master,ownership,x_um,y_um,planned_output_pin_x_um,planned_output_pin_y_um"} {
  error "PROGRAMME_ROWS unexpected CSV schema"
}
while {[gets $pr_fh pr_line] >= 0} {
  if {$pr_line eq ""} continue
  lassign [split [string trimright $pr_line "\r"] ,] pr_name pr_master pr_role pr_x pr_y
  if {[dict exists $pr_plan $pr_name]} {error "PROGRAMME_ROWS duplicate name $pr_name"}
  if {$pr_master ne "DFFHQNx1_ASAP7_75t_R"} {error "PROGRAMME_ROWS unexpected native master"}
  dict set pr_plan $pr_name [list $pr_master $pr_x $pr_y]
}
close $pr_fh
if {[dict size $pr_plan] != 20842} {error "PROGRAMME_ROWS expected exact20842 actual FF"}
set pr_actual {}
foreach pr_inst [$pr_block getInsts] {
  if {[[$pr_inst getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} continue
  # Only literal OpenDB escaping of native instance bus brackets is decoded.
  set pr_name [string map [list {\[} {[} {\]} {]}] [$pr_inst getName]]
  if {[dict exists $pr_actual $pr_name]} {error "PROGRAMME_ROWS nonbijective native names"}
  dict set pr_actual $pr_name $pr_inst
}
if {[lsort [dict keys $pr_actual]] ne [lsort [dict keys $pr_plan]]} {
  error "PROGRAMME_ROWS source/SYNTH name set differs from reviewed actual graph"
}
set pr_orient {}
foreach pr_row [$pr_block getRows] {
  lassign [$pr_row getOrigin] pr_rx pr_ry
  dict set pr_orient $pr_ry [list [$pr_row getOrient] $pr_rx [[$pr_row getSite] getWidth]]
}
set pr_out [open $::env(RESULTS_DIR)/programme_native_rows.txt w]
dict for {pr_name pr_spec} $pr_plan {
  lassign $pr_spec pr_master pr_cx pr_cy
  set pr_inst [dict get $pr_actual $pr_name]
  set pr_x [expr {round(($pr_cx-.54)*$pr_dbu)}]
  set pr_y [expr {round(($pr_cy-.135)*$pr_dbu)}]
  if {![dict exists $pr_orient $pr_y]} {error "PROGRAMME_ROWS missing actual native row for $pr_name"}
  lassign [dict get $pr_orient $pr_y] pr_o pr_rx pr_sw
  if {($pr_x-$pr_rx)%$pr_sw != 0} {error "PROGRAMME_ROWS off actual native row site"}
  $pr_inst setOrient $pr_o
  $pr_inst setLocation $pr_x $pr_y
  set pr_b [$pr_inst getBBox]
  if {[$pr_b xMin] != $pr_x || [$pr_b yMin] != $pr_y} {error "PROGRAMME_ROWS actual native orientation/location mismatch"}
  $pr_inst setPlacementStatus FIRM
  puts $pr_out [list [$pr_inst getName] $pr_x $pr_y $pr_o]
}
close $pr_out
source /work/runtime/programme_clock_reserve.tcl
puts "PROGRAMME_ROWS exact20842 source-native FF on reviewed rows; normal DPL/guards retained"
