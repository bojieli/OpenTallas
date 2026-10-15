read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_qkd_static_kv_return_slots_asap7_ref_qkd_static_kv_return_slots_r1_r1_7489b1528/base/6_final.odb
set ::ot_ce_corner ss
read_sdc /work/results/asap7/opentallas_qkd_static_kv_return_slots_asap7_ref_qkd_static_kv_return_slots_r1_r1_7489b1528/base/6_final.sdc
read_spef /work/results/asap7/opentallas_qkd_static_kv_return_slots_asap7_ref_qkd_static_kv_return_slots_r1_r1_7489b1528/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc

source /fix.sdc
if {[info exists ::env(OT_TEST_SWAP_DOMAIN)] && $::env(OT_TEST_SWAP_DOMAIN) eq "swapped"} {ot_rs_owned_ref hclk $ot_rs_ci}
puts QKD_OWNED_DOMAIN_PASS
report_checks -to [get_ports {actual_data[50]}] -path_delay max -format full_clock_expanded -digits 4 -fields {slew cap fanout}
exit
