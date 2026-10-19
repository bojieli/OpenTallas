read_db /work/results/asap7/opentallas_dsfd_ctrl_rg2_asap7_ref_gate/base/3_place.odb
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /model/instances.tsv w]; puts $f "name\tmaster\tblock\tstatus\tx\ty\tw\th\tarea"
foreach i [$b getInsts] {set m [$i getMaster];set r [$i getBBox];set x [expr {[$r xMin]/double($dbu)}];set y [expr {[$r yMin]/double($dbu)}];set w [expr {[expr {[$r xMax]-[$r xMin]}]/double($dbu)}];set h [expr {[expr {[$r yMax]-[$r yMin]}]/double($dbu)}];puts $f "[$i getName]\t[$m getName]\t[$m isBlock]\t[$i getPlacementStatus]\t$x\t$y\t$w\t$h\t[expr {$w*$h}]"}
close $f
puts "CTRL_BANK64_ACTUAL_INSTANCES [llength [$b getInsts]]"
