# --step-tcl PRE_RESIZE hook for the ot_fwd_link_hop2 fixture: drop the buffers timing-driven global placement inserted
# (named place*) while the stage flops were still migrating into their fences (v10/v11: a B flop -> port net detoured
# through a buffer left at x 250 um, -426 ps).  repair_design in this step re-buffers those nets from the final, fenced
# placement.  Port buffers and the clock network are not touched (a bare remove_buffers crashed TritonCTS in v13).
set gp {}
foreach inst [[ord::get_db_block] getInsts] {
  if {[string match "place*" [$inst getName]]} { lappend gp [$inst getName] }
}
puts "OT_FWD: remove_buffers on [llength $gp] placement-inserted buffers before resize"
if {[llength $gp]} { remove_buffers [get_cells $gp] }
