read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_db /checkpoint/5_1_grt.odb
read_sdc /checkpoint/5_1_grt.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
read_guides /checkpoint/route.guide
estimate_parasitics -global_routing
set_clock_latency 0 [all_clocks]
set_propagated_clock [all_clocks]
puts "OT_GRT_WS_SECONDS [sta::worst_slack_cmd max]"
set ot_classes [dict create]
set ot_regs [dict create]
foreach c [all_registers -cells] {dict set ot_regs [get_full_name $c] 1}
foreach kind {FF OUTPUT RESET} {
 if {$kind eq "FF"} {set pins [all_registers -data_pins]}
 if {$kind eq "OUTPUT"} {set pins [all_outputs]}
 if {$kind eq "RESET"} {set pins [get_pins -hierarchical */RESETN]}
 foreach p $pins {
  set name [get_full_name $p]
  if {$kind eq "RESET" && ![dict exists $ot_regs [file dirname $name]]} {continue}
  set slack [get_property $p slack_max]
  if {$slack eq "INF" || $slack>=0} {continue}
  puts "OT_NEG $kind $name $slack"
  regsub -all {\[[0-9]+\]} $name {[*]} family
  set family "$kind:$family"
  if {![dict exists $ot_classes $family] || $slack<[lindex [dict get $ot_classes $family] 0]} {
   dict set ot_classes $family [list $slack $p]
  }
 }
}
dict for {family entry} $ot_classes {
 puts "OT_CLASS $family [lindex $entry 0]"
 report_checks -path_delay max -to [lindex $entry 1] -group_path_count 1 -format full_clock_expanded
}
puts OT_GRT_TRUE_RECURRENCE
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -format full_clock_expanded
puts OT_GRT_INPUT_TO_TRUE_FF
report_checks -path_delay max -from [all_inputs] -to [all_registers -data_pins] -group_path_count 1 -format full_clock_expanded
puts OT_GRT_CENSUS_DONE

set ot_data {}
foreach p [all_registers -data_pins] {if {[string match */D [get_full_name $p]]} {lappend ot_data $p}}
puts OT_GRT_NEGATIVE_INPUT_TO_DATA
report_checks -path_delay max -from [all_inputs] -to $ot_data -group_path_count [llength $ot_data] -slack_max 0 -format full_clock_expanded
puts OT_GRT_NEGATIVE_INPUT_TO_DATA_DONE
