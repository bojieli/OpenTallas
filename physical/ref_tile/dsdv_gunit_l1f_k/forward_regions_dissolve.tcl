set b [ord::get_db_block]
set ng 0;set nr 0
foreach g [$b getGroups] {
 if {![string match ot_gf_* [$g getName]]} continue
 foreach i [$g getInsts] {$g removeInst $i}
 odb::dbGroup_destroy $g
 incr ng
}
foreach r [$b getRegions] {
 if {![string match ot_gf_* [$r getName]]} continue
 odb::dbRegion_destroy $r
 incr nr
}
if {$ng!=4 || $nr!=4} {error "OT_GFD expected four groups and four regions, got $ng / $nr"}
puts "OT_GFD PASS released four forward groups before DPL; GPL positions retained"
