
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_hbm_integrated_w2_result_sink_asap7_nash_w2_sink_f835_r1/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_hbm_integrated_w2_result_sink_asap7_nash_w2_sink_f835_r1/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hbm_integrated_w2_result_sink_asap7_nash_w2_sink_f835_r1/base/6_final.spef
set_propagated_clock [all_clocks]

set ps [find_timing_paths -path_delay max -group_path_count 10000 -endpoint_path_count 1 -unique_paths_to_endpoint -slack_max 0]
set picks [dict create]
foreach p $ps {
 set ep [get_full_name [get_property $p endpoint]]
 set class $ep
 if {[regexp {on\.code\[([0-9]+)\]} $ep -> word]} {
  if {$word==24} {set class protected_control} elseif {$word<8} {set class protected_metadata} else {set class protected_payload}
 } elseif {[regexp {req\[([0-9]+)\]} $ep -> bit]} {
  if {$bit==336} {set class request_direction} elseif {$bit>=304} {set class request_address} elseif {$bit>=48} {set class request_payload} elseif {$bit>=16} {set class request_strobe} else {set class request_tag}
 }
 if {![dict exists $picks $class] || [get_property $p slack] < [get_property [dict get $picks $class] slack]} {dict set picks $class $p}
}
dict for {class p} $picks {
 puts "SOURCE_CLASS $class [get_property $p slack] [get_full_name [get_property $p startpoint]] -> [get_full_name [get_property $p endpoint]]"
 report_checks -path_delay max -to [get_property $p endpoint] -group_path_count 1 -format full_clock_expanded -fields {fanout capacitance slew input_pin net}
}
exit
