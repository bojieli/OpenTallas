try {
set_thread_count 2
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] {read_liberty $f}
read_db $base/3_5_place_dp.odb
source $plat/setRC.tcl
estimate_parasitics -placement
set ::ot_ce_corner tt
read_sdc /proof/fixed_clock.sdc
source /src/tools/preroute_gate.tcl
ot_preroute_dump /proof/fixed_pre.json
puts "REPLAY_fixed_pre WNS [sta::worst_slack_cmd max]"
foreach c [get_clocks ot_entry_*] {puts "REPLAY_CLOCK [get_full_name $c] propagated=[get_property $c is_propagated]"}
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded -digits 3

} on error {message options} {puts stderr [dict get $options -errorinfo];exit 1}
