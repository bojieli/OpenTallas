read_db /work/checkpoint/4_cts.odb
source /scripts/clock_upper_trunk_profile.tcl
set f [open /scripts/clock_names.txt r]
set names [split [string trim [read $f]] \n]
close $f
if {[llength $names]!=2002} {error "Expected complete native clock ownership"}
ot_upper_trunk::apply [ord::get_db_block] $names ck 297 284
write_db /out/profile_4_cts.odb
