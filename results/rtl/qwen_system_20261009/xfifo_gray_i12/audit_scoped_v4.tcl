set plat /OpenROAD-flow-scripts/flow/platforms/asap7
set corner $::env(AUDIT_CORNER)
foreach group {AO INVBUF OA SEQ SIMPLE} {
 set lib [lindex [glob $plat/lib/NLDM/asap7sc7p5t_${group}_RVT_${corner}_nldm_*] 0]
 read_liberty $lib
}
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/3_place.odb
read_sdc $base/3_place.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
read_sdc /audit/signoff.sdc
puts "AUDIT_STAGE PLACE_BASELINE CORNER $corner"
puts "AUDIT_BASELINE_SETUP [sta::worst_slack_cmd max] HOLD [sta::worst_slack_cmd min]"
source /audit/gray_cdc_v4.tcl
puts "AUDIT_SCOPED_SETUP [sta::worst_slack_cmd max] HOLD [sta::worst_slack_cmd min]"
report_checks -path_delay min -group_path_count 3 -format full_clock_expanded
report_checks -path_delay max -group_path_count 2 -format full_clock_expanded
set groups [dict create]
foreach cell [get_cells -hierarchical *] {
 set nm [get_full_name $cell]
 if {[regexp {^(.*)[.]((rd_gray|wr_gray_pub|rd_gray_w1|wr_gray_r1)\[.*)$} $nm -> prefix reg]} {
  puts "AUDIT_GRAY_CELL $nm"
 }
}
# Enumerate actual worst-path classes without changing any constraints.
foreach p [find_timing_paths -path_delay min -group_path_count 40 -endpoint_path_count 1] {
 set sp [get_property $p startpoint];set ep [get_property $p endpoint]
 set sc [get_property $p startpoint_clock];set ec [get_property $p endpoint_clock]
 set sn [expr {$sc eq "" ? "-" : [get_full_name $sc]}];set en [expr {$ec eq "" ? "-" : [get_full_name $ec]}]
 puts "AUDIT_HOLD [get_property $p slack] $sn->$en [get_full_name $sp] -> [get_full_name $ep]"
}
exit
