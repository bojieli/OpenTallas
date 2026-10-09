
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_hbm_native_frame_station_rb_asap7_tk_W2_safe_NO2/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_hbm_native_frame_station_rb_asap7_tk_W2_safe_NO2/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hbm_native_frame_station_rb_asap7_tk_W2_safe_NO2/base/6_final.spef
set_propagated_clock [all_clocks]

puts "ATTR_WS [sta::worst_slack_cmd max]"
puts "ATTR_TNS [sta::total_negative_slack_cmd max]"
set negative {}
set output_count 0
foreach p [all_outputs] {
 incr output_count
 set s [get_property $p slack_max]
 if {$s ne "INF" && $s < 0} {lappend negative [list $s $p [get_full_name $p]]}
}
puts "ATTR_OUTPUT_COUNT $output_count NEGATIVE_PROPERTY_COUNT [llength $negative]"
set ordered [lsort -real -index 0 $negative]
foreach item [lrange $ordered 0 7] {
 lassign $item s p name
 puts "ATTR_NEGATIVE_PORT_BEGIN name=$name property_slack_max=$s"
 puts "ATTR_PORT_OBJECT $p"
 set paths [find_timing_paths -to $p -path_delay max -group_path_count 2]
 puts "ATTR_CONSTRAINED_PATH_COUNT [llength $paths]"
 foreach path $paths {puts "ATTR_CONSTRAINED_PATH_SLACK [get_property $path slack]"}
 report_checks -to $p -path_delay max -group_path_count 2 -format full_clock_expanded
 puts "ATTR_UNCONSTRAINED_DIAGNOSTIC"
 report_checks -to $p -path_delay max -unconstrained -group_path_count 2 -format full_clock_expanded
 puts "ATTR_NEGATIVE_PORT_END"
}
puts "ATTR_ACTUAL_OUTPUT_PATHS"
report_checks -to [all_outputs] -path_delay max -group_path_count 2 -format full_clock_expanded
puts "ATTR_CLOCKS"
report_clocks
puts "ATTR_DONE"
exit
