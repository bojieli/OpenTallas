source $::env(SCRIPTS_DIR)/load.tcl
load_design 3_place.odb 3_place.sdc
# IOHP-correct fall-writer contract (main landing_contract: no T/2 shift): HEAD-src values + 416.5
set_input_delay -max 699.7200 -clock fclk_in_t_i [get_ports {t_i[*]}]
foreach p {cland_dn_ready_t_i cland_dn_fault_t_i cland_fstart_in_t_i} { set_input_delay -max 166.6000 -clock fclk_in_t_i [get_ports $p] }
estimate_parasitics -placement
report_worst_slack -max -digits 1
foreach {n f} {fstart cland_fstart_in_t_i t_i t_i[*] dn_ready cland_dn_ready_t_i} { foreach pth [find_timing_paths -from [get_ports $f] -path_delay max -group_path_count 1] { puts "QP $n slack [get_property $pth slack] end [get_full_name [get_property $pth endpoint]]" } }
foreach pth [find_timing_paths -path_delay max -group_path_count 1] { puts "QP worst slack [get_property $pth slack] start [get_full_name [get_property $pth startpoint]] end [get_full_name [get_property $pth endpoint]]" }
