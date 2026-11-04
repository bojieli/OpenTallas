# Native partition run cap, measured on the actual synthesized top before
# TAP/filler insertion and before floorplan repair/placement. Macro masters are
# physical blocks, not standard cells. No library-helper stat is consulted.
# Default 400k. COORD 11-04 06:00 (2), OWNER targets-not-gates: a kit generated
# with gen.py phys --native-cell-cap N runs up to N, never above 517k, the largest
# closed run on record (0.53-1.31M all failed).
set ot_cap_limit 400000
if {[info exists ::ot_native_cell_limit]} {
 set ot_cap_limit [expr {min(int($::ot_native_cell_limit), 517000)}]
}
set ot_cap_std 0
set ot_cap_macros 0
foreach ot_cap_i [[ord::get_db_block] getInsts] {
 if {[[$ot_cap_i getMaster] isBlock]} { incr ot_cap_macros } else { incr ot_cap_std }
}
set ot_cap_receipt [open /work/native_cell_count.json w]
puts $ot_cap_receipt [format {{"schema":"opentallas.native_cell_count.v1","stage":"pre_floorplan","stdcells":%d,"macros":%d,"limit":%d}} $ot_cap_std $ot_cap_macros $ot_cap_limit]
close $ot_cap_receipt
puts "OT_NATIVE_CELL_CAP actual_std=$ot_cap_std macros=$ot_cap_macros limit=$ot_cap_limit"
if {$ot_cap_std > $ot_cap_limit} {
 error "OT_NATIVE_CELL_CAP actual standard cell count $ot_cap_std above $ot_cap_limit run cap"
}
if {$ot_cap_std > 400000} {
 puts "OT_NATIVE_CELL_CAP ADVISORY actual_std=$ot_cap_std above the 400000 target, within kit limit $ot_cap_limit"
}
unset -nocomplain ot_cap_std ot_cap_macros ot_cap_i ot_cap_receipt ot_cap_limit
