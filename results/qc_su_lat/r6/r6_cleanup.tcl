# QC-SU-LAT R6: remove the stale R5 island cells (ot_ms_Q*_nd) left in 3_place; R6 spec names its own cells (core_infra_htree)
set b [ord::get_db_block]; set k 0
foreach i [$b getInsts] { if {[string match ot_ms_Q*_nd [$i getName]]} { $i setDoNotTouch 0; odb::dbInst_destroy $i; incr k } }
puts "OT_R6_CLEANUP removed $k stale R5 island cells"
