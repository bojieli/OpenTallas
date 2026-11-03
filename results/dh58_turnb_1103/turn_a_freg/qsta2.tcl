source $::env(SCRIPTS_DIR)/load.tcl
load_design 3_place.odb 3_place.sdc
estimate_parasitics -placement
report_worst_slack -max -digits 1
report_tns -digits 1
foreach {n f} {fstart cland_fstart_in_t_i t_i t_i[*] dn_ready cland_dn_ready_t_i} { foreach pth [find_timing_paths -from [get_ports $f] -path_delay max -group_path_count 1] { puts "QP $n slack [get_property $pth slack] end [get_full_name [get_property $pth endpoint]]" } }
foreach pth [find_timing_paths -path_delay max -group_path_count 1] { puts "QP worst slack [get_property $pth slack] start [get_full_name [get_property $pth startpoint]] end [get_full_name [get_property $pth endpoint]]" }
foreach pth [find_timing_paths -from [get_pins -hierarchical u_face/*] -path_delay max -group_path_count 1] { puts "QP face->ring slack [get_property $pth slack] end [get_full_name [get_property $pth endpoint]]" }
report_check_types -max_slew -max_capacitance -max_fanout -violators
