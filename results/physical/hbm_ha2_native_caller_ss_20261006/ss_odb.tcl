foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_SS_*.lib*] {read_liberty $f}
read_db /work/results/asap7/turing_ha2_native_caller/base/1_synth.odb
read_sdc /work/constraint.sdc
puts "OT_EVIDENCE MAPPED_NATIVE_CALLER_IDEAL_CLOCK_NO_RC_NO_CTS_UNBOUND_EXTERNAL_IO"
puts "OT_REGISTERS [llength [all_registers -data_pins]]"
check_setup -verbose
report_checks -path_delay max -group_path_count 20 -format full_clock_expanded
report_checks -path_delay min -group_path_count 20 -format full_clock_expanded
foreach pattern {caller_h_v* caller_h_d* caller_p_v* caller_p_flit* caller_arm caller_active caller_rank* caller_pf*} {
 puts "OT_PRODUCER_CLASS $pattern"
 report_checks -unconstrained -to [get_ports $pattern] -path_delay max -group_path_count 8 -format full_clock_expanded
 report_checks -unconstrained -to [get_ports $pattern] -path_delay min -group_path_count 8 -format full_clock_expanded
}
report_check_types -max_slew -max_capacitance -max_fanout -violators
exit
