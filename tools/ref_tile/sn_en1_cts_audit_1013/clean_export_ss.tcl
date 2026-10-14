set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $plat/lib/NLDM/*RVT_SS*] {read_liberty $f}
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/4_1_cts.odb
read_sdc $base/4_cts.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/qfd_vm_face_sn_e1/signoff.sdc
puts "SN_CTS_CONTEXT ss actual4_1_cts placementRC unqualified; original source SLEW/waveform/IO preserved"
puts "SN_CTS_SLACK ss setup=[sta::worst_slack_cmd max] hold=[sta::worst_slack_cmd min]"
# Explicit diagnostic curve basis only: remove saved80fF output cap and
# regenerate placementRC, so table axis represents newly applied external cap.
# This does not change the original source/benchmark80fF load policy.
set_load 0 [get_ports {q[*]}]
estimate_parasitics -placement
write_timing_model -library_name ot_qfd_vm_face_sn_e1_ss /out/clean_base0/ot_qfd_vm_face_sn_e1_ss.lib
set_load 80 [get_ports {q[*]}]
estimate_parasitics -placement
puts "SN_CLEAN_BASE0_EXPORT_PASS ss diagnosticonly original80policyrestored"
exit
