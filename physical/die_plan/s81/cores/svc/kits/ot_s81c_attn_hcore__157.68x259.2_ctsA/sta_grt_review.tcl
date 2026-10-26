set C $::env(C)
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_${C}_*.lib*]] {read_liberty $f}
read_db /work/5_1_grt.odb
read_sdc /work/5_1_grt.sdc
set bound [expr {$C eq "FF" ? 213.14 : 258.53}]
set_clock_latency -source $bound [get_clocks vclk]
set sta_recovery_removal_checks_enabled 1
set_propagated_clock [get_clocks clk]
source /work/setRC_rcx.tcl
read_guides /work/route.guide
estimate_parasitics -global_routing
puts [format "OT_GRT %s setup_wns %.2f n %d hold_wns %.2f n %d" $C [expr {[sta::worst_slack_cmd max]*1e12}] [sta::endpoint_violation_count max] [expr {[sta::worst_slack_cmd min]*1e12}] [sta::endpoint_violation_count min]]
report_check_types -max_fanout -max_slew -max_capacitance -violators > /work/drv_$C.rpt
report_checks -path_delay min -group_path_count 5 -format end > /work/hold_$C.rpt
report_checks -path_delay max -group_path_count 5 -format end > /work/setup_$C.rpt
report_checks -path_delay max -fields {fanout cap slew} > /work/setup1_$C.rpt
report_checks -path_delay min -fields {fanout cap slew} > /work/hold1_$C.rpt
puts OT_DONE
