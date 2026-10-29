source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_1_cts.odb 4_cts.sdc
set_propagated_clock [all_clocks]
estimate_parasitics -placement
puts "PVJ_CTS_DIAG TT actualselected setup, original833/60/25 constraints"
report_checks -corner [ot_mm_sc] -path_delay max -group_path_count 3 -format full_clock_expanded -fields {slew cap input_pin net fanout} -digits 4
set_mode ff
source /work/vclk_ff.sdc
set_propagated_clock [all_clocks]
estimate_parasitics -placement
write_sdc -no_timestamp /work/pvj_cts_ff_readback.sdc
puts "PVJ_CTS_DIAG FF actualBC placementRC captureframe; exactkit mininput-40/output0 preserved; vclk202.5"
report_checks -corner BC -path_delay min -group_path_count 10 -format full_clock_expanded -fields {slew cap input_pin net fanout} -digits 4
puts "PVJ_CTS_DIAG_NO_GRT_NO_SIGNOFF"
