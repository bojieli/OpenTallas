read_db [lindex [glob /work/results/asap7/*/base/3_2_place_iop.odb] 0]
foreach i [[ord::get_db_block] getInsts] {if {[string match {*candidate*} [$i getName]]} {puts "CELL [$i getName] [[$i getMaster] getName]"}}
exit
