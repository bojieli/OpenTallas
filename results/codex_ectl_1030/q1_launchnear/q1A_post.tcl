source /work/kit_modes_eco.tcl
source /work/prd_grtrc.tcl
kit_modes_eco_done
source /work/grt_post_core.tcl
ot_mm_sync
puts "Q1A_GRT_PROTO stage [ot_hold_stage] setupTT [worst_slack -max] holdFF [ot_hold_stats] slew_both [sta::max_slew_violation_count] cap_both [sta::max_capacitance_violation_count]"
report_check_types -max_slew -max_capacitance -violators -max_count 10
ot_clk_freeze_assert q1A_grt_proto
