# S81/HEAD3 10-25 CTS STOP gate (COORD 2026-10-25 00:46): after CTS (placement RC, all corners incl. FF), before any
# hold repair: FF (bc, the hold sign-off corner) hold WNS < -100 ps or > 2000 FF hold endpoints = structural -> stop the
# run (plan/RTL fix, not repair).  TT hold is not a sign-off check and is reported only (elemB c9 10-25: TT -115 on the
# x[] input pin registers vs the TT vclk, FF -45.3 / 1909).
# On STOP: 4_1_cts_gate.odb + cts_gate_ends.tsv (every violating hold endpoint: slack, startpoint, endpoint) for the
# classification.  Then the unchanged ORFS CTS repair (repair_timing_helper at the kit HOLD_SLACK_MARGIN) + legalise.
estimate_parasitics -placement
set ot_sw [expr {[sta::worst_slack_cmd max] * 1e12}]
set ot_all_hn [sta::endpoint_violation_count min]
set ot_ff ""
foreach n {bc ff BC FF} {
  if {![catch {find_timing_paths -corner $n -path_delay min -group_path_count 100000 -endpoint_path_count 1 -slack_max 0} ot_ps]} { set ot_ff $n; break }
}
if {$ot_ff eq ""} { error "OT_CTS_GATE: no FF / bc corner defined ($ot_ps)" }
set ot_hn [llength $ot_ps]
set ot_hw 0.0
foreach p $ot_ps { set s [get_property $p slack]; if {$s < $ot_hw} { set ot_hw $s } }
set fh [open /work/cts_gate.json w]
puts $fh [format "{\"corner\": \"%s\", \"ff_hold_wns_ps\": %.2f, \"ff_hold_viol\": %d, \"all_corner_hold_viol\": %d, \"setup_wns_ps\": %.2f, \"limit_wns_ps\": -100, \"limit_viol\": 2000}" $ot_ff $ot_hw $ot_hn $ot_all_hn $ot_sw]
close $fh
puts "OT_CTS_GATE corner $ot_ff ff_hold_wns $ot_hw ff_hold_viol $ot_hn (all corners $ot_all_hn) setup_wns $ot_sw"
if {$ot_hw < -100.0 || $ot_hn > 2000} {
  set fh [open /work/cts_gate_ends.tsv w]
  foreach p $ot_ps {
    puts $fh [format "%.2f\t%s\t%s" [get_property $p slack] [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]]
  }
  close $fh
  report_checks -path_delay min -group_path_count 5 -slack_max 0 -format full_clock_expanded > /work/cts_gate_min.rpt
  orfs_write_db $::env(RESULTS_DIR)/4_1_cts_gate.odb
  error "OT_CTS_GATE STOP: structural FF hold (WNS $ot_hw ps, $ot_hn endpoints)"
}
repair_timing_helper
detailed_placement
check_placement -verbose
estimate_parasitics -placement
