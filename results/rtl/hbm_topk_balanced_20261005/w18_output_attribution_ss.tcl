
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_gpu_router_topk_ip_pred_ctx384_asap7_peirce_ctl_topk_pred_ctx_r1/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_gpu_router_topk_ip_pred_ctx384_asap7_peirce_ctl_topk_pred_ctx_r1/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_gpu_router_topk_ip_pred_ctx384_asap7_peirce_ctl_topk_pred_ctx_r1/base/6_final.spef
set_propagated_clock [all_clocks]
report_checks -path_delay max -to [all_outputs] -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew}
exit
