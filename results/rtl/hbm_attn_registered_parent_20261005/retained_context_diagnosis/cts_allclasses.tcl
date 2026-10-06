define_corners WC BC
set_thread_count 16
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /src/physical/hbm_fmax_attn_context/ot_attn_hgrp_m6h1/ot_attn_hgrp_m6h1_ss.lib
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /src/physical/hbm_fmax_attn_context/ot_attn_hgrp_m6h1/ot_attn_hgrp_m6h1_ff.lib
read_db /work/work/orfs/results/asap7/opentallas_ot_attn_registered_parent_phys_asap7_codex_h16_registered_parent_r1/base/4_1_cts.odb
read_sdc /work/work/orfs/results/asap7/opentallas_ot_attn_registered_parent_phys_asap7_codex_h16_registered_parent_r1/base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
source /src/physical/hbm_attn_registered_parent/clock_rc.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set n [llength [get_pins -hierarchical *]]
puts "ACTUAL_PIN_COUNT $n"
foreach c {WC BC} { foreach d {min max} { report_checks -corner $c -path_delay $d -format full_clock_expanded -group_path_count $n -endpoint_path_count 1 -slack_max 0 -digits 6 > /work/cts_${c}_${d}_all.rpt } }
puts "ALLCLASS_REPORT_COMPLETE"
help clock_tree_synthesis
