foreach l [list /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz /work/libs/ot_rom_4096x266_m8_tt.lib] { read_liberty $l }
read_db /work/slab_m8/6_final.odb
read_spef /work/slab_m8/6_final.spef
read_sdc /work/slab_m8/6_final.sdc
set_propagated_clock [all_clocks]
if {[file size /work/slab_m8/extra.sdc] > 0} { read_sdc /work/slab_m8/extra.sdc }
puts "OT_WS_MAX [sta::worst_slack_cmd max] OT_WS_MIN [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_qwen_slab_port_group_tt -cell_name ot_qwen_slab_port_group /work/slab_m8/ot_qwen_slab_port_group_tt.lib
puts OT_ETM_DONE
