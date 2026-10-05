
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_hbm_integrated_su_cp_bind_asap7_cp_boundary_u25/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_hbm_integrated_su_cp_bind_asap7_cp_boundary_u25/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hbm_integrated_su_cp_bind_asap7_cp_boundary_u25/base/6_final.spef
set_propagated_clock [all_clocks]
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
if {[llength $pr]} { puts "OT_WS_R2R [get_property [lindex $pr 0] slack]" } else { puts "OT_WS_R2R INF" }
set pi [find_timing_paths -path_delay max -from [all_inputs] -to [all_registers -data_pins] -group_path_count 1]
if {[llength $pi]} { puts "OT_WS_I2R [get_property [lindex $pi 0] slack]" } else { puts "OT_WS_I2R INF" }

foreach p [get_pins -hierarchical */D] {
 set s [get_property $p slack_max]
 if {$s ne "INF" && $s < 0} {puts "CP_FAIL_D [get_full_name $p] $s"}
}
foreach p [all_outputs] {
 set s [get_property $p slack_max]
 if {$s ne "INF" && $s < 0} {puts "CP_FAIL_OUT [get_full_name $p] $s"}
}
report_checks -path_delay max -group_path_count 30 -endpoint_path_count 1 -format full_clock_expanded
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 10 -format full_clock_expanded
exit
