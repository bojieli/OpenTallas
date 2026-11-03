# count instances per master in the 1_synth.odb (after ORFS synth_odb.tcl) -- env ODB = odb path
read_db $::env(ODB)
set c [dict create]
foreach i [[ord::get_db_block] getInsts] { dict incr c [[$i getMaster] getName] }
dict for {k v} $c { puts "ODBCOUNT $k $v" }
exit
