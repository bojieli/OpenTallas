source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 5_1_grt.sdc
estimate_parasitics -global_routing
report_checks -path_delay max -fields {fanout cap slew} -digits 3 -group_path_count 1
set eps [sta::find_timing_paths -path_delay max -group_path_count 400 -endpoint_path_count 1 -slack_max 0]
set d [dict create]
foreach p $eps { set n [get_full_name [[$p pin] ]]; regsub {\[.*} $n {} n; dict incr d $n }
dict for {k v} $d { puts "EP $k $v" }
