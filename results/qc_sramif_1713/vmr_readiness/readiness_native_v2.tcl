source /work/postcts_gate_native_v2.tcl
source /work/cf/mscts_core.tcl
set c [string tolower $::env(OT_CORNER)]
ot_ms_assign_corr $c
puts "READINESS_NATIVE $c hold [sta::time_sta_ui [sta::worst_slack_cmd min]]/[sta::endpoint_violation_count min] setup [sta::time_sta_ui [sta::worst_slack_cmd max]]/[sta::endpoint_violation_count max] slew [sta::max_slew_violation_count] cap [sta::max_capacitance_violation_count]"
ot_ms_report current_native
report_checks -path_delay min -group_path_count 5 -format full_clock_expanded > /work/current_${c}_hold.rpt
set ::ot_ps_lib_only 1
source /work/pair_skew_current.tcl
unset ::ot_ps_lib_only
ot_ps_zero_unc
set M [ot_ps_measure]
ot_ps_write $M /work/current_${c}_pairs.tsv $::env(OT_CORNER)
foreach delay {max min} {set row [dict get $M $delay];puts "READINESS_PAIR $c $delay worst [dict get $row worst] n [dict get $row n]"}
