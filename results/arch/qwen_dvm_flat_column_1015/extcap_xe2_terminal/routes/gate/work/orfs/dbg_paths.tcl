foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] { read_liberty $f }
read_db /work/results/asap7/opentallas_qfd_xs_leaf_extcap_asap7_ref_gate/base/4_1_cts.odb
read_sdc /work/results/asap7/opentallas_qfd_xs_leaf_extcap_asap7_ref_gate/base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
report_checks -path_delay max -group_path_count 3 -fields {fanout cap slew input_pins} -format full_clock_expanded -digits 1
report_checks -path_delay max -through [get_pins -hier *wo_off*] -digits 1
report_tns
report_wns
