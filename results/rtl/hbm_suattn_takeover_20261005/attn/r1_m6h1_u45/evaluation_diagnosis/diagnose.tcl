read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
define_corners WC BC
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_db /in/results/asap7/opentallas_ot_attn_hgrp_m6h1_asap7_cha_r1_m6h1_u45/base/6_final.odb
read_sdc /in/results/asap7/opentallas_ot_attn_hgrp_m6h1_asap7_cha_r1_m6h1_u45/base/6_final.sdc
read_spef /in/results/asap7/opentallas_ot_attn_hgrp_m6h1_asap7_cha_r1_m6h1_u45/base/6_final.spef
set_propagated_clock [all_clocks]
puts "DEFAULT"
report_checks -corner BC -path_delay min -format full_clock_expanded
read_spef -corner BC /in/results/asap7/opentallas_ot_attn_hgrp_m6h1_asap7_cha_r1_m6h1_u45/base/6_final.spef
puts "EXPLICIT_BC_SPEF"
report_checks -corner BC -path_delay min -format full_clock_expanded
exit
