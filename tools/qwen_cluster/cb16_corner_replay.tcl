# Read-only GRT database replay; no repair or constraint edits.
set corner $::env(CB16_CORNER)
if {$corner ni {TT FF}} { error "unsupported corner" }
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
set libs [glob $plat/lib/NLDM/*RVT_${corner}*]
foreach f $libs { read_liberty $f }
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/5_1_grt.odb
read_sdc $base/5_1_grt.sdc
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -global_routing
set ::ot_ce_corner [string tolower $corner]
read_sdc $::env(CB16_SIGNOFF)
puts "CB16_CORNER $corner GRT_DB_GLOBAL_ROUTING_RC setup=[sta::worst_slack_cmd max] hold=[sta::worst_slack_cmd min]"
report_checks -path_delay min -format full_clock_expanded -group_path_count 12 -fields {slew cap fanout input nets} -digits 6
report_checks -path_delay max -format full_clock_expanded -group_path_count 4 -fields {slew cap fanout input nets} -digits 6
