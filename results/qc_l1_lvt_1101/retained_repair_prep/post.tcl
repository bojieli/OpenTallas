# Retain genuine routed result even if source/count guards subsequently reject.
write_db /repair/actual_after_route.odb
if {[llength [[ord::get_db_block] getInsts]] != $::l1_retained_inst_count} {error "L1 no-birth repair added/removed instances"}
source /work/route_guard_post.tcl
