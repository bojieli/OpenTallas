set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $plat/lib/NLDM/*RVT_TT*] {read_liberty $f}
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/4_1_cts.odb
read_sdc $base/4_cts.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/qfd_vm_face_sn_e1/signoff.sdc
puts "SN_CTS_CONTEXT tt actual4_1_cts placementRC unqualified; original source SLEW/waveform/IO preserved"
puts "SN_CTS_SLACK tt setup=[sta::worst_slack_cmd max] hold=[sta::worst_slack_cmd min]"
puts "SN_PIN_ORACLE_BEGIN q334"
report_checks -to [get_ports {q[334]}] -path_delay max -format full_clock_expanded -fields {slew cap input fanout} -group_path_count 1
report_checks -to [get_ports {q[334]}] -path_delay min -format full_clock_expanded -fields {slew cap input fanout} -group_path_count 1
puts "SN_PIN_ARRIVAL q334"
report_arrival -digits 6 [get_ports {q[334]}]
puts "SN_CLK_SOURCE"
report_arrival -digits 6 [get_ports clk]
report_slews -digits 6 [get_ports clk]
report_clock_properties [all_clocks]
write_sdc /out/oracle_tt.sdc
puts "SN_PIN_ORACLE_PASS"
exit
