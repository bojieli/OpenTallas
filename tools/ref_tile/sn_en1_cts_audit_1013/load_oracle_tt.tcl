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
puts "SN_LOAD_CASE original80"
report_arrival -digits 6 [get_ports {q[334]}]
set_load 0 [get_ports {q[*]}]
estimate_parasitics -placement
puts "SN_LOAD_CASE diagnostic0_reestimated"
report_arrival -digits 6 [get_ports {q[334]}]
write_timing_model -library_name ot_qfd_vm_face_sn_e1_tt_load0 /out/ot_qfd_vm_face_sn_e1_tt_load0.lib
set_load 2.88 [get_ports {q[*]}]
estimate_parasitics -placement
puts "SN_LOAD_CASE diagnostic2.88_reestimated"
report_arrival -digits 6 [get_ports {q[334]}]
set_load 80 [get_ports {q[*]}]
estimate_parasitics -placement
puts "SN_LOAD_CASE original80_restored"
report_arrival -digits 6 [get_ports {q[334]}]
puts "SN_LOAD_ORACLE_PASS"
exit
