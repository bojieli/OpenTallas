# KVG3-CORES (gen_core_kit_kv.py): re-time the routed core at one corner (RCX SPEF of 6_final) and write its ETM.
# env: OT_CORNER (tt|ff) OT_LIBS (liberty list of that corner) OT_LEFS (tech + std + macro LEFs) RES (results dir)
#      OT_MOD (module) OT_OUT (output dir)
foreach l $::env(OT_LEFS) { read_lef $l }
foreach l $::env(OT_LIBS) { read_liberty $l }
read_db $::env(RES)/6_final.odb
if {[info exists ::env(OT_SDC)]} { read_sdc $::env(OT_SDC) } else { read_sdc $::env(RES)/6_final.sdc }
if {[file exists $::env(RES)/6_final.spef]} { read_spef $::env(RES)/6_final.spef; set par spef } else { estimate_parasitics -placement; set par placement }
set_propagated_clock [get_clocks clk]
set c $::env(OT_CORNER)
set fh [open $::env(OT_OUT)/sta_$c.json w]
proc nviol {kind} {
  set n 0
  foreach p [find_timing_paths -path_delay $kind -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] { incr n }
  return $n
}
# user units (ps: ASAP7 liberty time_unit) via the OpenSTA procs (the *_cmd variants return seconds)
set ws [worst_slack -max]
set wh [worst_slack -min]
set tns [total_negative_slack -max]
set thns [total_negative_slack -min]
set nv [nviol max]
set nh [nviol min]
puts $fh "{\"corner\": \"$c\", \"parasitics\": \"$par\", \"setup_wns_ps\": [expr {min(0,$ws)}], \"setup_ws_ps\": $ws, \"setup_tns_ps\": $tns, \"setup_viol_endpoints\": $nv, \"hold_wns_ps\": [expr {min(0,$wh)}], \"hold_ws_ps\": $wh, \"hold_tns_ps\": $thns, \"hold_viol_endpoints\": $nh}"
close $fh
report_checks -path_delay max -group_path_count 5 -format full_clock_expanded > $::env(OT_OUT)/sta_${c}_max.rpt
report_checks -path_delay min -group_path_count 5 -format full_clock_expanded > $::env(OT_OUT)/sta_${c}_min.rpt
puts "OT_CORNER $c setup_ws $ws tns $tns nviol $nv hold_ws $wh nviol $nh ($par)"
# write_timing_model includes the source latency in the model (ORFS generate_abstract does the same)
set_clock_latency -source 0 [all_clocks]
write_timing_model -library_name $::env(OT_MOD)_$c $::env(OT_OUT)/$::env(OT_MOD)_$c.lib
puts "OT_ETM_DONE $c"
exit
