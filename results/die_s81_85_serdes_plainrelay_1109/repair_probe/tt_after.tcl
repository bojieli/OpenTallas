foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT_nldm*] { read_liberty $f }
foreach f [glob /work/macros/*_tt.lib] { read_liberty $f }
read_db $::env(ODBX)
read_sdc [lindex [glob /work/run/results/asap7/*/base/4_cts.sdc] 0]
source /work/setRC_rcx.tcl
set real {}; foreach c [all_clocks] { if {[llength [get_property $c sources]]} { lappend real $c } }
set_propagated_clock $real
estimate_parasitics -placement
puts "TTX design setup wns [sta::time_sta_ui [sta::worst_slack_cmd max]] n [sta::endpoint_violation_count max]"
set w 1e9; set cnt 0; set all 0
foreach pe [find_timing_paths -path_delay max -through [get_pins -hierarchical u_bound.u_rrl_*/*] -group_path_count 100000 -endpoint_path_count 1 -slack_max 1e9] {
  set sp [get_full_name [get_property $pe startpoint]]; set ep [get_full_name [get_property $pe endpoint]]
  if {[string match {*u_rrl_*} $sp] && [string match {*u_rrl_*} $ep]} { incr all; set s [get_property $pe slack]; if {$s < 0} {incr cnt; puts "TTX NEG $s $sp -> $ep"}; if {$s < $w} {set w $s} }
}
puts "TTX relay-to-relay setup: paths $all neg $cnt worst $w"
