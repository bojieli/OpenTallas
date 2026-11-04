source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_cts.odb 4_cts.sdc
estimate_parasitics -placement
report_worst_slack -max -digits 1
report_worst_slack -min -digits 1
foreach {n f} {fstart cland_fstart_in_t_i t_i t_i[*]} { foreach md {max min} { foreach pth [find_timing_paths -from [get_ports $f] -path_delay $md -group_path_count 1] { puts "QC $n $md slack [get_property $pth slack] end [get_full_name [get_property $pth endpoint]]" } } }
foreach md {max min} { foreach pth [find_timing_paths -path_delay $md -group_path_count 1] { puts "QC worst $md slack [get_property $pth slack] start [get_full_name [get_property $pth startpoint]] end [get_full_name [get_property $pth endpoint]]" } }
