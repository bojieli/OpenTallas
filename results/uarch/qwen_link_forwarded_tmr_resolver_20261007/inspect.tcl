read_db [lindex [glob /work/results/asap7/*/base/3_2_place_iop.odb] 0]
foreach i [[ord::get_db_block] getInsts] {set n [$i getName]; set m [[$i getMaster] getName]; if {[regexp -nocase {inv0|inv1} $n] || [regexp {INV} $m]} {puts "INV_INSTANCE $n $m"}}
exit
