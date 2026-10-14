source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_1_pre_repair_setup_hold.odb snapshot_report/3_place.sdc
set_propagated_clock [all_clocks]
ot_mm_sync
puts "SNAPSHOT_FF_GLOBAL_MIN_PATHS"
report_checks -path_delay min -scenes BC -format full_clock_expanded -group_path_count 12 -digits 4
puts "SNAPSHOT_FF_ST_R25_PATH"
set p [get_pins -hierarchical -quiet {*st_r*25*/D}]
puts "TARGET_PINS $p"
report_checks -path_delay min -scenes BC -to $p -format full_clock_expanded -group_path_count 4 -digits 4
puts "SNAPSHOT_SS_GLOBAL_MAX_PATHS"
report_checks -path_delay max -scenes WC -format full_clock_expanded -group_path_count 4 -digits 4
