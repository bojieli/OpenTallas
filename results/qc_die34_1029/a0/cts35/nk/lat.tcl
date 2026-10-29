source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_1_diag.odb 3_place.sdc
estimate_parasitics -placement
catch {ot_mm_sync}
puts "=== CLOCK LATENCY"
catch {report_clock_latency -clock clk} m; puts $m
puts "=== HOLD input worst (BC)"
report_checks -path_delay min -scenes BC -to [get_pins ot_fcap_00034_ff/D] -format full_clock_expanded -digits 2
