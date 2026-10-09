
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_qwen_rom_core_asap7_qcc_core_kv_banked_fullwidth_clkfp_77d93ac50_tt/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_qwen_rom_core_asap7_qcc_core_kv_banked_fullwidth_clkfp_77d93ac50_tt/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_qwen_rom_core_asap7_qcc_core_kv_banked_fullwidth_clkfp_77d93ac50_tt/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/qwen_core_ctx/signoff833_skew90.sdc
puts "OT_WS_HOLD [sta::worst_slack_cmd min]"
set n 0; set ni 0; set wi 1e9; set wr 1e9
foreach p [all_outputs] { set s [get_property $p slack_min]; if {$s eq "INF"} continue
  set pth [find_timing_paths -path_delay min -to $p]
  set sp [get_property [get_property $pth startpoint] full_name]
  if {[get_ports -quiet $sp] ne ""} { if {$s < $wi} {set wi $s}; if {$s<0} {incr ni} } else { if {$s < $wr} {set wr $s}; if {$s<0} {incr n} } }
puts "OT_OUT_FEEDTHRU worst $wi neg $ni ; OT_OUT_REG worst $wr neg $n"
report_checks -path_delay min -group_path_count 2 -format full_clock_expanded
report_checks -path_delay min -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 1 -format full_clock_expanded
