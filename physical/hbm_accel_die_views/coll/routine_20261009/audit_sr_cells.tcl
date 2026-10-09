# Read-only audit of actual failed SR instances; no placement mutation.
read_db $::env(OT_FAILED_ODB)
set block [ord::get_db_block]
set names [open /inspect/sr_violations.txt r]
set byname [dict create]
foreach inst [$block getInsts] {dict set byname [$inst getName] $inst}
set counts [dict create]
set examples [dict create]
while {[gets $names name] >= 0} {
 if {![dict exists $byname $name]} {dict incr counts MISSING; continue}
 set inst [dict get $byname $name]; set master [$inst getMaster]
 set xy [$inst getOrigin]; set x [lindex $xy 0];set y [lindex $xy 1]
 set cls OTHER
 if {[string match {*g_rx*.u_rb/*} $name]} {set cls RX_RING} elseif {[string match {*g_rx*.u_wrx/*} $name]} {set cls RX_DELAY} elseif {[string match {*g_txq*.u_wtx/*} $name]} {set cls DELIVERY_DELAY} elseif {[string match {*u_i_*} $name]} {set cls FACE_INPUT} elseif {[string match {*u_o_*} $name]} {set cls FACE_OUTPUT}
 dict incr counts "$cls/TOTAL"
 dict incr counts "$cls/STATUS_[$inst getPlacementStatus]"
 if {$x%54!=0} {dict incr counts "$cls/X_OFFSITE"}
 if {($y-540)%270!=0} {dict incr counts "$cls/Y_OFFROW"}
 if {![dict exists $examples $cls]} {dict set examples $cls 0}
 if {[dict get $examples $cls]<3} {
  puts "ACTUAL_BAD_CELL $cls $name [$master getName] origin=$xy size=[$master getWidth],[$master getHeight] orient=[$inst getOrient] status=[$inst getPlacementStatus]"
  dict incr examples $cls
 }
}
close $names
puts "SR_FAILED_CELL_COUNTS $counts"
puts "SR_READ_ONLY_AUDIT_COMPLETE"
exit
