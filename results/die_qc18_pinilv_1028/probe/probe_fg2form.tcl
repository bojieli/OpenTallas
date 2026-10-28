# DIE-QC-18-PINILV placement-parasitics setup probe (diagnostic only): TT libs (FG2 rbprobe list), kit 3_place.odb + 3_place.sdc,
# kit setRC_rcx.tcl, estimate_parasitics -placement.  CLKMODE ideal (census, no tree) or propagated (plan tree in 3_place).
foreach f [split [string trim [read [open /out/libs_tt.txt]]] "\n"] { read_liberty $f }
read_db /base/3_place.odb
read_sdc /kit/constraint.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {$::env(CLKMODE) eq "propagated"} { set_propagated_clock [all_clocks] }
estimate_parasitics -placement
puts "PRB $::env(TAG) WNS [format %.2f [sta::time_sta_ui [sta::worst_slack_cmd max]]] TNS [format %.1f [sta::time_sta_ui [sta::total_negative_slack_cmd max]]] NV [sta::endpoint_violation_count max]"
set f [open /out/ep_$::env(TAG).tsv w]
foreach pa [find_timing_paths -path_delay max -group_path_count 100000 -endpoint_path_count 1 -slack_max 100] {
  puts $f "[get_full_name [get_property $pa startpoint]]\t[get_full_name [get_property $pa endpoint]]\t[format %.2f [sta::time_sta_ui [get_property $pa slack]]]"
}
close $f
report_checks -path_delay max -group_path_count 1 -fields {cap slew fanout} -digits 2 > /out/worst_$::env(TAG).rpt
