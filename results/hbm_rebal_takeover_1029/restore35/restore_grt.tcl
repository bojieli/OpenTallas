# ONE approved retained-GRT continuation; original source/833/60/25/frame.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb restored35_input/4_cts.sdc
set_propagated_clock [all_clocks]
set ::ot_mm_stage 4_cts.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
ot_mm_sync
set before_ff [ot_mm_ws min BC]
if {$before_ff > 100000 || $before_ff < -100000} {error "STOP FF hold unconstrained or invalid"}
set before_tt [ot_mm_ws max [ot_mm_sc]]
puts "HNX_RESTORE35 BEFORE_TT $before_tt BEFORE_FF [ot_mm_ws min BC]"
if {$before_tt < 0} {error "STOP TT setup already negative"}
global_route -start_incremental
source /work/restore35.tcl
source /work/clk_freeze.tcl
file mkdir /work/restored35
ot_clk_freeze /work/restored35
# Only new movable data hold cells may move to legalize original clock homes.
detailed_placement
check_placement -verbose
global_route -end_incremental
ot_clk_freeze_assert restored35_legal
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
ot_mm_unsync
ot_mm_sync
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
set tt [ot_mm_ws max [ot_mm_sc]]
set ff [ot_mm_ws min BC]
set slew [sta::max_slew_violation_count]
set cap [sta::max_capacitance_violation_count]
puts "HNX_RESTORE35 LEGAL TT $tt FF $ff SLEW $slew CAP $cap"
if {$tt < 0 || $ff > 100000 || $slew > 0 || $cap > 0} {
 report_check_types -max_slew -max_capacitance -violators
 write_db /work/restored35/guard_failed.odb
 error "STOP actual restored TT/DRV guard"
}
# Existing canonical coupled TT/FF residual hold mechanism, only if needed.
if {$ff < 0} {
 source /work/final_ff_hold.tcl
 ot_final_ff_hold
}
ot_clk_freeze_assert restored35_final
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
ot_mm_unsync
ot_mm_sync
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
puts "HNX_FINAL_ROUTE_ESTIMATE_BEGIN"
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
puts "HNX_FINAL_ROUTE_ESTIMATE_END"
puts "HNX_RESTORE35 FINAL TT [ot_mm_ws max [ot_mm_sc]] FF [ot_mm_ws min BC]"
if {[ot_mm_ws max [ot_mm_sc]] < 0 || [ot_mm_ws min BC] < 0 || [ot_mm_ws min BC] > 100000 || [sta::max_slew_violation_count] > 0 || [sta::max_capacitance_violation_count] > 0} {error "STOP final TT/FF/DRV"}
source /work/core_grt_post.tcl
check_placement -verbose
ot_clk_dump /work/restored35/clock_final.tsv final /work/restored35/clk_freeze_nets.txt
write_db /work/restored35/5_1_grt.odb
write_sdc -no_timestamp /work/restored35/5_1_grt.sdc
set ::env(OT_GEOM_OUT) /work/restored35/geom.tsv
source /work/geom_dump.tcl
puts "HNX_RESTORE35_DONE"
