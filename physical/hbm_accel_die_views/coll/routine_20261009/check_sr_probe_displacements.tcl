# Fresh-process comparison against immutable original metadata; no DB mutation.
# Metadata is exported by probe_sr_bounded_release181.tcl from the original failed ODB.
source $::env(OT_SR_METADATA_FILE)
read_db $::env(OT_PROBE_ODB)
set moved 0;set outside 0;set macro_bad 0;set anchor_bad 0;set maxx 0;set maxy 0
foreach inst [[ord::get_db_block] getInsts] {
 set name [$inst getName]
 if {![dict exists $all_orig $name]} {error "Unexpected instance $name"}
 set xy [dict get $all_orig $name];set now [$inst getOrigin]
 set dx [expr {abs([lindex $now 0]-[lindex $xy 0])}];set dy [expr {abs([lindex $now 1]-[lindex $xy 1])}]
 if {$dx||$dy} {incr moved}
 set maxx [expr {max($maxx,$dx)}];set maxy [expr {max($maxy,$dy)}]
 if {$dx>8100||$dy>6210} {incr outside}
 if {[dict exists $macro_orig $name] && [dict get $macro_orig $name] ne [list [$inst getOrigin] [$inst getOrient]]} {incr macro_bad}
 if {[dict exists $anchor_meta $name] && [dict get $anchor_meta $name] ne [list [$inst getOrigin] [$inst getOrient]]} {incr anchor_bad}
}
puts "SR_PROBE_ACTUAL_DISPLACEMENT_DBUMAX $maxx $maxy MOVED $moved OUTSIDE_8p10x6p21um $outside MACRO_MOVED $macro_bad FIXED_ANCHOR_MOVED $anchor_bad"
if {$macro_bad||$anchor_bad} {error "Wider probe violated required fixed positions"}
puts "SR_PROBE_IMMUTABLE_CONTRACT_PASS"
exit
