set cb [ord::get_db_block]
source /work/prd_route_keep.tcl
# Public normal GRT journal must begin BEFORE the only two approved pose changes.
global_route -start_incremental
foreach {name master oldxy newxy} {_27646_ OA211x2_ASAP7_75t_R {99090 37800} {37044 54540} wire17963 BUFx12_ASAP7_75t_R {32184 36180} {37800 78840}} {
 set i [$cb findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $master || [$i getLocation] ne $oldxy || [$i getOrient] ne "R0"} {error CAP_SOURCE_POSE_IDENTITY}
 set status [$i getPlacementStatus];set dnt [$i isDoNotTouch]
 $i setPlacementStatus PLACED
 $i setLocation {*}$newxy
 $i setPlacementStatus $status
 if {[$i getLocation] ne $newxy || [$i isDoNotTouch] != $dnt} {error CAP_EXACT_TWO_POSE_EVENT}
}
# Selection must be exactly the six incident DATA nets before any wire is ripped.
set rdb [odb::dbDatabase_create];odb::read_db $rdb /work/baseline/6_final.odb
set ref [ot_prd_route_snapshot [[$rdb getChip] getBlock]];odb::dbDatabase_destroy $rdb
set sel [ot_prd_route_keep_select $cb $ref]
if {[lsort [dict get $sel rip]] ne $::cap_expected_nets || [dict get $sel new] || [dict get $sel conn] || [dict get $sel insts_changed] != 2} {error "CAP_DIRTY_SELECTION_MISMATCH $sel"}
foreach name $::cap_expected_nets {
 set n [$cb findNet $name]
 if {$n eq "NULL" || [$n getSigType] ne "SIGNAL" || $n in [ot_clk_dbnets]} {error CAP_AFFECTED_NET_NOT_DATA}
}
ot_prd_route_keep /work/baseline/6_final.odb
global_route -end_incremental
ot_prd_route_keep_restore
# Every non-target routed wire, including real clock and reset wires, must remain exact.
dict for {name tokens} $::cap_wire_before {
 set n [$cb findNet $name]
 if {$n eq "NULL" || [ot_clk_wire_tokens $n] ne $tokens} {error "CAP_NON_TARGET_WIRE_CHANGED $name"}
}
dict for {name record} $::cap_net_flags {
 set n [$cb findNet $name]
 if {[$n getSigType] ne [lindex $record 0]} {error "CAP_SIGTYPE_CHANGED $name"}
 $n setDoNotTouch [lindex $record 1]
}
set final_names {}
foreach i [$cb getInsts] {
 set n [$i getName];lappend final_names $n;set expected [dict get $::cap_inst_before $n]
 if {$n eq "_27646_"} {lset expected 1 {37044 54540}}
 if {$n eq "wire17963"} {lset expected 1 {37800 78840}}
 set actual [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]
 if {$actual ne $expected} {error "CAP_UNEXPECTED_INSTANCE_STATE $n"}
}
set expected_names {};dict for {n record} $::cap_inst_before {if {$n ni $::cap_spacers} {lappend expected_names $n}}
if {[lsort $final_names] ne [lsort $expected_names]} {error CAP_BEFORE_SAVE_INSTANCE_SET_CHANGED}
set current_sig [dict get [ot_prd_route_snapshot $cb] sig]
if {[dict size $current_sig] != [dict size [dict get $ref sig]]} {error CAP_BEFORE_SAVE_NONPG_NET_SET_CHANGED}
dict for {name sig} [dict get $ref sig] {if {![dict exists $current_sig $name] || [dict get $current_sig $name] ne $sig} {error "CAP_BEFORE_SAVE_CONNECTION_CHANGED $name"}}
set pa [ot_native_pg_audit];if {[dict get $pa creates] || [dict get $pa swaps]} {error CAP_UNEXPECTED_NATIVE_BIRTH_OR_SWAP}
if {[ot_pg_drt_diag_library_inventory] ne $::cap_frozen_library_inventory} {error CAP_BEFORE_SAVE_ALL_LOADED_LIBRARY_INVENTORY_CHANGED}
# Use only NEW GRT parasitics after the six-net routing; never rearm stale routed baseline SPEF.
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
ot_clk_dump $::env(RESULTS_DIR)/clock_after.tsv cap_after
ot_pg_native_birth_end
puts "CAP_ROUTING_ONLY_CHECKPOINT exact6 DATA nets, no resizer/master/clock/reset/source/cycle edits; DRT_FILL_FINISH_HELD"
