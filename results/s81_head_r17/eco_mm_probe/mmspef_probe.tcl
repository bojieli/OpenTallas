# R17 probe: does read_spef (no -corner) reach BOTH scenes of an orfs_hold_mm session?  read-only, elemA_eco DB.
proc log_cmd {args} { uplevel 1 $args }
source /probe/orfs_hold_mm.tcl
proc ws {chk sc} { set w 1e6; foreach p [find_timing_paths -path_delay $chk -scenes $sc -group_path_count 1] { set s [get_property $p slack]; if {$s ne "INF" && $s < $w} { set w $s } }; return $w }
ot_mm_read_libs
read_db $::env(RESULTS_DIR)/5_1_grt.odb
ot_mm_read_sdc /probe/4_cts.sdc
source $::env(PLATFORM_DIR)/setRC.tcl
estimate_parasitics -global_routing
ot_mm_sync
puts [format "PROBE grt-est  tc setup %.3f  BC hold %.3f  BC setup %.3f  tc hold %.3f" [ws max tc] [ws min BC] [ws max BC] [ws min tc]]
read_spef $::env(RESULTS_DIR)/6_final.spef
puts [format "PROBE spef     tc setup %.3f  BC hold %.3f" [ws max tc] [ws min BC]]
report_checks -path_delay min -scenes BC -format end -group_path_count 3
exit
