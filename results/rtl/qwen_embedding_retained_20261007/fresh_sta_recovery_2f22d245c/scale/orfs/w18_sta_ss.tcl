
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_ss.lib
read_db /work/results/asap7/opentallas_ot_qwen_embed_scale_bank_retained_asap7_qdm_qfd_embed_scale_bank_retained_24bd6a53b/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_qwen_embed_scale_bank_retained_asap7_qdm_qfd_embed_scale_bank_retained_24bd6a53b/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_qwen_embed_scale_bank_retained_asap7_qdm_qfd_embed_scale_bank_retained_24bd6a53b/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc

puts "OT_CORNER ss"
puts "OT_WS [sta::worst_slack_cmd max]"
puts "OT_TNS [sta::total_negative_slack_cmd max]"
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
set n 0; set wd 1e9
foreach p [get_pins -hierarchical */D] { set s [get_property $p slack_max]; if {$s ne "INF"} { if {$s < 0} { incr n }; if {$s < $wd} { set wd $s } } }
puts "OT_VIOL_D_PINS $n"
puts "OT_WS_REG_D $wd"
set wo 1e9
foreach p [all_outputs] { set s [get_property $p slack_max]; if {$s ne "INF" && $s < $wo} { set wo $s } }
puts "OT_WS_OUT $wo"
set pr [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1]
# find_timing_paths returns one worst path PER GROUP. Select the minimum
# across groups; index 0 can be asynchronous even when core_clk is worse.
set ot_worst INF
foreach ot_path $pr {
    set ot_slack [get_property $ot_path slack]
    if {$ot_worst eq "INF" || $ot_slack < $ot_worst} { set ot_worst $ot_slack }
}
puts "OT_WS_R2R $ot_worst"
set pi [find_timing_paths -path_delay max -from [all_inputs] -to [all_registers -data_pins] -group_path_count 1]
# find_timing_paths returns one worst path PER GROUP. Select the minimum
# across groups; index 0 can be asynchronous even when core_clk is worse.
set ot_worst INF
foreach ot_path $pi {
    set ot_slack [get_property $ot_path slack]
    if {$ot_worst eq "INF" || $ot_slack < $ot_worst} { set ot_worst $ot_slack }
}
puts "OT_WS_I2R $ot_worst"
foreach p [find_timing_paths -path_delay max -group_path_count 5000 -endpoint_path_count 1 -slack_max 0] { puts "OT_PATH [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]] [get_property $p slack]" }
exit
