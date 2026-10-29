foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*] {read_liberty $f}
read_liberty /work/macros/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
set root /work/run/results/asap7/hc_qkd_ectlk_q3__216x172_8/base
read_db $root/3_place.odb
read_sdc $root/3_place.sdc
set b [ord::get_db_block]
set original [dict create]
foreach i [$b getInsts] {
 dict set original [$i getName] [list [$i getOrigin] [$i getOrient] [[$i getMaster] getName]]
 $i setPlacementStatus FIRM
}
source /work/master_core_infra.tcl
puts "NATIVE_TREE_INSERTED original=[dict size $original]"
detailed_placement
check_placement -verbose
set changed {}
foreach i [$b getInsts] {
 set n [$i getName]
 if {![dict exists $original $n]} continue
 set now [list [$i getOrigin] [$i getOrient] [[$i getMaster] getName]]
 if {$now ne [dict get $original $n]} {lappend changed $n}
}
if {[llength $changed]} {error "NATIVE_ORIGINAL_CHANGED $changed"}
set out [open /work/native_actual_cells.tsv w]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set nclock 0
foreach i [$b getInsts] {
 set box [$i getBBox]
 puts $out "[$i getName]\t[[$i getMaster] getName]\t[expr {[$box xMin]/double($u)}]\t[expr {[$box yMin]/double($u)}]\t[expr {[$box xMax]/double($u)}]\t[expr {[$box yMax]/double($u)}]"
 if {[string match mp_ck_* [$i getName]]} {incr nclock}
}
close $out
if {$nclock != 410} {error "NATIVE_CLOCK_DRIVER_COUNT $nclock"}
write_db /work/native_inserted.odb
write_sdc -no_timestamp /work/native_inserted.sdc
puts "NATIVE_DPL_PASS original=[dict size $original] changed=0 clockdrivers=$nclock"
