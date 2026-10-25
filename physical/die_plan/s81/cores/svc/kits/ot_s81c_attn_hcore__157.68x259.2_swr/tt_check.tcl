# PATH-S81/HCORE swr: independent TT setup check (833 ps, kit SDC 60/25, TT vclk 258.53, calibrated RC, propagated clocks).
# Env: ODB, SDC, OUT, BASIS (placement|global_routing).  Writes OUT; prints OT_TT_CHECK; exit 1 on any negative endpoint.
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_TT_*.lib*]] {read_liberty $f}
read_db $::env(ODB)
read_sdc $::env(SDC)
set_clock_latency -source 258.53 [get_clocks vclk]
foreach c [all_clocks] {if {[llength [get_property $c sources]]} {set_propagated_clock $c}}
source /work/setRC_rcx.tcl
estimate_parasitics -$::env(BASIS)
set w [sta::time_sta_ui [sta::worst_slack_cmd max]]
set n [sta::endpoint_violation_count max]
report_checks -path_delay max -group_path_count 20 -endpoint_path_count 1 -fields {slew cap fanout} > $::env(OUT)
puts "OT_TT_CHECK basis $::env(BASIS) setup_wns_ps $w endpoints $n"
if {$w < 0 || $n > 0} { exit 1 }
