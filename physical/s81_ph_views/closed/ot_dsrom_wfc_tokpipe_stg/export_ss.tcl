read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_db /in/results/asap7/wfc_stg_route/base/6_final.odb
read_sdc /in/results/asap7/wfc_stg_route/base/6_final.sdc
read_spef /in/results/asap7/wfc_stg_route/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/dsrom_wfc_tokpipe/eco_scope/region_die150_union.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_dsrom_wfc_tokpipe_stg_ss /out/ot_dsrom_wfc_tokpipe_stg_ss.lib
write_abstract_lef /out/ot_dsrom_wfc_tokpipe_stg.lef

puts "OT_EXPORT_DONE"
exit
