# QC-CQB3 s6 geometry/clock dump (s5 + HOLD_SLACK_MAX near-critical hold paths) (render input), from the QC-CQB geom_dump.tcl.  env: OT_CORNER tt|ff, ODB, PAR (grt|spef),
# SPEF (for spef), OUT.  grt: RC-calibrated GRT estimate (cf/rc_cal.tcl, OT_RC_CAL) on the DB's own route guides.
set C [string toupper $::env(OT_CORNER)]; set c [string tolower $C]
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { read_liberty $l }
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_$c.lib
read_db $::env(ODB)
if {[info exists ::env(SDC)]} { read_sdc $::env(SDC) } else { read_sdc /work/constraint.sdc }
if {$::env(PAR) eq "spef"} { read_spef $::env(SPEF) } else {
  source /work/cf/rc_cal.tcl
  set_routing_layers -signal M2-M5 -clock M4-M5
  if {[info exists ::env(GUIDE)] && $::env(GUIDE) ne ""} { read_guides $::env(GUIDE) } else {
    set_global_routing_layer_adjustment M2-M5 0.25; pin_access; global_route -congestion_iterations 30 }
  estimate_parasitics -global_routing
}
set_propagated_clock [all_clocks]
report_worst_slack -max; report_worst_slack -min ;# PATH-QC-SU: init the timing graph before pin arrival queries (pinVertices segv)
if {$::env(PAR) ne "spef" && [info exists ::env(OT_MSCTS_CORR)] && $::env(OT_MSCTS_CORR) ne ""} { source /work/cf/mscts_core.tcl; ot_ms_assign_corr $c }
if {[info exists ::env(VCLK_LAT)]} { set_clock_latency -source $::env(VCLK_LAT) [get_clocks vclk] }
set f [open $::env(OUT) w]
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [format %.2f [expr {$v / double($::dbu)}]] }
set die [$blk getDieArea]
puts $f "DIE\t[um [$die xMin]]\t[um [$die yMin]]\t[um [$die xMax]]\t[um [$die yMax]]"
foreach bt [$blk getBTerms] {
  set bb [$bt getBBox]
  puts $f "PORT\t[$bt getName]\t[um [expr {([$bb xMin]+[$bb xMax])/2}]]\t[um [expr {([$bb yMin]+[$bb yMax])/2}]]\t[$bt getIoType]"
}
foreach i [$blk getInsts] {
  set m [$i getMaster]; set mn [$m getName]
  if {[string match "FILL*" $mn] || [string match "DECAP*" $mn] || [string match "TAPCELL*" $mn]} continue
  set bb [$i getBBox]
  set kind std
  if {[$m isBlock]} { set kind macro }
  puts $f "INST\t[$i getName]\t$mn\t$kind\t[um [$bb xMin]]\t[um [$bb yMin]]\t[um [$bb xMax]]\t[um [$bb yMax]]"
}
foreach n [$blk getNets] {
  if {[$n getSigType] ne "CLOCK"} continue
  set drv ""; set sinks {}
  foreach it [$n getITerms] { if {[$it isOutputSignal]} { set drv [[$it getInst] getName] } else { lappend sinks "[[$it getInst] getName]/[[$it getMTerm] getName]" } }
  foreach bt [$n getBTerms] { if {$drv eq ""} { set drv "PORT:[$bt getName]" } }
  puts $f "CNET\t[$n getName]\t$drv\t[llength $sinks]\t[join $sinks { }]"
}
foreach p [all_registers -clock_pins] {
  set a ""; catch {set a [get_property $p arrival_max_rise]}
  puts $f "CK\t[get_full_name $p]\t$a"
}
set regs {}
foreach p [all_registers -clock_pins] { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] 1 }
foreach p [get_fanout -from [all_inputs -no_clocks] -flat -endpoints_only -trace_arcs all] {
  set i [regsub {/[^/]+$} [get_full_name $p] {}]; if {[dict exists $regs $i]} { puts $f "PINREG\tin\t$i" }
}
foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
  set i [regsub {/[^/]+$} [get_full_name $p] {}]; if {[dict exists $regs $i]} { puts $f "PINREG\tout\t$i" }
}
foreach pa [find_timing_paths -path_delay min -group_path_count 600 -endpoint_path_count 1 -slack_max [expr {[info exists ::env(HOLD_SLACK_MAX)] ? $::env(HOLD_SLACK_MAX) : 0}]] {
  set sp [get_full_name [get_property $pa startpoint]]; set ep [get_full_name [get_property $pa endpoint]]
  set ck ""; catch { set ck [get_full_name [get_property $pa endpoint_clock]] }
  puts $f "HOLD\t$ep\t$sp\t[get_property $pa slack]\t\t\t$ck"
}
puts $f "WNS\t[sta::time_sta_ui [sta::worst_slack_cmd min]]\t[sta::endpoint_violation_count min]\t[sta::time_sta_ui [sta::worst_slack_cmd max]]"
close $f
puts DUMP_DONE
