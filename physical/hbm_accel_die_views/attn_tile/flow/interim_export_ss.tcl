# CLAUDE HBM-ABSTRACTS (attn) interim view export from a post-CTS odb (docker: /in = ORFS results base, /out = export dir, /src = source snapshot)
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /src/physical/hbm_attn_tile_r/quad/ot_attn_tile_m6h1q/ot_attn_tile_m6h1q_ss.lib
read_lef /src/physical/hbm_attn_tile_r/quad/ot_attn_tile_m6h1q/ot_attn_tile_m6h1q.lef
read_db /in/4_cts.odb
read_sdc /in/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd max] [sta::worst_slack_cmd min]"
write_timing_model -library_name hfd_attn_tile_ss /out/hfd_attn_tile_ss.lib
write_abstract_lef /out/hfd_attn_tile_raw.lef
puts OT_EXPORT_DONE
exit
