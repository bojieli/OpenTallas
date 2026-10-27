# Read-only TT/FF gate on the accepted actual standalone interface.
set C $::env(OT_CORNER)
set c [string tolower $C]
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob /work/macros/*_${c}.lib] { read_liberty $f }
set nick [expr {[info exists ::env(OT_HEAD_NICK)] ? $::env(OT_HEAD_NICK) : "hd_elemA_rb"}]
read_db /work/run/results/asap7/$nick/base/5_1_grt.odb
read_sdc /work/constraint.sdc
if {$C eq "FF"} { set_clock_latency -source 202.5 [get_clocks vclk] }
set ::env(OT_RC_CAL) 0.8,0.9
source /work/cf/rc_cal.tcl
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set setup [sta::time_sta_ui [sta::worst_slack_cmd max]]
set hold [sta::time_sta_ui [sta::worst_slack_cmd min]]
set ns [sta::endpoint_violation_count max]
set nh [sta::endpoint_violation_count min]
puts "ACTUAL_HEAD_STA $C setup_ps $setup hold_ps $hold setup_endpoints $ns hold_endpoints $nh"
report_checks -path_delay max -group_path_count 5 -format full_clock_expanded -fields {slew cap fanout input}
report_checks -path_delay min -group_path_count 8 -format full_clock_expanded -fields {slew cap fanout input}
set f [open /work/actual_sta_${C}.json w]
puts $f [format {{"corner":"%s","setup_ps":%.6f,"hold_ps":%.6f,"setup_endpoints":%d,"hold_endpoints":%d}} $C $setup $hold $ns $nh]
close $f
if {$C eq "TT"} { write_verilog /work/actual_grt.v }
exit
