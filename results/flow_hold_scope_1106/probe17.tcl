set ::env(OT_HOLD_MM) 1
set ::env(OT_MM_SETUP_CORNER) tc
set ::env(RESULTS_DIR) /work/probe17
set ::env(REPORTS_DIR) /work/probe17
file mkdir /work/probe17
set root /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
set tt [list $root/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz $root/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz $root/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz $root/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib $root/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz]
set ff [list $root/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz $root/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz $root/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz $root/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib $root/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz]
proc log_cmd {args} {puts [list {*}$args];return [uplevel 1 $args]}
foreach l [concat $tt $ff] {read_liberty $l}
read_db /work/4_cts.odb
set_mode ss
set_mode ff
define_scene tc -mode ss -liberty $tt
define_scene BC -mode ff -liberty $ff
read_sdc -mode ss /work/4_cts.sdc
read_sdc -mode ff /work/4_cts.sdc
source /work/setRC_rcx.tcl
set_mode ff
read_sdc /work/vclk_ff.sdc
set_propagated_clock [all_clocks]
set_false_path -setup -from [all_clocks]
set_mode ss
set_propagated_clock [all_clocks]
set_false_path -hold -from [all_clocks]
estimate_parasitics -placement
source /work/orfs_hold_mm.tcl
set ::ot_mm_synced 1
set ::ot_mm_active 1
set ::ot_mm_stage 4_cts.sdc
source /work/scope17.tcl
puts "PRIVATE_SCOPE_BASE full=[ot_hold_stats] internal=[ot_hold_rr_stats]"
write_sdc -mode ss -digits 17 -no_timestamp /work/probe17/ss_before.sdc
set t0 [clock seconds]
ot_repair_hold_guarded {-hold_margin 0 -max_buffer_percent 10 -allow_setup_violations}
puts "PRIVATE_SCOPE_RESULT elapsed_s=[expr {[clock seconds]-$t0}] full=[ot_hold_stats] internal=[ot_hold_rr_stats]"
write_sdc -mode ss -digits 17 -no_timestamp /work/probe17/ss_after.sdc
if {[ot_scope_read /work/probe17/ss_before.sdc] ne [ot_scope_read /work/probe17/ss_after.sdc]} {error "PRIVATE_SCOPE_RESTORE_FAIL: SS SDC changed"}
report_checks -path_delay min -scenes BC -group_count 10 > /work/probe17/full_hold_restored.rpt
write_db /work/probe17/repaired.odb
puts PRIVATE_SCOPE_DONE
