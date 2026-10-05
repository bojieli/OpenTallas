define_corners WC BC
read_liberty -corner WC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz}
read_liberty -corner WC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz}
read_liberty -corner WC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz}
read_liberty -corner WC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib}
read_liberty -corner WC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz}
read_liberty -corner BC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner BC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz}
read_liberty -corner BC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner BC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner BC {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib}
read_db {/tmp/opentallas-topk-existing-grt-extraction-20261002/inputs/5_1_grt.odb}
read_sdc {/tmp/opentallas-topk-existing-grt-extraction-20261002/inputs/5_1_grt.sdc}
source {/tmp/opentallas-topk-existing-grt-extraction-20261002/runtime/OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl}
estimate_parasitics -global_routing
report_checks -path_delay max -format full_clock_expanded -fields {slew cap fanout input nets} -digits 4 -group_path_count 10 -endpoint_path_count 1
report_worst_slack -max
report_tns
exit
