# Compare private probe against immutable failed input. No database mutation.
read_db $::env(OT_FAILED_ODB)
set orig [dict create]
foreach inst [[ord::get_db_block] getInsts] {
 dict set orig [$inst getName] [list [$inst getOrigin] [$inst getOrient] [[$inst getMaster] isBlock] [$inst getPlacementStatus]]
}
read_db $::env(OT_PROBE_ODB)
set moved 0;set outside 0;set macro_bad 0;set anchor_bad 0;set maxx 0;set maxy 0
foreach inst [[ord::get_db_block] getInsts] {
 set name [$inst getName];if {![dict exists $orig $name]} {error "Unexpected instance $name"}
 lassign [dict get $orig $name] xy orient macro status
 set now [$inst getOrigin];set dx [expr {abs([lindex $now 0]-[lindex $xy 0])}];set dy [expr {abs([lindex $now 1]-[lindex $xy 1])}]
 if {$dx||$dy||[$inst getOrient] ne $orient} {incr moved}
 set maxx [expr {max($maxx,$dx)}];set maxy [expr {max($maxy,$dy)}]
 if {$dx>8100||$dy>6210} {incr outside}
 if {$macro && ($dx||$dy||[$inst getOrient] ne $orient)} {incr macro_bad}
 if {[$inst getPlacementStatus] in {FIRM LOCKED COVER} && ($dx||$dy||[$inst getOrient] ne $orient)} {incr anchor_bad}
}
puts "SR_PROBE_ACTUAL_DISPLACEMENT_DBUMAX $maxx $maxy MOVED $moved OUTSIDE_8p10x6p21um $outside MACRO_MOVED $macro_bad FIXED_ANCHOR_MOVED $anchor_bad"
if {$macro_bad||$anchor_bad} {error "Probe violated required fixed positions"}
puts "SR_PROBE_IMMUTABLE_CONTRACT_PASS"
exit
