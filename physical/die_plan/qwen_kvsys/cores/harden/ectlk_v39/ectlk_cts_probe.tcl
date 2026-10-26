# KV-CORES-PAR 10-24 (qkd_ectlk v3.9 centre-fed clock): POST_CTS_TCL hook (kit runs with SKIP_CTS_REPAIR_TIMING=1).
# 1. measures the raw CTS result before any timing repair: per-register clock arrival (TC, placement RC) ->
#    /work/cts_probe/clk_arrival.csv (name,x,y,arrival_ps) + clock buffer count + unrepaired setup / hold WNS
#    (the earlier ectlk runs died in the in-flow hold repair: RSZ-0060 max buffer count, raw hold -538..-570 ps on the
#    rst_n removal / input seam paths because the corner-fed tree had 680-890 ps insertion vs the 250 ps vclk).
# 2. then the in-flow repair ORFS would have run (setup, then hold, HOLD_SLACK_MARGIN), with -max_buffer_percent
#    OT_HOLD_MAXBUF (ORFS default 20 % of a 27k-cell core = the RSZ-0060 ceiling); counts reported.
file mkdir /work/cts_probe
set fh [open /work/cts_probe/clk_arrival.csv w]
puts $fh "name,x,y,arrival_ps"
set blk [ord::get_db_block]
set u [$blk getDbUnitsPerMicron]
set n 0; set sum 0.0; set mn 1e9; set mx -1e9
foreach p [all_registers -clock_pins] {
  set a ""
  catch {set a [get_property $p arrival_max_rise]}
  if {$a eq "" || ![string is double -strict $a]} { continue }
  set x 0; set y 0
  catch { lassign [[[sta::sta_to_db_pin $p] getInst] getLocation] x y }
  puts $fh "[get_full_name $p],[expr {$x / double($u)}],[expr {$y / double($u)}],$a"
  incr n; set sum [expr {$sum + $a}]; if {$a < $mn} {set mn $a}; if {$a > $mx} {set mx $a}
}
close $fh
set nb 0
foreach i [$blk getInsts] { if {[string match "clkbuf*" [$i getName]] || [string match "clkload*" [$i getName]]} { incr nb } }
set ws [sta::worst_slack_cmd max]; set wh [sta::worst_slack_cmd min]
puts "KVPAR_CTS raw: regs $n insertion min [format %.1f $mn] mean [format %.1f [expr {$sum / max($n,1)}]] max [format %.1f $mx] clkbufs $nb setup_ws [format %.1f $ws] hold_ws [format %.1f $wh]"
report_clock_skew -hold > /work/cts_probe/skew_hold_raw.rpt
report_checks -path_delay min -group_path_count 3 -format full_clock_expanded > /work/cts_probe/hold_raw.rpt
report_checks -path_delay max -group_path_count 3 > /work/cts_probe/setup_raw.rpt
set ninst0 [llength [$blk getInsts]]
repair_timing -setup -setup_margin $::env(SETUP_SLACK_MARGIN) -skip_last_gasp -repair_tns 100
repair_timing -hold -hold_margin $::env(HOLD_SLACK_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF) -allow_setup_violations
detailed_placement
check_placement -verbose
estimate_parasitics -placement
set ws [sta::worst_slack_cmd max]; set wh [sta::worst_slack_cmd min]
puts "KVPAR_CTS repaired: added_insts [expr {[llength [$blk getInsts]] - $ninst0}] setup_ws [format %.1f $ws] hold_ws [format %.1f $wh]"
report_checks -path_delay min -group_path_count 3 > /work/cts_probe/hold_rep.rpt
report_checks -path_delay max -group_path_count 3 > /work/cts_probe/setup_rep.rpt
