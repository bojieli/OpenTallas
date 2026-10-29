# HBM-CORES-KITS-10 / REBAL: HNX restored35 (TT +18.89 / FF +0.0015, clock frozen) -> FF hold repair with margin 10 ps
# BEFORE DRT (the ring kit lost ~9.7 ps FF hold GRT->RCX); clock nets/instances frozen and asserted; both scenes active
# (TT setup guard). Output /work/margin10/{5_1_grt.odb,5_1_grt.sdc,clock_final.tsv}. No DRT here.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt_r35.odb restored35_input/4_cts.sdc
set_propagated_clock [all_clocks]
set ::ot_mm_stage 4_cts.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
ot_mm_sync
set tt0 [ot_mm_ws max [ot_mm_sc]]; set ff0 [ot_mm_ws min BC]
puts "HNX_M10 BEFORE TT $tt0 FF $ff0"
if {$tt0 < 0 || $ff0 > 100000 || $ff0 < -100000} {error "STOP before-state invalid"}
source /work/clk_freeze.tcl
file mkdir /work/margin10
ot_clk_freeze /work/margin10
global_route -start_incremental
repair_timing -hold -hold_margin 10 -max_buffer_percent 100
detailed_placement
check_placement -verbose
global_route -end_incremental
ot_clk_freeze_assert margin10_legal
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
ot_mm_unsync
ot_mm_sync
source /work/setRC_rcx.tcl
estimate_parasitics -global_routing
set tt [ot_mm_ws max [ot_mm_sc]]; set ff [ot_mm_ws min BC]
set slew [sta::max_slew_violation_count]; set cap [sta::max_capacitance_violation_count]
puts "HNX_M10 FINAL TT $tt FF $ff SLEW $slew CAP $cap"
catch {report_checks -path_delay min -group_path_count 3 -format full_clock_expanded > /work/margin10/ff_hold.rpt}
if {$tt < 0 || $ff < 0 || $slew > 0 || $cap > 0} { write_db /work/margin10/guard_failed.odb; error "STOP final TT/FF/DRV" }
source /work/core_grt_post.tcl
check_placement -verbose
ot_clk_dump /work/margin10/clock_final.tsv final /work/restored35/clk_freeze_nets.txt
write_db /work/margin10/5_1_grt.odb
write_sdc -no_timestamp /work/margin10/5_1_grt.sdc
puts HNX_M10_DONE
exit
