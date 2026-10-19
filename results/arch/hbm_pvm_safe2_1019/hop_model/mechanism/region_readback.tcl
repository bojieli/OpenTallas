read_db /work/regions_only.odb
set rb [ord::get_db_block]
foreach name {pvm_macro_cone pvm_macro_W_constants} expected {8437 546} {
 set rr [$rb findRegion $name]
 if {$rr eq "NULL" || [$rr getRegionType] ne "EXCLUSIVE"} {error "REGION_READBACK wrongregion $name"}
 set groups [$rr getGroups]
 if {[llength $groups]!=1} {error "REGION_READBACK missingGPLgroup $name"}
 set g [lindex $groups 0]
 if {[$g getType] ne "PHYSICAL_CLUSTER" || [llength [$g getInsts]]!=$expected} {error "REGION_READBACK GPLgroup membership/type wrong $name"}
 set n [llength [$rr getRegionInsts]]
 if {$n!=$expected} {error "REGION_READBACK wrongcount $name:$n"}
 puts "REGION_READBACK PASS $name $n"
}
exit
