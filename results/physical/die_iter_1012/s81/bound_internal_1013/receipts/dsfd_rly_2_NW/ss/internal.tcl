read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_dsfd_rly_2_NW_asap7_ref_s81_rly_2_nw_v3_faf093855/base/6_final.odb
read_sdc /work/results/asap7/opentallas_dsfd_rly_2_NW_asap7_ref_s81_rly_2_nw_v3_faf093855/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_rly_2_NW_asap7_ref_s81_rly_2_nw_v3_faf093855/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc

puts "OT_INTERNAL_BEGIN"
report_clock_properties
foreach c [all_clocks] {
 puts "OT_INTERNAL_CLOCK [get_full_name $c] [get_property $c period]"
}
set eps [all_registers -data_pins]
puts "OT_INTERNAL_DATA_COUNT [llength $eps]"
set regnames [dict create]
foreach p [all_registers -output_pins] {dict set regnames [get_full_name $p] 1}
set pairs 0
foreach ep $eps {
 foreach p [get_fanin -to $ep -flat -startpoints_only -trace_arcs all] {
  if {[dict exists $regnames [get_full_name $p]]} {
   incr pairs
   puts "OT_INTERNAL_STRUCTURAL_PAIR [get_full_name $p] [get_full_name $ep]"
  }
 }
}
puts "OT_INTERNAL_STRUCTURAL_PAIRS $pairs"
foreach mode {max min} {
 set missing 0
 set worst INF
 foreach ep $eps {
  set val [get_property $ep slack_$mode]
  if {![string is double -strict $val]} {
   incr missing
   puts "OT_INTERNAL_UNCONSTRAINED $mode [get_full_name $ep]"
  } elseif {$worst eq "INF" || $val < $worst} {set worst $val}
 }
 puts "OT_INTERNAL_COVERAGE $mode [llength $eps] $missing $worst"
 set paths [find_timing_paths -from [all_registers -output_pins] -to $eps -path_delay $mode -group_path_count 1000000 -endpoint_path_count 1]
 set worst INF
 foreach p $paths {
  set val [get_property $p slack]
  if {$worst eq "INF" || $val < $worst} {set worst $val}
 }
 puts "OT_INTERNAL_REG2REG $mode [llength $paths] $worst"
 report_checks -from [all_registers -output_pins] -to $eps -path_delay $mode -group_path_count 10 -format full_clock_expanded -digits 6
}
puts "OT_INTERNAL_MIN_PERIOD_BEGIN"
report_clock_min_period
puts "OT_INTERNAL_MIN_PERIOD_END"
puts "OT_INTERNAL_PERIOD_CHECKS_BEGIN"
report_check_types -min_period -min_pulse_width -violators -digits 6
puts "OT_INTERNAL_PERIOD_CHECKS_END"
check_setup -verbose
write_sdc -no_timestamp /out/replayed.sdc
puts "OT_INTERNAL_DONE"
exit
