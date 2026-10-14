source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_1_pre_repair_setup_hold.odb gray_snapshot_report/3_place.sdc
set_propagated_clock [all_clocks]
ot_mm_sync
puts "GRAY_SNAPSHOT_FF_GLOBAL_MIN"
report_checks -path_delay min -scenes BC -format full_clock_expanded -group_path_count 8 -digits 4
puts "GRAY_SNAPSHOT_SS_GLOBAL_MAX"
report_checks -path_delay max -scenes WC -format full_clock_expanded -group_path_count 8 -digits 4
