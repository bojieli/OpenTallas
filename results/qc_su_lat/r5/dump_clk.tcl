read_db [lindex [glob /work/run/results/asap7/*/base/5_1_grt.odb] 0]
set f [open /work/r5_clk_cells.txt w]
foreach i [[ord::get_db_block] getInsts] {
  if {[string match ot_ms_* [$i getName]]} { set b [$i getBBox]; puts $f "[$i getName] [expr {[$b xMin]/1000.0}] [expr {[$b yMin]/1000.0}] [[$i getMaster] getName]" }
}
close $f
exit
