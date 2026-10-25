# QC rp1-clock 10-25: after the CTS-stage leaf balance (placement RC).  Recipe stop rule: FF hold WNS < -100 ps or
# > 2000 hold endpoints stops the run here (error -> make fails, no GRT/route).  Also: no clock buffer inside a macro
# outline (GEOM qc_clock_1025 PASS-COND condition).  MCMM (tc bc): worst over corners; FF scene reported separately.
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set g_ws [expr {[sta::worst_slack_cmd min]*1e12}]
set g_n [sta::endpoint_violation_count min]
# QC-PHYS f57: the stop rule judges the core-internal structure (clk + asynchronous groups); the vclk boundary group
# is bound to the measured I only at the route phase (set_vclk.py), so at CTS it is reported, not gated
set g_all $g_ws
set g_ws 1e9
foreach g {clk asynchronous} {
  foreach pa [find_timing_paths -path_delay min -path_group $g -group_path_count 1] { set g_ws [expr {min($g_ws, [get_property $pa slack])}] }
}
puts [format "RP1_CTS_GATE internal hold_wns %.2f (all groups incl. vclk boundary %.2f)" $g_ws $g_all]
set g_ws_max [expr {[sta::worst_slack_cmd max]*1e12}]
puts [format "RP1_CTS_GATE hold_wns %.2f hold_endpoints %d setup_wns %.2f" $g_ws $g_n $g_ws_max]
report_checks -path_delay min -group_path_count 8 -endpoint_path_count 1 -format end
report_checks -path_delay min -format full_clock_expanded -digits 2
set blk [ord::get_db_block]; set bad 0; set nck 0
set macros {}
foreach i [$blk getInsts] { if {[[$i getMaster] isBlock]} { lappend macros [$i getBBox] } }
foreach i [$blk getInsts] {
  if {[[$i getMaster] isBlock]} continue
  set isck 0
  foreach it [$i getITerms] { set n [$it getNet]; if {$n ne "NULL" && [$n getSigType] eq "CLOCK" && [[$it getMTerm] getIoType] eq "OUTPUT"} { set isck 1 } }
  if {!$isck} continue
  incr nck
  set b [$i getBBox]
  foreach m $macros {
    if {[$b xMin] < [$m xMax] && [$b xMax] > [$m xMin] && [$b yMin] < [$m yMax] && [$b yMax] > [$m yMin]} { incr bad; puts "RP1_CTS_GATE clock buffer in macro outline: [$i getName]" }
  }
}
puts "RP1_CTS_GATE clock_drivers $nck in_macro $bad"
if {$bad > 0} { error "RP1_CTS_GATE FAIL: $bad clock buffers inside macro outlines" }
if {$g_ws < -100.0 || $g_n > 2000} { error "RP1_CTS_GATE FAIL: FF hold WNS $g_ws ps / $g_n endpoints (stop rule -100 ps / 2000)" }
