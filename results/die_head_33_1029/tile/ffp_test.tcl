read_db /odb/3_place.odb
set ff_blk [ord::get_db_block]; set ff_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
source /out/ffp.tcl
set ffl {}
foreach i [$ff_blk getInsts] { set nm [$i getName]; if {![regexp {^u_cland_i[/.]} $nm]} continue; if {[cland_isseq $i] && ![[$i getMaster] isBlock]} { lappend ffl $i } }
puts "FFP n [llength $ffl]"
set fh [open /out/ffp_keys.txt w]
foreach pr [lsort -dictionary -index 0 [cland_ffp_keys $ffl]] { puts $fh [lindex $pr 0] }
close $fh
set fh [open /out/ffp_pins.txt w]
foreach i $ffl { set h [cland_cone_pin $i]; puts $fh "[$i getName]\t[lindex $h 1]\t[lindex $h 0]" }
close $fh
puts FFP_DONE
