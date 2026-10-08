
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_ff.lib
read_db /work/results/asap7/opentallas_ot_dsrom_head_elem_asap7_dshead_elemB_ss_a318fdf47/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_dsrom_head_elem_asap7_dshead_elemB_ss_a318fdf47/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_dsrom_head_elem_asap7_dshead_elemB_ss_a318fdf47/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/dsrom_fh_safe/gen/signoff_elemB.sdc
puts "OT_WS_MAX [sta::worst_slack_cmd max] OT_WS_MIN [sta::worst_slack_cmd min]"
report_clock_latency -include_internal_latency
write_timing_model -library_name ot_dsrom_head_elem_ff /out/ot_dsrom_head_elem_ff.lib

puts OT_EXPORT_DONE
exit
