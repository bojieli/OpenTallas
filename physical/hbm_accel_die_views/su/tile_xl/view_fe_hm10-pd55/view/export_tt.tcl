read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /mv0/ot_su12_light_tt.lib
read_lef /mv0/ot_su12_light.lef

read_db /in/results/asap7/opentallas_hfd_su_tile_xl_asap7_sut_hfd_su_tilexl_fe_fa7b65cba_sw147_ongrid_pdnp_tc_hm10_pd55_cl/base/6_final.odb
read_sdc /interface.sdc
read_spef /in/results/asap7/opentallas_hfd_su_tile_xl_asap7_sut_hfd_su_tilexl_fe_fa7b65cba_sw147_ongrid_pdnp_tc_hm10_pd55_cl/base/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd max]"
write_timing_model -library_name hfd_su_tile_xl_tt /out/hfd_su_tile_xl_tt.lib
puts "OT_EXPORT_DONE"
exit
