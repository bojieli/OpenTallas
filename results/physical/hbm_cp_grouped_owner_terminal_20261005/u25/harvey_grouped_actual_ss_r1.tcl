
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_hbm_integrated_su_cp_bind_asap7_cp_grouped_u25/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_hbm_integrated_su_cp_bind_asap7_cp_grouped_u25/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hbm_integrated_su_cp_bind_asap7_cp_grouped_u25/base/6_final.spef
set_propagated_clock [all_clocks]

puts "OT_ACTUAL_FF_DATA_PINS [llength [all_registers -data_pins]]"
set ff_names [dict create]
foreach pin [all_registers -data_pins] {
 set name [get_full_name $pin]; dict set ff_names $name 1
 set slack [get_property $pin slack_max]
 if {$slack ne "INF" && $slack < 0} {puts "OT_FF_VIOL $slack $name"}
}
foreach pin [get_pins -hierarchical */D] {
 set name [get_full_name $pin]; set slack [get_property $pin slack_max]
 if {$slack ne "INF" && $slack < 0 && ![dict exists $ff_names $name]} {puts "OT_COMB_D_VIOL $slack $name"}
}
foreach pin [all_outputs] {
 set slack [get_property $pin slack_max]
 if {$slack ne "INF" && $slack < 0} {puts "OT_OUTPUT_VIOL $slack [get_full_name $pin]"}
}
puts "OT_TRUE_R2R_PATHS"
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 100 -slack_max 0 -format full_clock_expanded
puts "OT_OUTPUT_PATHS"
report_checks -path_delay max -to [all_outputs] -group_path_count 100 -slack_max 0 -format full_clock_expanded
exit
