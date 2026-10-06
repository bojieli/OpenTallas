read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
set corner $::env(OT_CHECK_CORNER)
foreach lib [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${corner}_*] {read_liberty $lib}
read_verilog /retained/results/asap7/opentallas_ot_hbm_integrated_su_cp_context_asap7_harvey_cp_parent_context_r1/base/1_2_yosys.v
link_design ot_hbm_integrated_su_cp_context
read_sdc /out/retained_netlist_constraint.sdc
write_sdc /out/retained_${corner}_roundtrip.sdc
puts "OT_NETWORK_CONTRACT_PARSE_PASS $corner"
exit
