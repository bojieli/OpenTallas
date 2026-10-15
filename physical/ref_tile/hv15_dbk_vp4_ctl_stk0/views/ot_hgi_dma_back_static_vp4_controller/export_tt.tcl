read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_TT_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_hgi_dma_back_static_vp4_controller_asap7_ref_hv15_dbk_vp4_ctl_stk0_pfx4_048ef8953/base/6_final.odb
set ::ot_ce_corner tt
read_sdc /work/results/asap7/opentallas_ot_hgi_dma_back_static_vp4_controller_asap7_ref_hv15_dbk_vp4_ctl_stk0_pfx4_048ef8953/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hgi_dma_back_static_vp4_controller_asap7_ref_hv15_dbk_vp4_ctl_stk0_pfx4_048ef8953/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/hv15_dbk_vp4_ctl_stk0/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_hgi_dma_back_static_vp4_controller_tt /out/ot_hgi_dma_back_static_vp4_controller_tt.lib


puts "OT_EXPORT_DONE"
exit
