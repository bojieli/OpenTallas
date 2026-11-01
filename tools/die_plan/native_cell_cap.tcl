# Same 400k partition run cap, measured on the actual synthesized top before
# TAP/filler insertion and before floorplan repair/placement. Macro masters are
# physical blocks, not standard cells. No library-helper stat is consulted.
set ot_cap_std 0
set ot_cap_macros 0
foreach ot_cap_i [[ord::get_db_block] getInsts] {
 if {[[$ot_cap_i getMaster] isBlock]} { incr ot_cap_macros } else { incr ot_cap_std }
}
set ot_cap_receipt [open /work/native_cell_count.json w]
puts $ot_cap_receipt [format {{"schema":"opentallas.native_cell_count.v1","stage":"pre_floorplan","stdcells":%d,"macros":%d,"limit":400000}} $ot_cap_std $ot_cap_macros]
close $ot_cap_receipt
puts "OT_NATIVE_CELL_CAP actual_std=$ot_cap_std macros=$ot_cap_macros limit=400000"
if {$ot_cap_std > 400000} {
 error "OT_NATIVE_CELL_CAP actual standard cell count $ot_cap_std above 400000 run cap"
}
unset -nocomplain ot_cap_std ot_cap_macros ot_cap_i ot_cap_receipt
